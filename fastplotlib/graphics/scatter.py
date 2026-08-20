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
    VertexCmapTransform,
    VertexMarkers,
    UniformMarker,
    UniformEdgeColor,
    EdgeWidth,
    UniformRotations,
    VertexRotations,
    TextureArray,
)
from .features.types import ColorLike, MultiColorLike, ColormapLike


class ScatterGraphic(PositionsGraphic):
    _features = {
        "data": VertexPositions,
        "sizes": (VertexPointSizes, UniformSize),
        "colors": (VertexColors, UniformColor),
        "cmap": (VertexCmap, None),
        "cmap_transform": (VertexCmapTransform, None),
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
        colors: ColorLike | MultiColorLike = "w",
        cmap: ColormapLike | None = None,
        cmap_transform: np.ndarray | None = None,
        mode: Literal["markers", "simple", "gaussian", "image"] = "markers",
        markers: str | np.ndarray | Sequence[str] = "o",
        uniform_marker: bool = True,
        custom_sdf: str = None,
        edge_colors: str | np.ndarray | pygfx.Color | Sequence[float] = "black",
        uniform_edge_color: bool = True,
        edge_width: float = 1.0,
        image: np.ndarray = None,
        point_rotations: float | np.ndarray = 0,
        point_rotation_mode: Literal["uniform", "vertex", "curve"] = "uniform",
        sizes: float | np.ndarray | Sequence[float] = 5,
        uniform_size: bool = True,
        size_space: str = "screen",
        **kwargs,
    ):
        """
        Create a Scatter Graphic, 2d or 3d

        Parameters
        ----------
        data: array-like
            Scatter data to plot, Can provide 2D, or a 3D data. 2D data must be of shape [n_points, 2].
            3D data must be of shape [n_points, 3]

        colors: ColorLike or MultiColorLike, default "w"
            specify colors as a single human-readable string, a single RGBA array,
            or a Sequence (array, tuple, or list) of strings or RGBA arrays

        cmap: ColormapLike, optional
            apply a colormap to the scatter instead of assigning colors manually, this
            overrides any argument passed to "colors".
            For supported colormaps see the ``cmap`` library catalogue:
            https://cmap-docs.readthedocs.io/en/stable/catalog/

        cmap_transform: np.ndarray, optional
            1D array-like or list of numerical values, these values are used to map the colors from the cmap

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

        uniform_marker: bool, default ``True``
            If ``True``, use the same marker for all points. Only valid when `mode` is "markers".
            Useful if you need to use the same marker for all points and want to save GPU RAM. If ``False``, you can
            set per-vertex markers.

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

        uniform_edge_color: bool, default ``True``
            Set the same edge color for all markers. Useful for saving GPU RAM. Set to ``False`` for per-vertex edge
            colors

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

        uniform_size: bool, default ``False``
            if ``True``, uses a uniform buffer for the scatter point sizes. Useful if you need to
            save GPU VRAM when all points have the same size. Set to ``False`` if you need per-vertex sizes.

        size_space: str, default "screen"
            coordinate space in which the size is expressed, one of ("screen", "world", "model")

        kwargs
            passed to :class:`.Graphic`

        """

        super().__init__(
            data=data,
            colors=colors,
            cmap=cmap,
            cmap_transform=cmap_transform,
            size_space=size_space,
            **kwargs,
        )

        n_datapoints = self.data.value.shape[0]

        self._markers: VertexMarkers | UniformMarker | None = None
        self._edge_colors: UniformEdgeColor | VertexColors | None = None
        self._edge_width: EdgeWidth | None = None
        self._point_rotations: VertexRotations | UniformRotations | None = None
        self._image: TextureArray | None = None
        self._custom_sdf: str | None = None

        # material cannot be changed after the ScatterGraphic is created
        self._mode = mode
        match self._mode:
            case "markers":
                if uniform_marker:
                    if not isinstance(markers, str):
                        raise TypeError(
                            "must pass a single <str> marker if uniform_marker is True"
                        )

                    self._markers = UniformMarker(markers)
                else:
                    self._markers = VertexMarkers(markers, n_datapoints)

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
                else:
                    self._edge_colors = VertexColors(
                        edge_colors, n_datapoints, property_name="edge_colors"
                    )

                self._edge_width = EdgeWidth(edge_width)
                self._custom_sdf = custom_sdf

            case "image":
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

        if uniform_size:
            self._sizes = UniformSize(sizes)
        else:
            self._sizes = VertexPointSizes(sizes, n_datapoints=n_datapoints)

        match point_rotation_mode:
            case pygfx.enums.RotationMode.vertex:
                self._point_rotations = VertexRotations(
                    point_rotations, n_datapoints=n_datapoints
                )

            case pygfx.enums.RotationMode.uniform:
                self._point_rotations = UniformRotations(point_rotations)

            case pygfx.enums.RotationMode.curve:
                pass  # nothing special for curve rotation mode

            case _:
                raise ValueError(
                    f"`point_rotation_mode` must be one of: {pygfx.enums.RotationMode}, "
                    f"you have passed: {point_rotation_mode}"
                )

        world_object = pygfx.Points(
            geometry=self._make_geo(),
            material=self._make_material(),
        )

        self._set_world_object(world_object)

    def _make_material(self) -> pygfx.PointsMaterial:
        # create the pygfx material, the material class is determined by the scatter mode
        material_cls = {
            "markers": pygfx.PointsMarkerMaterial,
            "simple": pygfx.PointsMaterial,
            "gaussian": pygfx.PointsGaussianBlobMaterial,
            "image": pygfx.PointsSpriteMaterial,
        }[self._mode]
        return material_cls(**self._get_material_kwargs())

    def _get_material_kwargs(self) -> dict:
        # pygfx points material kwargs assembled from the current feature state
        kwargs = super()._get_material_kwargs()
        kwargs["size_space"] = self.size_space

        if isinstance(self._sizes, UniformSize):
            kwargs["size_mode"] = pygfx.SizeMode.uniform
            kwargs["size"] = self.sizes
        else:
            kwargs["size_mode"] = pygfx.SizeMode.vertex

        if isinstance(self._point_rotations, VertexRotations):
            kwargs["rotation_mode"] = pygfx.enums.RotationMode.vertex
        elif isinstance(self._point_rotations, UniformRotations):
            kwargs["rotation_mode"] = pygfx.enums.RotationMode.uniform
        else:
            kwargs["rotation_mode"] = pygfx.enums.RotationMode.curve

        match self._mode:
            case "markers":
                if isinstance(self._markers, UniformMarker):
                    kwargs["marker_mode"] = pygfx.MarkerMode.uniform
                    kwargs["marker"] = self._markers.value
                else:
                    kwargs["marker_mode"] = pygfx.MarkerMode.vertex

                if isinstance(self._edge_colors, UniformEdgeColor):
                    kwargs["edge_color_mode"] = pygfx.ColorMode.uniform
                    kwargs["edge_color"] = self._edge_colors.value
                else:
                    kwargs["edge_color_mode"] = pygfx.ColorMode.vertex

                kwargs["edge_width"] = self._edge_width.value
                kwargs["custom_sdf"] = self._custom_sdf

            case "image":
                kwargs["sprite"] = self._image.buffer[0, 0]

        return kwargs

    def _get_geo_kwargs(self) -> dict:
        # pygfx points geometry kwargs assembled from the current feature state
        kwargs = super()._get_geo_kwargs()

        if isinstance(self._sizes, VertexPointSizes):
            kwargs["sizes"] = self._sizes._fpl_buffer

        if isinstance(self._point_rotations, VertexRotations):
            kwargs["rotations"] = self._point_rotations._fpl_buffer

        if self._mode == "markers":
            if isinstance(self._markers, VertexMarkers):
                kwargs["markers"] = self._markers._fpl_buffer

            if isinstance(self._edge_colors, VertexColors):
                kwargs["edge_colors"] = self._edge_colors._fpl_buffer

        return kwargs

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
    def point_rotations(self, value: float | np.ndarray[tuple[int], np.dtype[np.number]]):
        if self.point_rotation_mode not in ["uniform", "vertex"]:
            raise AttributeError(
                f"point_rotation_mode is: {self.point_rotation_mode}. "
                f"it be 'uniform' or 'vertex' to set the `point_rotations`"
            )

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
        self._sizes.set_value(self, value)
