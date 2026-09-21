from typing import Literal, Sequence

import numpy as np
import cmap as cmap_lib

import pygfx
from pygfx.geometries.utils import merge as merge_geometries

from ._base import Graphic
from ._vectors import generate_cap, generate_torso
from .features import (
    STALK_SEGMENTS,
    StreamAlpha,
    StreamAlphaMode,
    StreamCmap,
    StreamCmapRange,
    StreamCmapTransform,
    StreamColor,
    StreamDirections,
    StreamMaxLength,
    StreamPositions,
    StreamSeparatingDistance,
    StreamSeparatingDistanceRatio,
    StreamSize,
    StreamSizeSpace,
    StreamThickness,
    VectorDirections,
    arrows_along_streamline,
    interpolate_grid,
    mat_compose,
    place_streamlines,
    positions_to_grid,
    quat_from_vecs,
)
from ..utils import global_config
from ..utils.types import ColorLike, ColormapLike

ARROW_SHAPE_KEYS = {"cone_radius", "cone_height", "stalk_length", "gap"}


def derive_arrow_shape(size: float) -> dict:
    """shape of one arrow from the arc length it takes up, the three lengths summing to it"""

    cone_height = size * 0.15

    return {
        # longer than it is wide, so the tip of the arrowhead is sharp
        "cone_radius": cone_height * 0.45,
        "cone_height": cone_height,
        "stalk_length": size * 0.75,
        "gap": size * 0.1,
    }


def create_arrowhead_geometry(
    cone_radius: float = 1.0,
    cone_height: float = 0.5,
    segments: int = 12,
):
    """
    Generate the mesh for an arrowhead pointing in the direction [0, 0, 1], the +z direction.

    Parameters
    ----------
    cone_radius:
        radius of the bottom of the cone

    cone_height:
        height of the cone

    segments:
        number of mesh segments, more looks nicer but is also more expensive to render, 12 looks good enough.

    """

    radius_top = 0  # radius top = 0 means the cylinder becomes a cone

    cone = generate_torso(
        cone_radius, radius_top, cone_height, segments, 1, 0.0, np.pi * 2
    )
    cap = generate_cap(
        cone_radius, -cone_height / 2, segments, 0.0, np.pi * 2, up=False
    )

    positions, normals, texcoords, indices = merge_geometries([cone, cap])

    return positions, indices.reshape((-1, 3))


def merge_arrowheads(
    positions: np.ndarray,
    directions: np.ndarray,
    cone_radius: float,
    cone_height: float,
):
    """
    Generate one mesh holding an arrowhead at every position, each pointing along its direction.

    Unlike VectorsGraphic these are copies of the arrowhead rather than instances of it, because
    pygfx indexes texcoords by vertex and not by instance, so every instance of one mesh would
    take the same color from the colormap.

    Parameters
    ----------
    positions:
        center of each arrowhead, shape [n_arrows, 3]

    directions:
        direction each arrowhead points in, shape [n_arrows, 3]

    cone_radius:
        radius of the bottom of the cone

    cone_height:
        height of the cone

    """

    template, indices = create_arrowhead_geometry(cone_radius, cone_height)

    rotations = quat_from_vecs(VectorDirections.init_direction, directions)
    transforms = mat_compose(positions, rotations, np.ones(len(positions))).reshape(
        -1, 4, 4
    )

    # one rotated and translated copy of the template per arrow, [n_arrows, n_vertices, 3]
    vertices = (
        np.einsum("aij,vj->avi", transforms[:, :3, :3], template)
        + transforms[:, None, :3, 3]
    )
    offsets = (np.arange(len(positions)) * len(template))[:, None, None]

    return (
        vertices.reshape(-1, 3).astype(np.float32),
        (indices[None] + offsets).reshape(-1, 3).astype(np.int32),
    )


