import math
from typing import *

import numpy as np
import pygfx
from pygfx import Texture

from ..utils import quick_min_max
from ._base import Graphic
from .selectors import (
    LinearSelector,
    LinearRegionSelector,
    RectangleSelector,
    PolygonSelector,
)
from .features import (
    TextureArray,
    ImageCmap,
    ImageVmin,
    ImageVmax,
    ImageInterpolation,
    ImageCmapInterpolation,
)


def _format_value(value: float):
    """float -> rounded str, or str with scientific notation"""
    abs_val = abs(value)
    if abs_val < 0.01 or abs_val > 9_999:
        return f"{value:.2e}"
    else:
        return f"{value:.4f}"


class _ImageTile(pygfx.Image):
    """
    Similar to pygfx.Image, only difference is that it modifies the pick_info
    by adding the data row start indices that correspond to this chunk of the big image
    """

    def __init__(
        self,
        geometry,
        material,
        data_slice: tuple[slice, slice],
        chunk_index: tuple[int, int],
        **kwargs,
    ):
        super().__init__(geometry, material, **kwargs)

        self._data_slice = data_slice
        self._chunk_index = chunk_index

    def _wgpu_get_pick_info(self, pick_value):
        pick_info = super()._wgpu_get_pick_info(pick_value)

        data_row_start, data_col_start = (
            self.data_slice[0].start,
            self.data_slice[1].start,
        )

        # add the actual data row and col start indices
        x, y = pick_info["index"]
        x += data_col_start
        y += data_row_start
        pick_info["index"] = (x, y)

        xp, yp = pick_info["pixel_coord"]
        xp += data_col_start
        yp += data_row_start
        pick_info["pixel_coord"] = (xp, yp)

        # add row chunk and col chunk index to pick_info dict
        return {
            **pick_info,
            "data_slice": self.data_slice,
            "chunk_index": self.chunk_index,
        }

    @property
    def data_slice(self) -> tuple[slice, slice]:
        return self._data_slice

    @property
    def chunk_index(self) -> tuple[int, int]:
        return self._chunk_index


