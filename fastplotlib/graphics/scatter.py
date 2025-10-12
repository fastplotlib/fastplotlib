from typing import *

import numpy as np
from numpy.typing import ArrayLike
import pygfx

from ._positions_base import PositionsGraphic
from .features import (
    PointsSizesFeature,
    UniformSize,
    SizeSpace,
    VertexPositions,
    VertexColors,
    UniformColor,
    VertexCmap,
    VertexMarkers,
    UniformMarker,
    UniformEdgeColor,
    TextureArray,
)


class ScatterGraphic(PositionsGraphic):
    _features = {
        "data": VertexPositions,
        "sizes": (PointsSizesFeature, UniformSize),
        "colors": (VertexColors, UniformColor),
        "cmap": (VertexCmap, None),
        "size_space": SizeSpace,
    }

    def __init__(
        self,
        data: Any,
        colors: str | np.ndarray | Sequence[float] | Sequence[str] = "w",
        uniform_color: bool = False,
        cmap: str = None,
        cmap_transform: np.ndarray = None,
        mode: Literal["markers", "points", "gaussian", "image"] = "markers",
        markers: None | str | np.ndarray | Sequence[str] = "o",
        uniform_marker: bool = False,
        custom_sdf: str = None,
        image: ArrayLike = None,
        edge_colors: str | np.ndarray | pygfx.Color | Sequence[float] = "black",
        uniform_edge_color: bool = True,
        edge_width: float = 1.0,
        rotations: ArrayLike = None,
        uniform_rotation: bool = False,
        sizes: float | np.ndarray | Sequence[float] = 1,
        uniform_size: bool = False,
        size_space: str = "screen",
        isolated_buffer: bool = True,
        **kwargs,
    ):
        """
        Create a Scatter Graphic, 2d or 3d

        Parameters
        ----------
        data: array-like
            Scatter data to plot, Can provide 2D, or a 3D data. 2D data must be of shape [n_points, 2].
            3D data must be of shape [n_points, 3]

        colors: str, array, tuple, list, Sequence, default "w"
            specify colors as a single human-readable string, a single RGBA array,
            or a Sequence (array, tuple, or list) of strings or RGBA arrays

        uniform_color: bool, default False
            if True, uses a uniform buffer for the scatter point colors. Useful if you need to
            save GPU VRAM when all points have the same color.

        cmap: str, optional
            apply a colormap to the scatter instead of assigning colors manually, this
            overrides any argument passed to "colors".  For supported colormaps see the
            ``cmap`` library catalogue: https://cmap-docs.readthedocs.io/en/stable/catalog/

        cmap_transform: 1D array-like or list of numerical values, optional
            if provided, these values are used to map the colors from the cmap

        isolated_buffer: bool, default True
            whether the buffers should be isolated from the user input array.
            Generally always ``True``, ``False`` is for rare advanced use if you have large arrays.

        sizes: float or iterable of float, optional, default 1.0
            sizes of the scatter points

        uniform_size: bool, default False
            if True, uses a uniform buffer for the scatter point sizes. Useful if you need to
            save GPU VRAM when all points have the same size.

        size_space: str, default "screen"
            coordinate space in which the size is expressed ("screen", "world", "model")

        kwargs
            passed to :class:`.Graphic`

        """

        super().__init__(
            data=data,
            colors=colors,
            uniform_color=uniform_color,
            cmap=cmap,
            cmap_transform=cmap_transform,
            isolated_buffer=isolated_buffer,
            size_space=size_space,
            **kwargs,
        )

        n_datapoints = self.data.value.shape[0]

        geo_kwargs = {"positions": self._data.buffer}

        aa = kwargs.get("alpha_mode", "auto") in ("blend", "weighted_blend")

        material_kwargs = dict(
            pick_write=True,
            aa=aa,
        )

        self._sprite_texture_array: TextureArray | None = None

        # material cannot be changed after the ScatterGraphic is created
        self._mode = mode
        match self.mode:
            case "markers":
                # default
                material = pygfx.PointsMarkerMaterial

                if uniform_marker:
                    if not isinstance(markers, str):
                        raise TypeError("must pass a single <str> marker if uniform_marker is True")

                    self._markers = UniformMarker(markers)

                    material_kwargs["marker_mode"] = pygfx.MarkerMode.uniform
                    material_kwargs["marker"] = self._markers.value
                else:
                    material_kwargs["marker_mode"] = pygfx.MarkerMode.vertex

                    self._markers = VertexMarkers(markers)

                    geo_kwargs["markers"] = self._markers.value_int

                if uniform_edge_color:
                    self._edge_color = UniformEdgeColor(edge_colors)
                material_kwargs["custom_sdf"] = custom_sdf

            case "points":
                # basic points material
                material = pygfx.PointsMaterial

            case "gaussian":
                material = pygfx.PointsGaussianBlobMaterial

            case "image":
                material = pygfx.PointsSpriteMaterial
                # sprites should actually only be one texture, but we don't
                # want to create a new buffer manager just for sprites.
                # If someone is creating scatter plots with images of size
                # larger than the typical limit of 16384, I'm very curious
                # to know what they're trying to visualize
                shared = pygfx.renderers.wgpu.get_shared()
                limit = shared.device.limits["max-texture-dimension-2d"]
                if any([dim > limit for dim in image.shape]):
                    raise BufferError(
                        f"Scatter point image dimension is greater than the device texture limit."
                        f"Your device limit is: {limit} but your image shape is: {image.shape}"
                    )

                self._sprite_texture_array = TextureArray(image)

                material_kwargs["sprite"] = self._sprite_texture_array.buffer[0, 0]

        self._size_space = SizeSpace(size_space)

        if uniform_color:
            material_kwargs["color_mode"] = "uniform"
            material_kwargs["color"] = self.colors
        else:
            material_kwargs["color_mode"] = "vertex"
            geo_kwargs["colors"] = self.colors.buffer

        if uniform_size:
            material_kwargs["size_mode"] = "uniform"
            self._sizes = UniformSize(sizes)
            material_kwargs["size"] = self.sizes
        else:
            material_kwargs["size_mode"] = "vertex"
            self._sizes = PointsSizesFeature(sizes, n_datapoints=n_datapoints)
            geo_kwargs["sizes"] = self.sizes.buffer

        material_kwargs["size_space"] = self.size_space
        world_object = pygfx.Points(
            pygfx.Geometry(**geo_kwargs),
            material=pygfx.PointsMaterial(**material_kwargs),
        )

        self._set_world_object(world_object)

    @property
    def mode(self) -> str:
        """scatter plot mode"""
        return self._mode

    @property
    def image(self) -> TextureArray | None:
        """Get or set the image data, returns None if scatter plot mode is not 'image'"""
        return self._sprite_texture_array

    @image.setter
    def image(self, data):
        if self.mode != "image":
            raise AttributeError(f"scatter plot is: {self.mode}. The mode must be 'image' to set the image")

        self._sprite_texture_array[:] = data

    @property
    def sizes(self) -> PointsSizesFeature | float:
        """Get or set the scatter point size(s)"""
        if isinstance(self._sizes, PointsSizesFeature):
            return self._sizes

        elif isinstance(self._sizes, UniformSize):
            return self._sizes.value

    @sizes.setter
    def sizes(self, value):
        if isinstance(self._sizes, PointsSizesFeature):
            self._sizes[:] = value

        elif isinstance(self._sizes, UniformSize):
            self._sizes.set_value(self, value)