@global_config.register
class StreamGraphic(Graphic):
    _features = {
        "positions": StreamPositions,
        "directions": StreamDirections,
        "color": (StreamColor, None),
        "cmap": (StreamCmap, None),
        "cmap_transform": (StreamCmapTransform, None),
        "cmap_range": (StreamCmapRange, None),
        "thickness": StreamThickness,
        "size_space": StreamSizeSpace,
        "separating_distance": StreamSeparatingDistance,
        "separating_distance_ratio": StreamSeparatingDistanceRatio,
        "max_length": StreamMaxLength,
        "size": StreamSize,
    }

    @global_config.declare(
        "color", "cmap", "thickness", "size_space", "separating_distance_ratio"
    )
    def __init__(
        self,
        positions: np.ndarray | Sequence[float],
        directions: np.ndarray | Sequence[float],
        color: ColorLike = "w",
        cmap: ColormapLike | None = None,
        cmap_transform: np.ndarray | None = None,
        cmap_range: tuple[float, float] | None = None,
        thickness: float = None,
        size_space: Literal["screen", "world", "model"] = "world",
        separating_distance: float = None,
        separating_distance_ratio: float = 0.5,
        max_length: float = None,
        size: float = None,
        arrow_shape_options: dict = None,
        **kwargs,
    ):
        """
        Create graphic that draws streamlines of a vector field. Similar to Mathematica StreamPlot.

        Parameters
        ----------
        positions: np.ndarray | Sequence[float]
            positions of the field samples, array-like, must lie on a regular grid, shape must be [n, 2] or [n, 3]
            where n is the number of samples.

        directions: np.ndarray | Sequence[float]
            field vector at each position, array-like, shape must be the same as ``positions``.

        color: str | pygfx.Color | Sequence[float] | np.ndarray, default "w"
            color of the streamlines

        cmap: ColormapLike, optional
            Apply a colormap to the streamlines instead of assigning a color manually, this
            overrides any argument passed to "color". For supported colormaps see the
            ``cmap`` library catalogue: https://cmap-docs.readthedocs.io/en/stable/catalog/

        cmap_transform: np.ndarray, optional
            1D array-like of numerical values, one per field position, if provided these values are used to map the
            colors from the cmap. The arrow length follows it as well, so a low value gives a short arrow. Defaults
            to the magnitude of the field, which is what Mathematica colors by.

        cmap_range: (float, float), optional
            the (min, max) of the cmap_transform mapped onto the colormap and onto the arrow length, defaults to the
            transform's own range

        thickness: float or None
            Width of the arrow stalks, in the coordinate space given by ``size_space``.
            Derived from the arrow shape if not provided.

        size_space: str, default "world"
            coordinate space in which the stalk thickness is expressed ("screen", "world", "model"). The arrowheads
            are always in world space, so "world" keeps the whole arrow in proportion at any zoom.

        separating_distance: float or None
            Distance a new streamline keeps from the streamlines already placed, i.e. d_sep, which is what sets the
            density. Estimated from density if not provided.

        separating_distance_ratio: float, default 0.5
            How close a growing streamline may come to one already placed, as a fraction of ``separating_distance``,
            i.e. d_test / d_sep. Lower values give longer streamlines.

        max_length: float or None
            Maximum arc length of one streamline. Unbounded if not provided, so a streamline stops only where it
            leaves the field, stalls, or meets another streamline.

        size: float or None
            Arc length taken up by one arrow and the gap after it in world space, i.e. the spacing between
            consecutive arrowheads along a streamline. Derived from ``separating_distance`` if not provided.

        arrow_shape_options: dict
            dict with the following fields that directly describes the shape of the arrows.
            Overrides ``size`` argument.

                * cone_radius
                * cone_height
                * stalk_length
                * gap

        **kwargs
            passed to :class:`.Graphic`

        """

        super().__init__(**kwargs)

        if cmap_transform is not None and cmap is None:
            raise ValueError("must pass `cmap` if passing `cmap_transform`")

        positions = np.asarray(positions)
        directions = np.asarray(directions)

        if positions.shape != directions.shape:
            raise ValueError(
                f"positions.shape != directions.shape: {positions.shape} != {directions.shape}\n"
                f"They must be of the same shape"
            )

        self._positions = StreamPositions(positions)
        self._directions = StreamDirections(directions)

        if separating_distance is None:
            # guess from density, one streamline per row of field samples
            # take unique to get the density along x, same for y and z
            unique = [np.unique(self._positions[:, dim]) for dim in range(3)]
            separating_distance = np.mean(
                [np.diff(u).mean() for u in unique if u.size > 1]
            )

        self._separating_distance = StreamSeparatingDistance(separating_distance)
        self._separating_distance_ratio = StreamSeparatingDistanceRatio(
            separating_distance_ratio
        )
        self._max_length = StreamMaxLength(max_length)

        if size is None:
            # arrows a little longer than the streamlines are apart, so the stalks read as the
            # curved lines they are rather than as a field of darts
            size = 1.6 * self._separating_distance.value

        self._size = StreamSize(size)

        if arrow_shape_options is not None:
            if set(arrow_shape_options.keys()) != ARROW_SHAPE_KEYS:
                raise KeyError(
                    f"`arrow_shape_options` must be a dict with the following keys: {ARROW_SHAPE_KEYS}.\n"
                    f"You have passed: {arrow_shape_options}"
                )

        self._arrow_shape_options = arrow_shape_options

        # defaults are None
        self._color = None
        self._cmap = None
        self._cmap_transform = None
        self._cmap_range = None

        if cmap is not None:
            # if a cmap is specified it overrides the color argument
            self._cmap, self._cmap_transform, self._cmap_range = (
                self._create_cmap_features(cmap, cmap_transform, cmap_range)
            )

        else:
            # no cmap given
            self._color = StreamColor(color)

        if thickness is None:
            # half the arrowhead's radius, thin enough that the stalk reads as a line
            thickness = self.arrow_shape_options["cone_radius"] / 2

        self._thickness = StreamThickness(thickness)
        self._size_space = StreamSizeSpace(size_space)

        stalk_geometry, head_geometry = self._make_geo()

        self._stalks = pygfx.Line(stalk_geometry, self._make_line_material())
        self._heads = pygfx.Mesh(head_geometry, self._make_mesh_material())

        # the group has no material, so alpha has to reach both of its children
        self._alpha = StreamAlpha(self.alpha)
        self._alpha_mode = StreamAlphaMode(self.alpha_mode)

        world_object = pygfx.Group()
        world_object.add(self._stalks, self._heads)

        self._set_world_object(world_object)

    @property
    def _materials(self) -> tuple[pygfx.Material, pygfx.Material]:
        # the group has no material, a property that sets one must reach both children
        return self._stalks.material, self._heads.material

    def _create_cmap_features(
        self, cmap, cmap_transform, cmap_range
    ) -> tuple[StreamCmap, StreamCmapTransform, StreamCmapRange]:
        cmap = StreamCmap(cmap)

        if cmap_transform is None:
            # default transform is the magnitude of the field
            cmap_transform = np.linalg.norm(self._directions.value, axis=1)

        cmap_transform = StreamCmapTransform(cmap_transform)

        if cmap_range is None:
            # default range is the transform's own (min, max)
            cmap_range = cmap_transform.value.min(), cmap_transform.value.max()

        return cmap, cmap_transform, StreamCmapRange(cmap_range)

    def _get_material_kwargs(self) -> dict:
        # material kwargs shared by the stalk line and the arrowhead mesh, the color mode is
        # determined by the current color/cmap state
        kwargs = dict(
            pick_write=True,
            depth_compare="<=",
            opacity=self.alpha,
            alpha_mode=self.alpha_mode,
        )

        if self._cmap is not None:
            kwargs["color_mode"] = "vertex_map"
            kwargs["map"] = self.cmap.to_pygfx()
            kwargs["maprange"] = self._cmap_range.value
        else:
            kwargs["color_mode"] = "uniform"
            kwargs["color"] = self.color

        return kwargs

    def _make_line_material(self) -> pygfx.LineMaterial:
        return pygfx.LineMaterial(
            thickness=self.thickness,
            thickness_space=self.size_space,
            aa=self.alpha_mode in ("blend", "weighted_blend"),
            **self._get_material_kwargs(),
        )

    def _make_mesh_material(self) -> pygfx.MeshBasicMaterial:
        return pygfx.MeshBasicMaterial(**self._get_material_kwargs())

    def _make_geo(self) -> tuple[pygfx.Geometry, pygfx.Geometry]:
        # place the streamlines and build both geometries from the current feature values
        field, origin, spacing = positions_to_grid(
            self._positions.value, self._directions.value
        )

        paths = place_streamlines(
            field,
            origin,
            spacing,
            separating_distance=self.separating_distance,
            test_distance=self.separating_distance * self.separating_distance_ratio,
            max_length=self.max_length,
        )

        # the same scalar field and range drive both the color and the arrow length, so one knob
        # controls both. with no cmap there is no range to share, so use what it would default to
        if self._cmap is None:
            transform = np.linalg.norm(field, axis=-1)
            low, high = transform.min(), transform.max()
        else:
            transform, _, _ = positions_to_grid(
                self._positions.value, self._cmap_transform.value
            )
            low, high = self._cmap_range.value

        span = high - low if high > low else 1.0
        shape_options = self.arrow_shape_options

        stalks, tips = list(), list()
        for path in paths:
            # a slow arrow has a shorter stalk, so the arrow length encodes the transform too.
            # the square root keeps the typical stalk long enough to read as a line, which a few
            # fast samples would otherwise set the scale for
            values = interpolate_grid(transform, origin, spacing, path)
            scales = np.sqrt(np.clip((values - low) / span, 0, 1))
            arrows = arrows_along_streamline(path, scales, shape_options)

            if arrows is None:
                # this streamline is shorter than one arrow
                continue

            stalks.append(arrows[0])
            tips.append(arrows[1])

        if len(stalks) == 0:
            raise ValueError(
                "no streamline in this field is long enough to draw an arrow on, pass a smaller "
                "`size` or `separating_distance`"
            )

        stalks = np.concatenate(stalks)
        tips = np.concatenate(tips)

        # the field vector at each arrowhead orients it, and is what a pick reports
        self._arrow_positions = tips
        self._arrow_directions = interpolate_grid(field, origin, spacing, tips)

        # a row of nan between arrows so the line material breaks instead of joining them
        stalk_positions = np.full(
            (len(stalks), STALK_SEGMENTS + 1, 3), np.nan, dtype=np.float32
        )
        stalk_positions[:, :-1] = stalks

        head_positions, head_indices = merge_arrowheads(
            tips,
            self._arrow_directions,
            shape_options["cone_radius"],
            shape_options["cone_height"],
        )
        self._faces_per_head = len(head_indices) // len(tips)

        stalk_geometry = pygfx.Geometry(positions=stalk_positions.reshape(-1, 3))
        head_geometry = pygfx.Geometry(positions=head_positions, indices=head_indices)

        if self._cmap is not None:
            # one texcoord per stalk point, and the value at its own tip for a whole arrowhead
            stalk_texcoords = np.zeros(
                (len(stalks), STALK_SEGMENTS + 1), dtype=np.float32
            )
            stalk_texcoords[:, :-1] = interpolate_grid(
                transform, origin, spacing, stalks.reshape(-1, 3)
            ).reshape(len(stalks), STALK_SEGMENTS)

            head_texcoords = np.repeat(
                interpolate_grid(transform, origin, spacing, tips),
                len(head_positions) // len(tips),
            )

            stalk_geometry.texcoords = pygfx.Buffer(stalk_texcoords.reshape(-1))
            head_geometry.texcoords = pygfx.Buffer(head_texcoords.astype(np.float32))

        return stalk_geometry, head_geometry

    def _fpl_rebuild(self):
        # the number of arrows changes with any property that moves the streamlines or lays the
        # arrows out again, so both geometries are replaced rather than updated in place
        stalk_geometry, head_geometry = self._make_geo()

        self._stalks.geometry = stalk_geometry
        self._heads.geometry = head_geometry

    @property
    def positions(self) -> StreamPositions:
        """Field sample positions"""
        return self._positions

    @positions.setter
    def positions(self, new_positions):
        self._positions.set_value(self, new_positions)

    @property
    def directions(self) -> StreamDirections:
        """Field vector at each position"""
        return self._directions

    @directions.setter
    def directions(self, new_directions):
        self._directions.set_value(self, new_directions)

    @property
    def color(self) -> pygfx.Color | None:
        """Get or set the color, ``None`` while a cmap is set"""
        if self._color is not None:
            return self._color.value

    @color.setter
    def color(self, value: ColorLike):
        if self._color is not None:
            self._color.set_value(self, value)
            return

        # switching away from a cmap, back to a uniform color and neither geometry needs texcoords
        self._cmap.clear_event_handlers()
        self._cmap_transform.clear_event_handlers()
        self._cmap_range.clear_event_handlers()
        self._cmap = None
        self._cmap_transform = None
        self._cmap_range = None

        self._color = StreamColor(value)

        for material in self._materials:
            material.map = None
            material.color = self._color.value
            material.color_mode = "uniform"

        self._stalks.geometry.texcoords = None
        self._heads.geometry.texcoords = None

    @property
    def cmap(self) -> cmap_lib.Colormap | None:
        """
        Get or set the colormap, ``None`` while a color is set

        For supported colormaps see the ``cmap`` library catalogue: https://cmap-docs.readthedocs.io/en/stable/catalog/
        """
        if self._cmap is not None:
            return self._cmap.value

    @cmap.setter
    def cmap(self, value: ColormapLike):
        if self._cmap is not None:
            self._cmap.set_value(self, value)
            return

        # need to create cmap features
        self._color.clear_event_handlers()
        self._color = None

        self._cmap, self._cmap_transform, self._cmap_range = self._create_cmap_features(
            value, None, None
        )

        for material in self._materials:
            material.map = self._cmap.value.to_pygfx()
            material.maprange = self._cmap_range.value
            material.color_mode = "vertex_map"

        # neither geometry has texcoords yet, they are built along with the streamlines
        self._fpl_rebuild()

    @property
    def cmap_transform(self) -> np.ndarray | None:
        """Get or set the per-position values that the colors are mapped from"""
        if self._cmap_transform is not None:
            return self._cmap_transform.value

    @cmap_transform.setter
    def cmap_transform(self, value: np.ndarray):
        if self._cmap is None:
            raise AttributeError("Must set `cmap` before setting `cmap_transform`")

        self._cmap_transform.set_value(self, value)
        # new default range from the new transform's (min, max)
        transform = self._cmap_transform.value
        self._cmap_range.set_value(self, (transform.min(), transform.max()))

    @property
    def cmap_range(self) -> tuple[float, float] | None:
        """Get or set the (min, max) of the cmap_transform that is mapped onto the colormap"""
        if self._cmap_range is not None:
            return self._cmap_range.value

    @cmap_range.setter
    def cmap_range(self, value: tuple[float, float]):
        if self._cmap is None:
            raise AttributeError("Must set `cmap` before setting `cmap_range`")

        self._cmap_range.set_value(self, value)

    @property
    def thickness(self) -> float:
        """Get or set the width of the arrow stalks"""
        return self._thickness.value

    @thickness.setter
    def thickness(self, value: float):
        self._thickness.set_value(self, value)

    @property
    def size_space(self) -> str:
        """
        The coordinate space in which the stalk thickness is expressed ('screen', 'world', 'model')

        See https://docs.pygfx.org/stable/_autosummary/utils/utils/enums/pygfx.utils.enums.CoordSpace.html#pygfx.utils.enums.CoordSpace for available options.
        """
        return self._size_space.value

    @size_space.setter
    def size_space(self, value: str):
        self._size_space.set_value(self, value)

    @property
    def separating_distance(self) -> float:
        """Get or set the distance a streamline keeps from the others, i.e. d_sep"""
        return self._separating_distance.value

    @separating_distance.setter
    def separating_distance(self, value: float):
        self._separating_distance.set_value(self, value)

    @property
    def separating_distance_ratio(self) -> float:
        """Get or set how close a streamline may come to another, i.e. d_test / d_sep"""
        return self._separating_distance_ratio.value

    @separating_distance_ratio.setter
    def separating_distance_ratio(self, value: float):
        self._separating_distance_ratio.set_value(self, value)

    @property
    def max_length(self) -> float | None:
        """Get or set the maximum arc length of one streamline, ``None`` for unbounded"""
        return self._max_length.value

    @max_length.setter
    def max_length(self, value: float | None):
        self._max_length.set_value(self, value)

    @property
    def size(self) -> float:
        """Get or set the size of one arrow in world space"""
        return self._size.value

    @size.setter
    def size(self, value: float):
        # a new size derives a whole arrow shape, replacing any explicit arrow_shape_options
        self._arrow_shape_options = None
        self._size.set_value(self, value)

    @property
    def arrow_shape_options(self) -> dict:
        """Shape of one arrow, derived from ``size`` unless it was passed explicitly"""
        if self._arrow_shape_options is not None:
            return self._arrow_shape_options

        return derive_arrow_shape(self.size)

    def format_pick_info(self, pick_info: dict) -> str:
        if "face_index" in pick_info:
            # an arrowhead, whose cone is one run of faces
            index = pick_info["face_index"] // self._faces_per_head
        else:
            # a stalk, whose points are one run of vertices, the last the nan separator
            index = pick_info["vertex_index"] // (STALK_SEGMENTS + 1)

        info = (
            f"position: {self._arrow_positions[index]}\n"
            f"direction: {self._arrow_directions[index]}"
        )

        return info