class ImageGraphic(Graphic):
    _features = {
        "data": TextureArray,
        "cmap": ImageCmap,
        "vmin": ImageVmin,
        "vmax": ImageVmax,
        "interpolation": ImageInterpolation,
        "cmap_interpolation": ImageCmapInterpolation,
    }

    def __init__(
        self,
        data: Any,
        vmin: float = None,
        vmax: float = None,
        cmap: str = "plasma",
        interpolation: str = "nearest",
        cmap_interpolation: str = "linear",
        colorspace: Literal[
            "srgb", "tex-srgb", "physical", "yuv420p", "yuv444p"
        ] = "srgb",
        colorrange: Literal["full", "limited"] = "full",
        cpu_buffer: bool = True,
        **kwargs,
    ):
        """
        Create an Image Graphic

        Parameters
        ----------
        data: array-like
            array-like, usually numpy.ndarray, must support ``memoryview()``
            # TODO: update this, and also allow tuple/list of arrays for yuv420p
            | shape must be ``[n_rows, n_cols]``, ``[n_rows, n_cols, 3]`` for RGB or ``[n_rows, n_cols, 4]`` for RGBA

        vmin: float, optional
            minimum value for color scaling, estimated from data if not provided

        vmax: float, optional
            maximum value for color scaling, estimated from data if not provided

        cmap: str, optional, default "plasma"
            colormap to use to display the data. For supported colormaps see the
            ``cmap`` library catalogue: https://cmap-docs.readthedocs.io/en/stable/catalog/

        interpolation: str, optional, default "nearest"
            interpolation filter, one of "nearest" or "linear"

        cmap_interpolation: str, optional, default "linear"
            colormap interpolation method, one of "nearest" or "linear"

        colorspace: one of "srgb", "tex-srgb", "physical", "yuv420p", "yuv444p", default "srgb"
            colorspace in which to interpret the provided data.

                * "srgb": the data represents intensity, rgb, or rgba pixels in the sRGB space.
                  sRGB is a standard color space designed for consistent representation of colors
                  across devices like monitors. Most images store colors in this space.
                  The shader convers sRGB colors to physical in the shader before doing color computations.

                * "tex-srgb": the underlying texture will be of an sRGB format. This means the data
                  is automatically converted to sRGB when it is sampled. This results in better glTF
                  compliance (because interpolation in the sampling happens in linear space).
                  Note that sampling *always* results in the sRGB values, also when not interpreted as color.
                  Only supported for rgb and rgba data.

                * "physical": the colors are (already) in the physical / linear space, where lighting
                  calculations can be applied. Shader code that interprets the data as color will use it as-is.

                * "yuv420p": A common video format. The data is represented as 3 planes (y, u, and v).
                  The y represents intensity, and is at full resolution. The u and v planes are a
                  quarter of the size. data must be a 2D array which packs y, u and v:

                    ======
                    | y  |
                    | .  |
                    | .  |
                    | .  |
                    ------
                    | u  |
                    ------
                    | v  |
                    ======

                  This is the same as the packed array structure that pyav provides when reading video in as yuv420p.

                  If the data represents an image with width and height (w, h), then the packed data array must be of
                  shape: [w, h * 3 // 2].

                  # TODO: You can also provide a tuple of arrays to data: (y, u, v)

                  For more info see: https://docs.pygfx.org/stable/_gallery/feature_demo/video_yuv.html
                  and https://github.com/pygfx/pygfx/pull/873


                * "yuv444p": A lesser common video format. The data is represented as 3 planes
                  (y, u, and v) similar to yuv420p however the u and v planes are stored
                  at full resolution.

        colorrange: Literal["full", "limited"] = "limited",
            Relevant for yuv colorspaces. Most videos use "limited".

            * "limited": The luma plane (Y) is limited to the range of 16-235 for 8 bits.
                         The chroma planes (U and V) are limited to the range of 16-240 for 8 bits
            * "full": The luma plane and chroma plane use the full range of the storage format.

            See the following links from the FFMPEG documentation for more details:
            https://trac.ffmpeg.org/wiki/colorspace
            https://ffmpeg.org/doxygen/7.0/pixfmt_8h_source.html#l00609

        cpu_buffer: bool, default True
            If ``True``, maintains a buffer of system RAM that is sychronized with a corresponding storage buffer
            on the GPU.
            If ``False``, setting the graphic data will send the new data directly to the GPU, we also
            call this "bufferless". This is much faster but lacks the following features:
                * you must update the entire data array, i.e. you can perform ``image.data = new_data``, and you
                cannot perform partial updates such as ``image.data[indices] = <new_data_at_indices>``.
                * RGB arrays of shape [rows, cols, 3] are not supported since wgpu does not have RGB textures,
                use RGBA or use `cpu_buffer=True` if you really need RGB instead of RGBA.
                * tooltip values for grayscale data are estimated using an inverse transforms on the colormap LUT.
                The tooltip values may or may not be accurate for a given colormap and vmin, vmax. If you require
                precise and reliable tooltip values for grayscale data use `cpu_buffer=True`.

        kwargs:
            additional keyword arguments passed to :class:`.Graphic`

        """

        super().__init__(**kwargs)

        group = pygfx.Group()

        self._colorspace = colorspace
        self._colorrange = colorrange

        if isinstance(data, TextureArray):
            # share buffer
            self._data = data
        else:
            # create new texture array to manage buffer
            # texture array that manages the multiple textures on the GPU that represent this image
            self._data = TextureArray(
                data,
                cpu_buffer=cpu_buffer,
                colorspace=colorspace,
                colorrange=colorrange,
            )

        if isinstance(data, (tuple, list)):
            # unpacked yuv
            data = data[0]

        if (vmin is None) or (vmax is None):
            _vmin, _vmax = quick_min_max(data)
            if vmin is None:
                vmin = _vmin
            if vmax is None:
                vmax = _vmax

        # other graphic features
        self._vmin = ImageVmin(vmin)
        self._vmax = ImageVmax(vmax)

        self._interpolation = ImageInterpolation(interpolation)
        self._cmap_interpolation = ImageCmapInterpolation(cmap_interpolation)

        # cmap only used for grayscale images
        self._cmap = None
        _map = None

        if data.ndim == 2 and colorspace != "yuv420p":
            # use TextureMap for grayscale images
            self._cmap = ImageCmap(cmap)

            _map = pygfx.TextureMap(
                self._cmap.texture,
                filter=self._cmap_interpolation.value,
                wrap="clamp-to-edge",
            )

        # one common material is used for every Texture chunk
        self._material = pygfx.ImageBasicMaterial(
            clim=(vmin, vmax),
            map=_map,
            interpolation=self._interpolation.value,
            pick_write=True,
        )

        # create the _ImageTile world objects, add to group
        for tile in self._create_tiles():
            group.add(tile)

        self._set_world_object(group)

    def _create_tiles(self) -> list[_ImageTile]:
        tiles = list()
        # iterate through each texture chunk and create
        # an _ImageTile, offset the tile using the data indices
        for texture, chunk_index, data_slice in self._data:
            # create an ImageTile using the texture for this chunk
            img = _ImageTile(
                geometry=pygfx.Geometry(grid=texture),
                material=self._material,
                data_slice=data_slice,  # used to parse pick_info
                chunk_index=chunk_index,
            )

            # row and column start index for this chunk
            data_row_start = data_slice[0].start
            data_col_start = data_slice[1].start

            # offset tile position using the indices from the big data array
            # that correspond to this chunk
            img.world.x = data_col_start
            img.world.y = data_row_start

            tiles.append(img)

        return tiles

    @property
    def data(self) -> TextureArray:
        """
        Get or set the image data.

        Note that if the shape of the new data array does not equal the shape of
        current data array, a new set of GPU Textures are automatically created.
        This can have performance drawbacks when you have a very large image.
        This is usually fine as long as you don't need to do it hundreds of times
        per second.
        """
        return self._data

    @data.setter
    def data(self, new_data):
        if isinstance(new_data, np.ndarray):
            # check if a new buffer is required
            if self._data.shape != new_data.shape:
                # create new TextureArray
                self._data = TextureArray(
                    new_data,
                    cpu_buffer=self.cpu_buffer,
                    colorspace=self.colorspace,
                    colorrange=self.colorrange,
                )

                # see if the new texture data needs a cmap
                if len(self._data.shape) == 3 and self._data.colorspace != "yuv420p":
                    # set cmap to None since data is not grayscale
                    self._cmap = None
                    self._material.map = None
                else:
                    if (
                        self.cmap is None
                    ):  # have switched from non-grayscale -> grayscale image
                        # create default cmap
                        self._cmap = ImageCmap("plasma")
                        self._material.map = pygfx.TextureMap(
                            self._cmap.texture,
                            filter=self._cmap_interpolation.value,
                            wrap="clamp-to-edge",
                        )

                # remove tiles from the WorldObject -> Graphic map
                self._remove_group_graphic_map(self.world_object)

                # clear image tiles
                self.world_object.clear()

                # create new tiles
                for tile in self._create_tiles():
                    self.world_object.add(tile)

                # add new tiles to WorldObject -> Graphic map
                self._add_group_graphic_map(self.world_object)

                return

        self._data.set_value(self, new_data)

    @property
    def cpu_buffer(self) -> bool:
        return self.data.cpu_buffer

    @property
    def colorspace(
        self,
    ) -> Literal["srgb", "tex-srgb", "physical", "yuv420p", "yuv444p"]:
        """colorspace, read-only property"""
        return self.data.colorspace

    @property
    def colorrange(self) -> Literal["full", "limited"]:
        """colorrange, read-only property"""
        return self.data.colorrange

    @property
    def cmap(self) -> str | None:
        """
        Get or set the colormap for grayscale images. Returns ``None`` if image is RGB(A).

        For supported colormaps see the ``cmap`` library catalogue: https://cmap-docs.readthedocs.io/en/stable/catalog/
        """
        if self._cmap is not None:
            return self._cmap.value

    @cmap.setter
    def cmap(self, name: str):
        if len(self.data.shape) > 2:
            raise AttributeError("cmap is only supported for grayscale images")

        self._cmap.set_value(self, name)

    @property
    def vmin(self) -> float:
        """lower contrast limit"""
        return self._vmin.value

    @vmin.setter
    def vmin(self, value: float):
        self._vmin.set_value(self, value)

    @property
    def vmax(self) -> float:
        """upper contrast limit"""
        return self._vmax.value

    @vmax.setter
    def vmax(self, value: float):
        self._vmax.set_value(self, value)

    @property
    def interpolation(self) -> str:
        """Data interpolation method"""
        return self._interpolation.value

    @interpolation.setter
    def interpolation(self, value: str):
        self._interpolation.set_value(self, value)

    @property
    def cmap_interpolation(self) -> str:
        """cmap interpolation method, 'linear' or 'nearest'. Used only for grayscale images"""
        return self._cmap_interpolation.value

    @cmap_interpolation.setter
    def cmap_interpolation(self, value: str):
        self._cmap_interpolation.set_value(self, value)

    def reset_vmin_vmax(self):
        """
        Reset the vmin, vmax by estimating it from the data by subsampling.
        """
        if not self.cpu_buffer:
            return

        vmin, vmax = quick_min_max(self._data.value)
        self.vmin = vmin
        self.vmax = vmax

    def add_linear_selector(
        self, selection: int = None, axis: str = "x", **kwargs
    ) -> LinearSelector:
        """
        Adds a :class:`.LinearSelector`.

        Selectors are just ``Graphic`` objects, so you can manage, remove, or delete them
        from a plot area just like any other ``Graphic``.

        Parameters
        ----------
        selection: int, optional
            initial position of the selector

        kwargs:
            passed to :class:`.LinearSelector`

        Returns
        -------
        LinearSelector

        """

        if axis == "x":
            limits = (0, self._data.value.shape[1])
        elif axis == "y":
            limits = (0, self._data.value.shape[0])
        else:
            raise ValueError("`axis` must be one of 'x' | 'y'")

        if selection is None:
            selection = limits[0]

        if selection < limits[0] or selection > limits[1]:
            raise ValueError(
                f"the passed selection: {selection} is beyond the limits: {limits}"
            )

        selector = LinearSelector(
            selection=selection,
            limits=limits,
            axis=axis,
            parent=self,
            **kwargs,
        )

        self._plot_area.add_graphic(selector, center=False)

        return selector

    def add_linear_region_selector(
        self,
        selection: tuple[float, float] = None,
        axis: str = "x",
        padding: float = 0.0,
        fill_color=(0, 0, 0.35, 0.2),
        **kwargs,
    ) -> LinearRegionSelector:
        """
        Add a :class:`.LinearRegionSelector`.

        Selectors are just ``Graphic`` objects, so you can manage, remove, or delete them
        from a plot area just like any other ``Graphic``.

        Parameters
        ----------
        selection: (float, float)
            initial (min, max) of the selection

        axis: "x" | "y"
            axis the selector can move along

        padding: float, default 100.0
            Extends the linear selector along the perpendicular axis to make it easier to interact with.

        kwargs
            passed to ``LinearRegionSelector``

        Returns
        -------
        LinearRegionSelector

        """

        if axis == "x":
            size = self._data.value.shape[0]
            center = size / 2
            limits = (0, self._data.value.shape[1])
        elif axis == "y":
            size = self._data.value.shape[1]
            center = size / 2
            limits = (0, self._data.value.shape[0])
        else:
            raise ValueError("`axis` must be one of 'x' | 'y'")

        # default padding is 25% the height or width of the image
        if padding is None:
            size *= 1.25
        else:
            size += padding

        if selection is None:
            selection = limits[0], int(limits[1] * 0.25)

        if padding is None:
            size *= 1.25

        else:
            size += padding

        selector = LinearRegionSelector(
            selection=selection,
            limits=limits,
            size=size,
            center=center,
            axis=axis,
            fill_color=fill_color,
            parent=self,
            **kwargs,
        )

        self._plot_area.add_graphic(selector, center=False)

        return selector

    def add_rectangle_selector(
        self,
        selection: tuple[float, float, float, float] = None,
        fill_color=(0, 0, 0.35, 0.2),
        **kwargs,
    ) -> RectangleSelector:
        """
        Add a :class:`.RectangleSelector`.

        Selectors are just ``Graphic`` objects, so you can manage, remove, or delete them
        from a plot area just like any other ``Graphic``.

        Parameters
        ----------
        selection: (float, float, float, float), optional
            initial (xmin, xmax, ymin, ymax) of the selection

        """
        # default selection is 25% of the diagonal
        if selection is None:
            diagonal = math.sqrt(
                self._data.value.shape[0] ** 2 + self._data.value.shape[1] ** 2
            )

            selection = (0, int(diagonal / 4), 0, int(diagonal / 4))

        # min/max limits are image shape
        # rows are ys, columns are xs
        limits = (0, self._data.value.shape[1], 0, self._data.value.shape[0])

        selector = RectangleSelector(
            selection=selection,
            limits=limits,
            fill_color=fill_color,
            parent=self,
            **kwargs,
        )

        self._plot_area.add_graphic(selector, center=False)

        return selector

    def add_polygon_selector(
        self,
        selection: List[tuple[float, float]] = None,
        fill_color=(0, 0, 0.35, 0.2),
        **kwargs,
    ) -> PolygonSelector:
        """
        Add a :class:`.PolygonSelector`.

        Selectors are just ``Graphic`` objects, so you can manage, remove, or delete them
        from a plot area just like any other ``Graphic``.

        Parameters
        ----------
        selection: list[tuple[float, float]], optional
            Initial points for the polygon. If not given or None, you'll start drawing the selection (clicking adds points to the polygon).

        """

        # min/max limits are image shape
        # rows are ys, columns are xs
        limits = (0, self._data.value.shape[1], 0, self._data.value.shape[0])

        selector = PolygonSelector(
            selection,
            limits,
            fill_color=fill_color,
            parent=self,
            **kwargs,
        )

        self._plot_area.add_graphic(selector, center=False)

        return selector

    def format_pick_info(self, pick_info: dict) -> str:
        if not self.cpu_buffer:
            if self.data.colorspace != "yuv420p" and len(self.data.shape) == 2:
                # inverse map from rgb pixel value to grayscale value using the colormap
                # we can only perform a guess
                lut = self._material.map.texture.data
                rgb = pick_info["rgba"][:3]
                closest = np.argmin(np.linalg.norm(lut[:, :3] - rgb, axis=1))
                scalar = closest / (lut.shape[0] - 1)
                val = self.vmin + scalar * (self.vmax - self.vmin)
                return f"{val:.4g}\n!!estimate!!, cpu_buffer=False"
            else:
                # rgba vals
                rgba_val = pick_info["rgba"]
                info = "\n".join(
                    f"{channel}: {val: .4g}" for channel, val in zip("rgba", rgba_val)
                )
                return info

        col, row = pick_info["index"]
        if self.data.value.ndim == 2:
            val = self.data[row, col]
            info = f"{val:.4g}"
        else:
            info = "\n".join(
                f"{channel}: {val:.4g}"
                for channel, val in zip("rgba", self.data[row, col])
            )

        return info
