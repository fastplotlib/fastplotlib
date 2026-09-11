from typing import *

import numpy as np
import pygfx

from ._positions_base import PositionsGraphic
from .features import (
    VertexPointSizes,
    UniformSize,
    VertexColors,
    VertexMarkers,
    UniformMarker,
    UniformEdgeColor,
    EdgeWidth,
    UniformRotations,
    VertexRotations,
    TextureArray,
)
from .features.types import ColorLike, MultiColorLike, ColormapLike
from .features.utils import is_single_color


class ScatterGraphic(PositionsGraphic):
    _features = {
        "sizes": (VertexPointSizes, UniformSize),
        "markers": (VertexMarkers, UniformMarker, None),
        "edge_colors": (UniformEdgeColor, VertexColors, None),
        "edge_width": (EdgeWidth, None),
        "image": (TextureArray, None),
        "point_rotations": (UniformRotations, VertexRotations, None),
    }

    def __init__(
        self,
        data: Any,
        colors: ColorLike | MultiColorLike = "w",
        cmap: ColormapLike | None = None,
        cmap_transform: np.ndarray | None = None,
        cmap_range: tuple[float, float] | None = None,
        mode: Literal["markers", "simple", "gaussian", "image"] = "markers",
        markers: str | np.ndarray | Sequence[str] = "o",
        custom_sdf: str = None,
        edge_colors: ColorLike | MultiColorLike | None = "black",
        edge_width: float = 1.0,
        image: np.ndarray = None,
        point_rotations: float | np.ndarray | None = None,
        sizes: float | np.ndarray | Sequence[float] = 5,
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

        cmap_range: (float, float), optional
            the (min, max) of the cmap_transform mapped onto the colormap, defaults to the transform's own range

        mode: one of: "markers", "simple", "gaussian", "image", default "markers"
            The scatter points mode, cannot be changed after the graphic has been created.

            * markers: represent points with various or custom markers, default
            * simple: all scatters points are simple circles
            * gaussian: each point is a gaussian blob
            * image: use an image for each point, pass an array to the `image` kwarg, these are also called sprites

        markers: str | np.ndarray | Sequence[str], default "o"
            The shape of the markers when `mode` is "markers". Specify a single marker to use the same
            marker for all points, or a Sequence of markers for per-vertex markers.

            Supported values:

            * A string from pygfx.MarkerShape enum
            * Matplotlib compatible characters: "osD+x^v<>*".
            * Unicode symbols: "●○■♦♥♠♣✳▲▼◀▶".
            * Emojis: "❤️♠️♣️♦️💎💍✳️📍".
            * A string containing the value "custom". In this case, WGSL code defined by ``custom_sdf`` will be used.

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

        edge_colors: ColorLike, MultiColorLike, or None, default "black"
            edge color(s) of the markers, used when `mode` is "markers". Specify a single color to use the
            same edge color for all markers, or a Sequence of colors for per-vertex edge colors. Pass
            ``None`` for no edge color.

        edge_width: float = 1.0,
            Width of the marker edges. used when `mode` is "markers".

        image: array-like, optional
            renders an image at the scatter points, also known as sprites.
            The image color is multiplied with the point's "normal" color.

        point_rotations: float, array-like, or None, default None
            The rotation of the scatter points in radians. The rotation mode is determined automatically from
            the value: pass ``None`` (default) for "curve" mode, where each point's rotation follows the curve
            of the data (in screen space); a single float for the same rotation on every point ("uniform"); or
            an array of rotation values for per-point rotations ("vertex").

        sizes: float, np.ndarray, or Sequence[float], default 5
            size(s) of the scatter points. Specify a single size to use the same size for all points, or a
            Sequence of sizes for per-point sizes.

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
            cmap_range=cmap_range,
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
                self._markers = self._create_markers_buffer(markers)
                self._edge_colors = self._create_edge_colors_buffer(edge_colors)
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

        self._sizes = self._create_sizes_buffer(sizes)
        self._point_rotations = self._create_point_rotations_buffer(point_rotations)

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
            kwargs["rotation"] = self._point_rotations.value
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

    def _create_markers_buffer(self, markers) -> UniformMarker | VertexMarkers:
        # creates either a UniformMarker or VertexMarkers based on the given `markers`

        if isinstance(markers, (VertexMarkers, UniformMarker)):
            # share buffer with existing markers instance
            return markers

        # a single marker is a str, a sequence is one marker per datapoint
        if isinstance(markers, str):
            return UniformMarker(markers)

        else:
            return VertexMarkers(markers, n_datapoints=self._data.value.shape[0])

    def _create_edge_colors_buffer(self, edge_colors) -> UniformEdgeColor | VertexColors:
        # creates either a UniformEdgeColor or VertexColors based on the given `edge_colors`

        if edge_colors is None:
            # interpret as no edge color
            edge_colors = (0, 0, 0, 0)

        if isinstance(edge_colors, (VertexColors, UniformEdgeColor)):
            # share buffer with existing edge_colors instance
            return edge_colors

        # determine if a single or multiple colors were passed and decide edge_color_mode
        if is_single_color(edge_colors):
            # one color specified as a str or pygfx.Color, or one color specified with RGB(A) values
            return UniformEdgeColor(edge_colors)

        else:
            # sequence of colors, one edge color per datapoint
            return VertexColors(
                edge_colors,
                n_colors=self._data.value.shape[0],
                property_name="edge_colors",
            )

    def _create_sizes_buffer(self, sizes) -> UniformSize | VertexPointSizes:
        # creates either a UniformSize or VertexPointSizes based on the given `sizes`

        if isinstance(sizes, (VertexPointSizes, UniformSize)):
            # share buffer with existing sizes instance
            return sizes

        # a single size is a scalar, a sequence is one size per datapoint
        if isinstance(sizes, (np.ndarray, list, tuple)):
            return VertexPointSizes(sizes, n_datapoints=self._data.value.shape[0])

        else:
            return UniformSize(sizes)

    def _create_point_rotations_buffer(
        self, point_rotations
    ) -> UniformRotations | VertexRotations | None:
        # None -> curve mode (no feature, rotation follows the data curve), a single value ->
        # uniform, a sequence -> vertex

        if isinstance(point_rotations, (VertexRotations, UniformRotations)):
            # share buffer with existing point_rotations instance
            return point_rotations

        if point_rotations is None:
            return None

        if isinstance(point_rotations, (np.ndarray, list, tuple)):
            return VertexRotations(point_rotations, n_datapoints=self._data.value.shape[0])

        else:
            return UniformRotations(point_rotations)

    @property
    def mode(self) -> str:
        """scatter point display mode"""
        return self._mode

    @property
    def markers(self) -> str | VertexMarkers | None:
        """Get or set the markers, if mode is 'markers'"""
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

        # currently per-vertex: stay per-vertex, broadcasting a single marker or setting a sequence
        if isinstance(self._markers, VertexMarkers):
            self._markers.set_value(self, value)
            return

        # currently uniform: a single marker stays uniform
        if isinstance(value, str):
            self._markers.set_value(self, value)
            return

        # currently uniform and a sequence was passed: switch uniform -> vertex
        self._markers.clear_event_handlers()
        self._markers = self._create_markers_buffer(value)
        self.world_object.geometry.markers = self._markers._fpl_buffer
        self.world_object.material.marker_mode = "vertex"

    @property
    def edge_colors(self) -> VertexColors | pygfx.Color | None:
        """Get or set the marker edge colors, if mode is 'markers'"""

        if isinstance(self._edge_colors, VertexColors):
            return self._edge_colors

        elif isinstance(self._edge_colors, UniformEdgeColor):
            return self._edge_colors.value

    @edge_colors.setter
    def edge_colors(self, value: ColorLike | MultiColorLike | None):
        if self.mode != "markers":
            raise AttributeError(
                f"scatter plot is: {self.mode}. The mode must be 'markers' to set the edge_colors"
            )

        if value is None:
            # interpret as no edge color
            value = (0, 0, 0, 0)

        # currently per-vertex: stay per-vertex, broadcasting a single color or setting a sequence
        if isinstance(self._edge_colors, VertexColors):
            self._edge_colors.set_value(self, value)
            return

        # currently uniform: a single color stays uniform
        if is_single_color(value):
            self._edge_colors.set_value(self, value)
            return

        # currently uniform and a sequence was passed: switch uniform -> vertex
        self._edge_colors.clear_event_handlers()
        self._edge_colors = self._create_edge_colors_buffer(value)
        self.world_object.geometry.edge_colors = self._edge_colors._fpl_buffer
        self.world_object.material.edge_color_mode = "vertex"

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
        """Get or set the point rotations in radians; returns None in 'curve' mode"""

        if isinstance(self._point_rotations, VertexRotations):
            return self._point_rotations

        elif isinstance(self._point_rotations, UniformRotations):
            return self._point_rotations.value

    @point_rotations.setter
    def point_rotations(self, value: float | np.ndarray[tuple[int], np.dtype[np.number]] | None):
        # None selects curve mode, where the rotation follows the data curve
        if value is None:
            if self._point_rotations is not None:
                self._point_rotations.clear_event_handlers()
            self._point_rotations = None
            self.world_object.material.rotation_mode = "curve"
            self.world_object.geometry.rotations = None
            return

        # currently per-vertex: stay per-vertex, broadcasting a single value or setting a sequence
        if isinstance(self._point_rotations, VertexRotations):
            self._point_rotations.set_value(self, value)
            return

        # currently uniform: a single value stays uniform
        if isinstance(self._point_rotations, UniformRotations) and not isinstance(
            value, (np.ndarray, list, tuple)
        ):
            self._point_rotations.set_value(self, value)
            return

        # switch to the mode the value implies (from uniform, or from curve which has no feature)
        if self._point_rotations is not None:
            self._point_rotations.clear_event_handlers()

        self._point_rotations = self._create_point_rotations_buffer(value)

        if isinstance(self._point_rotations, VertexRotations):
            self.world_object.geometry.rotations = self._point_rotations._fpl_buffer
            self.world_object.material.rotation_mode = "vertex"
        else:
            self.world_object.material.rotation = self._point_rotations.value
            self.world_object.material.rotation_mode = "uniform"
            self.world_object.geometry.rotations = None

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
    def sizes(self, value: float | np.ndarray | Sequence[float]):
        # currently per-vertex: stay per-vertex, broadcasting a single value or setting a sequence
        if isinstance(self._sizes, VertexPointSizes):
            self._sizes.set_value(self, value)
            return

        # currently uniform: a single value stays uniform
        if not isinstance(value, (np.ndarray, list, tuple)):
            self._sizes.set_value(self, value)
            return

        # currently uniform and a sequence was passed: switch uniform -> vertex
        self._sizes.clear_event_handlers()
        self._sizes = self._create_sizes_buffer(value)
        self.world_object.geometry.sizes = self._sizes._fpl_buffer
        self.world_object.material.size_mode = "vertex"
