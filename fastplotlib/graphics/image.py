import math
from typing import *

import pygfx

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
        isolated_buffer: bool = True,
        **kwargs,
    ):
        """
        Create an Image Graphic

        Parameters
        ----------
        data: array-like
            array-like, usually numpy.ndarray, must support ``memoryview()``
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

        isolated_buffer: bool, default True
            If True, initialize a buffer with the same shape as the input data and then
            set the data, useful if the data arrays are ready-only such as memmaps.
            If False, the input array is itself used as the buffer - useful if the
            array is large.

        kwargs:
            additional keyword arguments passed to :class:`.Graphic`

        """

        super().__init__(**kwargs)

        world_object = pygfx.Group()

        if isinstance(data, TextureArray):
            # share buffer
            self._data = data
        else:
            # create new texture array to manage buffer
            # texture array that manages the multiple textures on the GPU that represent this image
            self._data = TextureArray(data, isolated_buffer=isolated_buffer)

        if (vmin is None) or (vmax is None):
            _vmin, _vmax = quick_min_max(self.data.value)
            if vmin is None:
                vmin = _vmin
            if vmax is None:
                vmax = _vmax

        # other graphic features
        self._vmin = ImageVmin(vmin)
        self._vmax = ImageVmax(vmax)

        self._interpolation = ImageInterpolation(interpolation)

        # set map to None for RGB images
        if self._data.value.ndim > 2:
            self._cmap = None
            _map = None
        else:
            # use TextureMap for grayscale images
            self._cmap = ImageCmap(cmap)
            self._cmap_interpolation = ImageCmapInterpolation(cmap_interpolation)

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

            world_object.add(img)

        self._set_world_object(world_object)

    @property
    def data(self) -> TextureArray:
        """Get or set the image data"""
        return self._data

    @data.setter
    def data(self, data):
        self._data[:] = data

    @property
    def cmap(self) -> str | None:
        """
        Get or set the colormap for grayscale images. Returns ``None`` if image is RGB(A).

        For supported colormaps see the ``cmap`` library catalogue: https://cmap-docs.readthedocs.io/en/stable/catalog/
        """
        if self._cmap is not None:
            return self._cmap.value

        return None

    @cmap.setter
    def cmap(self, name: str):
        if self.data.value.ndim > 2:
            raise AttributeError("RGB(A) images do not have a colormap property")
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
        """cmap interpolation method"""
        return self._cmap_interpolation.value

    @cmap_interpolation.setter
    def cmap_interpolation(self, value: str):
        self._cmap_interpolation.set_value(self, value)

    def reset_vmin_vmax(self):
        """
        Reset the vmin, vmax by estimating it from the data by subsampling.
        """

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
        selection: List of positions, optional
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
