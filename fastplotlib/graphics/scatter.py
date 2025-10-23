from typing import *

import numpy as np
import pygfx

from ._positions_base import PositionsGraphic
from .features import (
    VertexPointSizes,
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
        "sizes": (VertexPointSizes, UniformSize),
        "colors": (VertexColors, UniformColor),
        "cmap": (VertexCmap, None),
        "markers": (VertexMarkers, UniformMarker, None),
        "edge_colors": (UniformEdgeColor, VertexColors, None),
        "edge_width": (EdgeWidth, None),
        "image": (TextureArray, None),
        "size_space": SizeSpace,
        "point_rotations": (UniformRotations, VertexRotations, None),
    }

    def __init__(
        self,
        data: Any,
        colors: str | np.ndarray | Sequence[float] | Sequence[str] = "w",
        uniform_color: bool = False,
        cmap: str = None,
        cmap_transform: np.ndarray = None,
        mode: Literal["markers", "simple", "gaussian", "image"] = "markers",
        markers: str | np.ndarray | Sequence[str] = "o",
        uniform_marker: bool = False,
        custom_sdf: str = None,
        edge_colors: str | np.ndarray | pygfx.Color | Sequence[float] = "black",
        uniform_edge_color: bool = True,
        edge_width: float = 1.0,
        image: np.ndarray = None,
        point_rotations: float | np.ndarray = 0,
        point_rotation_mode: Literal["uniform", "vertex", "curve"] = "uniform",
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

        mode: one of: "markers", "simple", "gaussian", "image", default "markers"
            The scatter points mode, cannot be changed after the graphic has been created.

            * markers: represent points with various or custom markers, default
            * simple: all scatters points are simple circles
            * gaussian: each point is a gaussian blob
            * image: use an image for each point, pass an array to the `image` kwarg, these are also called sprites

        markers: None | str | np.ndarray | Sequence[str], default "o"
            The shape of the markers when `mode` is "markers"

            Supported values:

            * A string from pygfx.MarkerShape enum
            * Matplotlib compatible characters: "osD+x^v<>*".
            * Unicode symbols: "●○■♦♥♠♣✳▲▼◀▶".
            * Emojis: "❤️♠️♣️♦️💎💍✳️📍".
            * A string containing the value "custom". In this case, WGSL code defined by ``custom_sdf`` will be used.

        uniform_marker: bool, default False
            Use the same marker for all points. Only valid when `mode` is "markers". Useful if you need to use
            the same marker for all points and want to save GPU RAM.

        custom_sdf: str = None,
            The SDF code for the marker shape when the marker is set to custom.
            Can be used when `mode` is "markers".

            Negative values are inside the shape, positive values are outside the
            shape.

            The SDF's takes in two parameters `coords: vec2<f32>` and `size: f32`.
            The first is a WGSL coordinate and `size` is the overall size of
            the texture. The returned value should be the signed distance from
            any edge of the shape. Distances (positive and negative) that are
            less than half the `edge_width` in absolute terms will be colored
            with the `edge_color`. Other negative distances will be colored by
            `colors`.

        edge_colors: str | np.ndarray | pygfx.Color | Sequence[float], default "black"
            edge color of the markers, used when `mode` is "markers"

        uniform_edge_color: bool, default True
            Set the same edge color for all markers. Useful for saving GPU RAM.

        edge_width: float = 1.0,
            Width of the marker edges. used when `mode` is "markers".

        image: ArrayLike, optional
            renders an image at the scatter points, also known as sprites.
            The image color is multiplied with the point's "normal" color.

        point_rotations: float | ArrayLike = 0,
            The rotation of the scatter points in radians. Default 0. A single float rotation value can be set on all
            points, or an array of rotation values can be used to set per-point rotations

        point_rotation_mode: one of: "uniform" | "vertex" | "curve", default "uniform"
            * uniform: set the same rotation for every point, useful to save GPU RAM
            * vertex: set per-vertex rotations
            * curve: The rotation follows the curve of the line defined by the points (in screen space)

        sizes: float or iterable of float, optional, default 1.0
            sizes of the scatter points

        uniform_size: bool, default False
            if True, uses a uniform buffer for the scatter point sizes. Useful if you need to
            save GPU VRAM when all points have the same size.

        size_space: str, default "screen"
            coordinate space in which the size is expressed, one of ("screen", "world", "model")

        isolated_buffer: bool, default True
            whether the buffers should be isolated from the user input array.
            Generally always ``True``, ``False`` is for rare advanced use if you have large arrays.

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
            depth_compare="<=",
        )

        self._markers: VertexMarkers | UniformMarker | None = None
        self._edge_colors: UniformEdgeColor | VertexColors | None = None
        self._edge_width: EdgeWidth | None = None
        self._point_rotations: VertexRotations | UniformRotations | None = None
        self._image: TextureArray | None = None

        # material cannot be changed after the ScatterGraphic is created
        self._mode = mode
        match self.mode:
            case "markers":
                # default
                material = pygfx.PointsMarkerMaterial

                if uniform_marker:
                    if not isinstance(markers, str):
                        raise TypeError(
                            "must pass a single <str> marker if uniform_marker is True"
                        )

                    self._markers = UniformMarker(markers)

                    material_kwargs["marker_mode"] = pygfx.MarkerMode.uniform
                    material_kwargs["marker"] = self._markers.value
                else:
                    material_kwargs["marker_mode"] = pygfx.MarkerMode.vertex

                    self._markers = VertexMarkers(markers, n_datapoints)

                    geo_kwargs["markers"] = self._markers.buffer

                if edge_colors is None:
                    # interpret as no edge color
                    edge_colors = (0, 0, 0, 0)

                if uniform_edge_color:
                    if not isinstance(edge_colors, (str, pygfx.Color)):
                        if len(edge_colors) not in [3, 4]:
                            raise TypeError(
                                f"if `uniform_edge_color` is True, then `edge_color` must be a str, pygfx.Color, "
                                f"or an RGB(A) tuple, list, array representation of a single color. You have passed: "
                                f"{edge_colors}"
                            )

                    self._edge_colors = UniformEdgeColor(edge_colors)
                    material_kwargs["edge_color"] = self._edge_colors.value
                    material_kwargs["edge_color_mode"] = pygfx.ColorMode.uniform
                else:
                    self._edge_colors = VertexColors(
                        edge_colors, n_datapoints, property_name="edge_colors"
                    )
                    material_kwargs["edge_color_mode"] = pygfx.ColorMode.vertex
                    geo_kwargs["edge_colors"] = self._edge_colors.buffer

                self._edge_width = EdgeWidth(edge_width)
                material_kwargs["edge_width"] = self._edge_width.value
                material_kwargs["custom_sdf"] = custom_sdf

            case "simple":
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

                # create texture array with normalized image
                self._image = TextureArray(
                    image / np.nanmax(image), property_name="image"
                )

                material_kwargs["sprite"] = self._image.buffer[0, 0]

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
            self._sizes = VertexPointSizes(sizes, n_datapoints=n_datapoints)
            geo_kwargs["sizes"] = self.sizes.buffer

        match point_rotation_mode:
            case pygfx.enums.RotationMode.vertex:
                self._point_rotations = VertexRotations(
                    point_rotations, n_datapoints=n_datapoints
                )
                geo_kwargs["rotations"] = self._point_rotations.buffer

            case pygfx.enums.RotationMode.uniform:
                self._point_rotations = UniformRotations(point_rotations)

            case pygfx.enums.RotationMode.curve:
                pass  # nothing special for curve rotation mode

            case _:
                raise ValueError(
                    f"`point_rotation_mode` must be one of: {pygfx.enums.RotationMode}, "
                    f"you have passed: {point_rotation_mode}"
                )

        material_kwargs["rotation_mode"] = point_rotation_mode
        material_kwargs["size_space"] = self.size_space

        world_object = pygfx.Points(
            pygfx.Geometry(**geo_kwargs),
            material=material(**material_kwargs),
        )

        self._set_world_object(world_object)

    @property
    def mode(self) -> str:
        """scatter point display mode"""
        return self._mode

    @property
    def markers(self) -> str | VertexMarkers | None:
        """markers if mode is 'marker'"""
        if isinstance(self._markers, VertexMarkers):
            return self._markers
        elif isinstance(self._markers, UniformMarker):
            return self._markers.value

    @markers.setter
    def markers(self, value: str | np.ndarray[str] | Sequence[str]):
        if self.mode != "markers":
            raise AttributeError(
                f"scatter plot is: {self.mode}. The mode must be 'markers' to set the markers"
            )
        if isinstance(self._markers, VertexMarkers):
            self._markers[:] = value
        elif isinstance(self._markers, UniformMarker):
            self._markers.set_value(self, value)

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
            raise AttributeError(
                f"scatter plot is: {self.mode}. The mode must be 'markers' to set the edge_colors"
            )

        if isinstance(self._edge_colors, VertexColors):
            self._edge_colors[:] = value

        elif isinstance(self._edge_colors, UniformEdgeColor):
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
            raise AttributeError(
                f"scatter plot is: {self.mode}. The mode must be 'markers' to set the edge_width"
            )

        self._edge_width.set_value(self, value)

    @property
    def point_rotation_mode(self) -> str:
        """point rotation mode, read-only, one of 'uniform', 'vertex', or 'curve'"""
        return self.world_object.material.rotation_mode

    @property
    def point_rotations(self) -> VertexRotations | float | None:
        """rotation of each point, in radians, if `point_rotation_mode` is 'uniform' or 'vertex'"""

        if isinstance(self._point_rotations, VertexRotations):
            return self._point_rotations

        elif isinstance(self._point_rotations, UniformRotations):
            return self._point_rotations.value

    @point_rotations.setter
    def point_rotations(self, value: float | np.ndarray[float]):
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
        return self._image

    @image.setter
    def image(self, data):
        if self.mode != "image":
            raise AttributeError(
                f"scatter plot is: {self.mode}. The mode must be 'image' to set the image"
            )

        self._image[:] = data

    @property
    def sizes(self) -> VertexPointSizes | float:
        """Get or set the scatter point size(s)"""
        if isinstance(self._sizes, VertexPointSizes):
            return self._sizes

        elif isinstance(self._sizes, UniformSize):
            return self._sizes.value

    @sizes.setter
    def sizes(self, value):
        if isinstance(self._sizes, VertexPointSizes):
            self._sizes[:] = value

        elif isinstance(self._sizes, UniformSize):
            self._sizes.set_value(self, value)
