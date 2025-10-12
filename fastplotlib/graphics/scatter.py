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
    EdgeWidth,
    UniformRotations,
    VertexRotations,
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
        point_rotations: float | ArrayLike = 0,
        point_rotation_mode: pygfx.enums.RotationMode = "uniform",
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

        self._markers: VertexMarkers | None = None
        self._edge_colors: UniformEdgeColor | VertexColors | None = None
        self._edge_width: EdgeWidth | None = None
        self._point_rotations: VertexRotations | UniformRotations | None = None
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

                    geo_kwargs["markers"] = self._markers.buffer

                if uniform_edge_color:
                    self._edge_colors = UniformEdgeColor(edge_colors)
                    material_kwargs["edge_color_mode"] = pygfx.ColorMode.uniform
                else:
                    self._edge_colors = VertexColors(edge_colors, n_datapoints, property_name="edge_colors")
                    material_kwargs["edge_color_mode"] = pygfx.ColorMode.vertex
                    geo_kwargs["edge_colors"] = self._edge_colors.buffer

                self._edge_width = EdgeWidth(edge_width)
                material_kwargs["edge_width"] = self._edge_width.value
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

                self._sprite_texture_array = TextureArray(image, property_name="image")

                material_kwargs["sprite"] = self._sprite_texture_array.buffer[0, 0]

        self._size_space = SizeSpace(size_space)

        if uniform_color:
            material_kwargs["color_mode"] = pygfx.ColorMode.uniform
            material_kwargs["color"] = self.colors
        else:
            material_kwargs["color_mode"] = pygfx.ColorMode.vertex
            geo_kwargs["colors"] = self.colors.buffer

        if uniform_size:
            material_kwargs["size_mode"] = pygfx.SizeMode.uniform
            self._sizes = UniformSize(sizes)
            material_kwargs["size"] = self.sizes
        else:
            material_kwargs["size_mode"] = pygfx.SizeMode.vertex
            self._sizes = PointsSizesFeature(sizes, n_datapoints=n_datapoints)
            geo_kwargs["sizes"] = self.sizes.buffer

        match point_rotation_mode:
            case pygfx.enums.RotationMode.vertex:
                self._point_rotations = VertexRotations(point_rotations, n_datapoints=n_datapoints)

            case pygfx.enums.RotationMode.uniform:
                self._point_rotations = UniformRotations(point_rotations)

            case pygfx.enums.RotationMode.curve:
                pass # nothing special for curve rotation mode

            case _:
                raise ValueError(
                    f"`point_rotation_mode` must be one of: {pygfx.enums.RotationMode}, "
                    f"you have passed: {point_rotation_mode}"
                )

        material_kwargs["rotation_mode"] = point_rotation_mode
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
    def markers(self) -> str | VertexMarkers | None:
        """markers if mode is 'marker'"""
        return self._markers

    @markers.setter
    def markers(self, value: str | np.ndarray[str] | Sequence[str]):
        if self.mode != "markers":
            raise AttributeError(f"scatter plot is: {self.mode}. The mode must be 'markers' to set the markers")
        self._markers[:] = value

    @property
    def edge_colors(self) -> str | pygfx.Color | VertexColors | None:
        """edge_colors if mode is 'marker'"""

        if isinstance(self._edge_colors, VertexColors):
            return self._edge_colors

        elif isinstance(self._edge_colors, UniformEdgeColor):
            return self._edge_colors.value

    @edge_colors.setter
    def edge_colors(self, value: str | np.ndarray | Sequence[str] | Sequence[float]):
        if self.mode != "markers":
            raise AttributeError(f"scatter plot is: {self.mode}. The mode must be 'markers' to set the edge_colors")

        if isinstance(self._colors, VertexColors):
            self._edge_colors[:] = value

        elif isinstance(self._colors, UniformEdgeColor):
            self._edge_colors.set_value(self, value)

    @property
    def edge_width(self) -> float | None:
        """Get or set the edge_width if mode is 'markers'"""
        if self._edge_width is None:
            return None

        return self._edge_width.value

    @edge_width.setter
    def edge_width(self, value: float):
        if self.mode != "markers":
            raise AttributeError(f"scatter plot is: {self.mode}. The mode must be 'markers' to set the edge_width")

        self._edge_width.set_value(self, value)

    @property
    def point_rotation_mode(self) -> str:
        """point rotation mode, read-only, one of 'uniform', 'vertex', or 'curve'"""
        return self.world_object.rotation_mode

    @property
    def point_rotations(self) -> VertexRotations | float | None:
        """rotation of each point, in radians, if `point_rotation_mode` is 'uniform' or 'vertex'"""

        if isinstance(self._point_rotations, VertexRotations):
            return self._point_rotations

        elif isinstance(self._point_rotations, UniformRotations):
            return self._point_rotations.value

    @point_rotations.setter
    def point_rotations(self, value: float | ArrayLike[float]):
        if self.point_rotation_mode not in ["uniform", "vertex"]:
            raise AttributeError(
                f"point_rotation_mode is: {self.point_rotation_mode}. "
                f"it be 'uniform' or 'vertex' to set the `point_rotations`"
            )

        if isinstance(self._point_rotations, VertexRotations):
            self._point_rotations[:] = value

        elif isinstance(self._point_rotations, UniformRotations):
            self._point_rotations.set_value(self, value)

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
