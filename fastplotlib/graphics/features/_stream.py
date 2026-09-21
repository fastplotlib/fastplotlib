from collections import deque
from itertools import product
from math import hypot

import numpy as np
import pygfx
import cmap as cmap_lib

from ._base import (
    GraphicFeature,
    GraphicFeatureEvent,
    block_reentrance,
)
from ._common import Alpha, AlphaMode
from ...utils.types import ColorLike, ColormapLike

# points along one arrow's stalk, a stalk is short enough that 8 follows its curve closely
STALK_SEGMENTS = 8

# tolerance in grid index space, so a point on the edge of the grid still counts as inside it
# despite the rounding in origin and spacing
GRID_TOLERANCE = 1e-4


def parse_field_array(value: np.ndarray, name: str) -> np.ndarray:
    """array-like of shape [n, 2] or [n, 3] -> float32 array of shape [n, 3]"""

    value = np.asarray(value, dtype=np.float32)

    if value.ndim != 2 or value.shape[1] not in (2, 3):
        raise ValueError(
            f"stream {name} must be of shape [n, 2] or [n, 3], you passed an array of "
            f"shape: {value.shape}"
        )

    if value.shape[1] == 2:
        value = np.column_stack([value, np.zeros(value.shape[0], dtype=np.float32)])

    return value


def positions_to_grid(
    positions: np.ndarray, values: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    put values onto the regular grid that the positions lie on -> grid, origin, spacing

    ``positions`` is of shape [n, 3] and ``values`` of shape [n] or [n, 3]. The grid is of shape
    [ny, nx, ...] for a planar field and [nz, ny, nx, ...] for a volumetric one, so its axes are
    ordered the way image data is. ``origin`` is the (x, y, z) of the grid's first sample and
    ``spacing`` the (x, y, z) distance between samples, zero along an axis with a single sample.
    """

    coords = [np.unique(positions[:, dim]) for dim in range(3)]
    n_samples = [len(c) for c in coords]

    if np.prod(n_samples) != positions.shape[0]:
        raise ValueError(
            f"stream positions must lie on a regular grid, the unique x, y and z values in the "
            f"positions passed form a grid of {n_samples} = {np.prod(n_samples)} points but "
            f"{positions.shape[0]} positions were passed"
        )

    if n_samples[0] < 2 or n_samples[1] < 2:
        raise ValueError(
            f"stream positions must have at least 2 samples along both x and y, the positions "
            f"passed form a grid of {n_samples}"
        )

    spacing = np.zeros(3, dtype=np.float32)
    for dim, c in enumerate(coords):
        if n_samples[dim] < 2:
            continue

        steps = np.diff(c)
        if not np.allclose(steps, steps[0]):
            raise ValueError(
                f"stream positions must lie on a regular grid, the spacing along {'xyz'[dim]} "
                f"varies between {steps.min()} and {steps.max()}"
            )

        spacing[dim] = steps[0]

    # index of every position along each axis, to scatter the values onto the grid with
    indices = [np.searchsorted(coords[dim], positions[:, dim]) for dim in range(3)]

    grid = np.zeros((*n_samples[::-1], *values.shape[1:]), dtype=np.float32)
    grid[indices[2], indices[1], indices[0]] = values

    if n_samples[2] == 1:
        # planar field, drop the z axis so the grid is 2d
        grid = grid[0]

    return grid, np.array([c[0] for c in coords], dtype=np.float32), spacing


def interpolate_grid(
    grid: np.ndarray, origin: np.ndarray, spacing: np.ndarray, points: np.ndarray
) -> np.ndarray:
    """
    multilinear interpolation of a regularly gridded array at arbitrary points

    ``grid``, ``origin`` and ``spacing`` are as returned by ``positions_to_grid`` and ``points``
    is of shape [n, 3]. Returns shape [n, ...], nan for a point that lies outside the grid.
    """

    points = np.atleast_2d(points)

    # a zero spacing along z means the grid is planar, so it has 2 axes rather than 3
    n_axes = 3 if spacing[2] > 0 else 2
    shape = np.array(grid.shape[:n_axes])

    # continuous index along each grid axis, whose (z, y, x) order reverses a position's xyz
    coords = np.empty((points.shape[0], n_axes))
    for axis in range(n_axes):
        dim = n_axes - 1 - axis
        coords[:, axis] = (points[:, dim] - origin[dim]) / spacing[dim]

    inside = np.all(
        (coords >= -GRID_TOLERANCE) & (coords <= shape - 1 + GRID_TOLERANCE), axis=1
    )

    # a point outside the grid, or one that is not finite at all, still has to index somewhere
    # for the weighted sum below, its value is replaced with nan once that is done
    coords[~inside] = 0

    # clipped so a point on the far edge of the grid interpolates within the last cell
    lower = np.clip(np.floor(coords), 0, shape - 2).astype(np.intp)
    frac = np.clip(coords - lower, 0, 1)

    out = np.zeros((points.shape[0], *grid.shape[n_axes:]), dtype=np.float32)

    for corner in product((0, 1), repeat=n_axes):
        weight = np.ones(points.shape[0])
        for axis, offset in enumerate(corner):
            weight *= frac[:, axis] if offset else 1 - frac[:, axis]

        index = tuple(lower[:, axis] + offset for axis, offset in enumerate(corner))
        out += weight.reshape(-1, *(1,) * (out.ndim - 1)) * grid[index]

    out[~inside] = np.nan

    return out


def make_grid_sampler(grid: np.ndarray, origin: np.ndarray, spacing: np.ndarray):
    """
    build a function that interpolates the grid at one point -> value, or None outside the grid

    Same multilinear interpolation as ``interpolate_grid``, written out for a single point
    because the streamline integrator evaluates the field four times per step, where numpy's
    per-call overhead on a one element array dominates by a measured 13x.
    """

    n_axes = 3 if spacing[2] > 0 else 2
    origin = [float(v) for v in origin]
    spacing = [float(v) for v in spacing]
    # the grid's (z, y, x) axis order reverses a position's xyz
    last = [n - 1 for n in grid.shape[:n_axes][::-1]]

    def cell(coord: float, axis: int) -> tuple[int, float]:
        """index of the cell holding the coord, and how far into it the coord lies"""
        index = min(max(int(coord), 0), last[axis] - 1)
        return index, min(max(coord - index, 0.0), 1.0)

    if n_axes == 2:

        def sample(point: np.ndarray) -> np.ndarray | None:
            fx = (float(point[0]) - origin[0]) / spacing[0]
            fy = (float(point[1]) - origin[1]) / spacing[1]

            if not (
                -GRID_TOLERANCE <= fx <= last[0] + GRID_TOLERANCE
                and -GRID_TOLERANCE <= fy <= last[1] + GRID_TOLERANCE
            ):
                return None

            ix, tx = cell(fx, 0)
            iy, ty = cell(fy, 1)
            low, high = grid[iy], grid[iy + 1]

            return (
                low[ix] * ((1 - tx) * (1 - ty))
                + low[ix + 1] * (tx * (1 - ty))
                + high[ix] * ((1 - tx) * ty)
                + high[ix + 1] * (tx * ty)
            )

    else:

        def sample(point: np.ndarray) -> np.ndarray | None:
            fx = (float(point[0]) - origin[0]) / spacing[0]
            fy = (float(point[1]) - origin[1]) / spacing[1]
            fz = (float(point[2]) - origin[2]) / spacing[2]

            if not (
                -GRID_TOLERANCE <= fx <= last[0] + GRID_TOLERANCE
                and -GRID_TOLERANCE <= fy <= last[1] + GRID_TOLERANCE
                and -GRID_TOLERANCE <= fz <= last[2] + GRID_TOLERANCE
            ):
                return None

            ix, tx = cell(fx, 0)
            iy, ty = cell(fy, 1)
            iz, tz = cell(fz, 2)

            out = 0.0
            for dz, wz in ((0, 1 - tz), (1, tz)):
                plane = grid[iz + dz]
                for dy, wy in ((0, 1 - ty), (1, ty)):
                    row = plane[iy + dy]
                    out = (
                        out
                        + row[ix] * ((1 - tx) * wy * wz)
                        + row[ix + 1] * (tx * wy * wz)
                    )

            return out

    return sample


def place_streamlines(
    field: np.ndarray,
    origin: np.ndarray,
    spacing: np.ndarray,
    separating_distance: float,
    test_distance: float,
    max_length: float | None,
) -> list[np.ndarray]:
    """
    place evenly spaced streamlines through a gridded vector field -> list of [m, 3] paths

    Jobard & Lefer (1997), "Creating Evenly-Spaced Streamlines of Arbitrary Density". A
    streamline is seeded only where it is at least ``separating_distance`` (d_sep) from every
    streamline already placed, and grown until it comes within ``test_distance`` (d_test) of
    one. New seeds are proposed one separating distance either side of the streamline just
    placed, which is what keeps the density uniform. ``max_length`` bounds the arc length of one
    streamline, or is None for unbounded.

    ``field``, ``origin`` and ``spacing`` are as returned by ``positions_to_grid``.
    """

    n_axes = 3 if spacing[2] > 0 else 2

    if n_axes == 2 and not np.allclose(field[..., 2], 0):
        raise ValueError(
            "stream positions lie in a plane but the directions have a z component, there is no "
            "grid to follow the streamlines out of the plane with"
        )

    # (nx, ny) or (nx, ny, nz), reversing the grid's (z, y, x) axis order back to xyz
    shape = np.array(field.shape[:n_axes][::-1])
    lower = origin[:n_axes]
    upper = lower + spacing[:n_axes] * (shape - 1)

    magnitudes = np.linalg.norm(field, axis=-1)
    if magnitudes.max() == 0:
        return []

    # a streamline cannot be followed where the field effectively vanishes
    stall = magnitudes.max() * 1e-6

    # fine enough to follow the curvature of a feature the size of the streamline spacing
    step = separating_distance / 4
    # the samples a streamline just laid down must not stop it, only a return to itself
    lookback = int(np.ceil(2 * separating_distance / step)) + 1
    half_length = np.inf if max_length is None else max_length / 2

    # every sample of every placed streamline, bucketed into cells of one separating distance so
    # the distance test only has to look at the cells neighbouring a point
    placed = np.empty((0, 3), dtype=np.float32)
    cells: dict[tuple, list[int]] = {}

    def is_clear(point: np.ndarray, distance: float) -> bool:
        """whether the point is at least ``distance`` from every sample of every placed streamline"""
        cell = ((point[:n_axes] - lower) // separating_distance).astype(np.intp)

        candidates = []
        for offset in product((-1, 0, 1), repeat=n_axes):
            bucket = cells.get(tuple(cell + offset))
            if bucket is not None:
                candidates += bucket

        if not candidates:
            return True

        return bool(
            (np.linalg.norm(placed[candidates] - point, axis=1) >= distance).all()
        )

    sample_field = make_grid_sampler(field, origin, spacing)

    def unit(point: np.ndarray) -> np.ndarray | None:
        """the field direction at the point, None outside the grid or where the field vanishes"""
        vector = sample_field(point)

        if vector is None:
            return None

        magnitude = hypot(*vector)

        if magnitude < stall:
            return None

        return vector / magnitude

    def advance(point: np.ndarray, signed_step: float) -> np.ndarray | None:
        """one RK4 step of ``signed_step`` arc length, None where the step cannot be taken"""
        k1 = unit(point)
        if k1 is None:
            return None

        k2 = unit(point + 0.5 * signed_step * k1)
        if k2 is None:
            return None

        k3 = unit(point + 0.5 * signed_step * k2)
        if k3 is None:
            return None

        k4 = unit(point + signed_step * k3)
        if k4 is None:
            return None

        new = point + (signed_step / 6) * (k1 + 2 * k2 + 2 * k3 + k4)

        if np.any(new[:n_axes] < lower) or np.any(new[:n_axes] > upper):
            return None

        return new

    def grow(seed: np.ndarray, signed_step: float, other: np.ndarray) -> np.ndarray:
        """
        integrate from the seed until the streamline has to stop -> [m, 3] path

        It stops where it leaves the grid, stalls, comes within ``test_distance`` of a streamline
        already placed, or comes back around to itself. ``other`` is the [m, 3] other half of
        this same streamline with its samples near the seed dropped, so the two halves do not
        stop each other.
        """
        points = np.empty((64, 3), dtype=np.float32)
        points[0] = seed
        count = 1
        length = 0.0

        while length < half_length:
            point = advance(points[count - 1], signed_step)
            if point is None:
                break

            if not is_clear(point, test_distance):
                break

            if count > lookback:
                trail = points[: count - lookback]
                if (np.linalg.norm(trail - point, axis=1) < test_distance).any():
                    break

            if (
                len(other)
                and (np.linalg.norm(other - point, axis=1) < test_distance).any()
            ):
                break

            length += float(np.linalg.norm(point - points[count - 1]))

            if count == len(points):
                points = np.concatenate([points, np.empty_like(points)])

            points[count] = point
            count += 1

        return points[:count]

    def propose_seeds(path: np.ndarray) -> list[np.ndarray]:
        """candidate seeds one separating distance either side of the path"""
        if len(path) < 2:
            return []

        # one candidate site every separating distance of arc length
        arc = np.concatenate(
            [[0.0], np.cumsum(np.linalg.norm(np.diff(path, axis=0), axis=1))]
        )
        sites = np.arange(0, arc[-1], separating_distance)
        if len(sites) == 0:
            return []

        centers = np.column_stack(
            [np.interp(sites, arc, path[:, dim]) for dim in range(3)]
        )
        tangents = np.column_stack(
            [
                np.interp(sites + step, arc, path[:, dim])
                - np.interp(sites - step, arc, path[:, dim])
                for dim in range(3)
            ]
        )
        norms = np.linalg.norm(tangents, axis=1, keepdims=True)
        tangents = tangents / np.where(norms > 0, norms, 1)

        if n_axes == 2:
            normals = [
                np.column_stack([-tangents[:, 1], tangents[:, 0], np.zeros(len(sites))])
            ]
        else:
            # the axis a tangent leans on least gives a vector it cannot be parallel to, and two
            # cross products turn that into an orthonormal basis of the normal plane
            leaning = np.zeros_like(tangents)
            leaning[np.arange(len(tangents)), np.argmin(np.abs(tangents), axis=1)] = 1.0
            first = np.cross(tangents, leaning)
            first = first / np.linalg.norm(first, axis=1, keepdims=True)
            normals = [first, np.cross(tangents, first)]

        candidates = np.concatenate(
            [
                centers + sign * separating_distance * normal
                for normal in normals
                for sign in (1, -1)
            ]
        )
        inside = np.all(
            (candidates[:, :n_axes] >= lower) & (candidates[:, :n_axes] <= upper),
            axis=1,
        )

        return list(candidates[inside])

    def cell_centers():
        """the center of every cell, in order, whether or not it holds a sample yet"""
        n_cells = np.ceil((upper - lower) / separating_distance).astype(int) + 1

        for index in product(*(range(n) for n in n_cells)):
            center = origin.copy()
            center[:n_axes] = lower + (np.array(index) + 0.5) * separating_distance

            if np.all(center[:n_axes] <= upper):
                yield center

    # start where the field is fastest, since that is the flow the plot is mostly about
    fastest = np.unravel_index(np.argmax(magnitudes), magnitudes.shape)
    first_seed = origin.copy()
    first_seed[:n_axes] = lower + spacing[:n_axes] * np.array(fastest[::-1])

    seeds = deque([first_seed])
    # consumed lazily across sweeps, so every cell is only ever tested once
    sweep = cell_centers()
    paths = list()

    while True:
        while seeds:
            seed = seeds.popleft()

            if not is_clear(seed, separating_distance):
                continue

            backward = grow(seed, -step, np.empty((0, 3), dtype=np.float32))
            forward = grow(seed, step, backward[lookback:])
            path = np.concatenate([backward[::-1], forward[1:]])

            base = len(placed)
            placed = np.concatenate([placed, path])

            keys = ((path[:, :n_axes] - lower) // separating_distance).astype(np.intp)
            for i, key in enumerate(map(tuple, keys)):
                cells.setdefault(key, []).append(base + i)

            paths.append(path)
            seeds.extend(propose_seeds(path))

        # candidates only ever come off a placed streamline, so the queue can empty with part of
        # the field never visited, leaving holes. sweep for a cell that is still clear and go again
        for center in sweep:
            if is_clear(center, separating_distance):
                seeds.append(center)
                break
        else:
            return paths


def arrows_along_streamline(
    path: np.ndarray,
    scales: np.ndarray,
    shape_options: dict,
    segments: int = STALK_SEGMENTS,
) -> tuple[np.ndarray, np.ndarray, np.ndarray] | None:
    """
    lay arrows out along one streamline -> stalks, tips, directions, or None if it is too short

    ``path`` is a [m, 3] streamline and ``scales`` the [m] field magnitude at each of its
    samples, normalized to (0, 1]. The arc-length pitch is the same for every arrow so the
    density stays uniform, while the stalk of a slow arrow is shorter, which is what makes the
    arrow length encode the magnitude. ``stalks`` is of shape [n_arrows, segments, 3] and is nan
    for an arrow whose stalk is too short to draw, ``tips`` and ``directions`` are of shape
    [n_arrows, 3] and give the center of each arrowhead cone and the flow direction there.
    """

    stalk_length = shape_options["stalk_length"]
    cone_height = shape_options["cone_height"]
    pitch = stalk_length + cone_height + shape_options["gap"]

    # arc length at each sample, from the chords rather than the step so it stays exact
    arc = np.concatenate(
        [[0.0], np.cumsum(np.linalg.norm(np.diff(path, axis=0), axis=1))]
    )

    n_arrows = int(arc[-1] // pitch)
    if n_arrows < 1:
        return None

    # centered along the streamline so the leftover is split between its two ends
    starts = (arc[-1] - n_arrows * pitch) / 2 + np.arange(n_arrows) * pitch
    stalk_scales = np.interp(starts, arc, scales)

    stalk_arc = (
        starts[:, None]
        + np.linspace(0, 1, segments)[None, :] * (stalk_length * stalk_scales)[:, None]
    )
    # the cone is centered half its own height past the end of the stalk
    tip_arc = starts + stalk_length * stalk_scales + cone_height / 2

    def sample(at: np.ndarray) -> np.ndarray:
        """the path position at each arc length in ``at``, of shape [*at.shape, 3]"""
        positions = np.stack(
            [np.interp(at.ravel(), arc, path[:, dim]) for dim in range(3)], axis=-1
        )
        return positions.reshape(*at.shape, 3).astype(np.float32)

    stalks = sample(stalk_arc)
    tips = sample(tip_arc)
    # the flow direction over the span that the cone itself covers
    directions = sample(tip_arc + cone_height / 2) - sample(tip_arc - cone_height / 2)

    # a stalk this short is invisible and would leave the line material with a zero-length
    # segment, so it is dropped and only the arrowhead is drawn
    stalks[stalk_scales < 1e-3] = np.nan

    return stalks, tips, directions


# it doesn't make sense to modify just a portion of a vector field, same as for VectorPositions,
# so we only allow setting the entire array, but allow getting portions of it
class StreamField(GraphicFeature):
    def __init__(self, value: np.ndarray, property_name: str):
        """Manages one of the two arrays describing the vector field, places the streamlines again"""

        self._value = parse_field_array(value, property_name)
        super().__init__(property_name=property_name)

    @property
    def value(self) -> np.ndarray:
        return self._value

    def __getitem__(self, item):
        return self.value[item]

    def __setitem__(self, key, value):
        raise NotImplementedError(
            f"cannot set individual slices of stream {self._property_name}, must set all of them"
        )

    @block_reentrance
    def set_value(self, graphic, value: np.ndarray):
        value = parse_field_array(value, self._property_name)

        if value.shape[0] != self._value.shape[0]:
            raise ValueError(
                f"number of stream {self._property_name} in the passed array != the number in "
                f"the graphic: {value.shape[0]} != {self._value.shape[0]}"
            )

        self._value = value
        graphic._fpl_rebuild()

        event = GraphicFeatureEvent(type=self._property_name, info={"value": value})
        self._call_event_handlers(event)


class StreamPositions(StreamField):
    event_info_spec = [
        {
            "dict key": "value",
            "type": "np.ndarray",
            "description": "new field positions",
        },
    ]

    def __init__(self, positions: np.ndarray, property_name: str = "positions"):
        """Manages the positions of the field samples that the streamlines are followed through"""

        super().__init__(positions, property_name)


class StreamDirections(StreamField):
    event_info_spec = [
        {
            "dict key": "value",
            "type": "np.ndarray",
            "description": "new field directions",
        },
    ]

    def __init__(self, directions: np.ndarray, property_name: str = "directions"):
        """Manages the field vectors that the streamlines are followed along"""

        super().__init__(directions, property_name)


class StreamLayout(GraphicFeature):
    def __init__(self, value, property_name: str):
        """Manages a property that places the streamlines or lays out the arrows again"""

        self._value = self._parse(value)
        super().__init__(property_name=property_name)

    def _parse(self, value):
        """validate and coerce the value, subclasses override"""
        return value

    @property
    def value(self):
        return self._value

    @block_reentrance
    def set_value(self, graphic, value):
        self._value = self._parse(value)
        graphic._fpl_rebuild()

        event = GraphicFeatureEvent(
            type=self._property_name, info={"value": self._value}
        )
        self._call_event_handlers(event)


class StreamSeparatingDistance(StreamLayout):
    """d_sep, the distance a new streamline keeps from the ones already placed"""

    event_info_spec = [
        {
            "dict key": "value",
            "type": "float",
            "description": "new separating distance",
        },
    ]

    def __init__(self, value: float, property_name: str = "separating_distance"):
        super().__init__(value, property_name)

    def _parse(self, value: float) -> float:
        value = float(value)

        if value <= 0:
            raise ValueError(f"`separating_distance` must be > 0, you passed: {value}")

        return value


class StreamSeparatingDistanceRatio(StreamLayout):
    """d_test / d_sep, how close a growing streamline may come to a placed one"""

    event_info_spec = [
        {
            "dict key": "value",
            "type": "float",
            "description": "new separating distance ratio",
        },
    ]

    def __init__(self, value: float, property_name: str = "separating_distance_ratio"):
        super().__init__(value, property_name)

    def _parse(self, value: float) -> float:
        value = float(value)

        if not 0 < value <= 1:
            raise ValueError(
                f"`separating_distance_ratio` must be in (0, 1], you passed: {value}"
            )

        return value


class StreamMaxLength(StreamLayout):
    """Maximum arc length of one streamline"""

    event_info_spec = [
        {
            "dict key": "value",
            "type": "float | None",
            "description": "new maximum streamline length",
        },
    ]

    def __init__(self, value: float | None, property_name: str = "max_length"):
        super().__init__(value, property_name)

    def _parse(self, value: float | None) -> float | None:
        if value is None:
            return None

        value = float(value)

        if value <= 0:
            raise ValueError(f"`max_length` must be > 0 or None, you passed: {value}")

        return value


class StreamSize(StreamLayout):
    """Size of one arrow in world space"""

    event_info_spec = [
        {
            "dict key": "value",
            "type": "float",
            "description": "new arrow size",
        },
    ]

    def __init__(self, value: float, property_name: str = "size"):
        super().__init__(value, property_name)

    def _parse(self, value: float) -> float:
        value = float(value)

        if value <= 0:
            raise ValueError(f"`size` must be > 0, you passed: {value}")

        return value


class StreamCmapTransform(GraphicFeature):
    event_info_spec = [
        {
            "dict key": "value",
            "type": "np.ndarray",
            "description": "new colormap transform",
        },
    ]

    def __init__(self, value: np.ndarray, property_name: str = "cmap_transform"):
        """Manages the per-position scalar field that the colors are looked up from"""

        self._value = self._parse(value)
        super().__init__(property_name=property_name)

    def _parse(self, value: np.ndarray) -> np.ndarray:
        value = np.asarray(value, dtype=np.float32).squeeze()

        if value.ndim != 1:
            raise ValueError(
                f"stream `cmap_transform` must be 1 dimensional with one value per field "
                f"position, you passed an array of shape: {value.shape}"
            )

        return value

    @property
    def value(self) -> np.ndarray:
        return self._value

    @block_reentrance
    def set_value(self, graphic, value: np.ndarray):
        value = self._parse(value)

        if value.size != len(graphic.positions.value):
            raise ValueError(
                f"stream `cmap_transform` must have one value per field position: "
                f"{value.size} != {len(graphic.positions.value)}"
            )

        self._value = value
        graphic._fpl_rebuild()

        event = GraphicFeatureEvent(type=self._property_name, info={"value": value})
        self._call_event_handlers(event)


class StreamColor(GraphicFeature):
    ndim = 1

    event_info_spec = [
        {
            "dict key": "value",
            "type": "str | pygfx.Color | np.ndarray | Sequence[float]",
            "description": "new color value",
        },
    ]

    def __init__(self, value: ColorLike, property_name: str = "color"):
        """Manages uniform color for the stalk line and arrowhead mesh materials"""

        self._value = pygfx.Color(value)
        super().__init__(property_name=property_name)

    @property
    def value(self) -> pygfx.Color:
        return self._value

    @block_reentrance
    def set_value(self, graphic, value: ColorLike):
        value = pygfx.Color(value)

        for material in graphic._materials:
            material.color = value

        self._value = value

        event = GraphicFeatureEvent(type=self._property_name, info={"value": value})
        self._call_event_handlers(event)


class StreamCmap(GraphicFeature):
    event_info_spec = [
        {
            "dict key": "value",
            "type": "cmap.Colormap",
            "description": "new colormap",
        },
    ]

    def __init__(self, value: ColormapLike, property_name: str = "cmap"):
        """
        colormap feature, sets the map of the stalk line and arrowhead mesh materials
        """

        self._value = cmap_lib.Colormap(value)
        super().__init__(property_name=property_name)

    @property
    def value(self) -> cmap_lib.Colormap:
        return self._value

    @block_reentrance
    def set_value(self, graphic, value: ColormapLike):
        self._value = cmap_lib.Colormap(value)

        for material in graphic._materials:
            material.map = self._value.to_pygfx()

        event = GraphicFeatureEvent(type=self._property_name, info={"value": value})
        self._call_event_handlers(event)

    def __repr__(self):
        return self.value.__repr__()

    def _repr_html_(self):
        return self.value._repr_html_()

    def _repr_png(self):
        return self.value._repr_png_()


class StreamCmapRange(GraphicFeature):
    """
    The (min, max) range of the ``cmap_transform`` that is mapped onto the colormap, i.e. the
    materials' ``maprange``.
    """

    ndim = 1

    event_info_spec = [
        {
            "dict key": "value",
            "type": "tuple[float, float]",
            "description": "new range",
        },
    ]

    def __init__(self, value: tuple[float, float], property_name: str = "cmap_range"):
        self._value = (float(value[0]), float(value[1]))
        super().__init__(property_name=property_name)

    @property
    def value(self) -> tuple[float, float]:
        return self._value

    @block_reentrance
    def set_value(self, graphic, value: tuple[float, float]):
        self._value = (float(value[0]), float(value[1]))

        for material in graphic._materials:
            material.maprange = self._value

        event = GraphicFeatureEvent(type=self._property_name, info={"value": value})
        self._call_event_handlers(event)


class StreamThickness(GraphicFeature):
    event_info_spec = [
        {"dict key": "value", "type": "float", "description": "new thickness value"},
    ]

    def __init__(self, value: float, property_name: str = "thickness"):
        """Manages the width of the arrow stalks"""

        self._value = float(value)
        super().__init__(property_name=property_name)

    @property
    def value(self) -> float:
        return self._value

    @block_reentrance
    def set_value(self, graphic, value: float):
        value = float(value)
        graphic._stalks.material.thickness = value
        self._value = value

        event = GraphicFeatureEvent(type=self._property_name, info={"value": value})
        self._call_event_handlers(event)


class StreamSizeSpace(GraphicFeature):
    event_info_spec = [
        {
            "dict key": "value",
            "type": "str",
            "description": "'screen' | 'world' | 'model'",
        },
    ]

    def __init__(self, value: str, property_name: str = "size_space"):
        """Manages the coordinate space that the stalk thickness is expressed in"""

        self._value = self._parse(value)
        super().__init__(property_name=property_name)

    def _parse(self, value: str) -> str:
        if value not in ["screen", "world", "model"]:
            raise ValueError(
                f"`size_space` must be one of: {['screen', 'world', 'model']}"
            )

        return value

    @property
    def value(self) -> str:
        return self._value

    @block_reentrance
    def set_value(self, graphic, value: str):
        value = self._parse(value)
        graphic._stalks.material.thickness_space = value
        self._value = value

        event = GraphicFeatureEvent(type=self._property_name, info={"value": value})
        self._call_event_handlers(event)


class StreamAlpha(Alpha):
    """The alpha value of a stream graphic, whose group has no material of its own."""

    @block_reentrance
    def set_value(self, graphic, value: float):
        for material in graphic._materials:
            material.opacity = value

        self._value = value

        event = GraphicFeatureEvent(type=self._property_name, info={"value": value})
        self._call_event_handlers(event)


class StreamAlphaMode(AlphaMode):
    """The alpha-mode value of a stream graphic, whose group has no material of its own."""

    @block_reentrance
    def set_value(self, graphic, value: str):
        for material in graphic._materials:
            material.alpha_mode = value

        # the line material only anti-aliases for the blended methods, as for a line graphic
        graphic._stalks.material.aa = value in ("blend", "weighted_blend")

        self._value = value

        event = GraphicFeatureEvent(type=self._property_name, info={"value": value})
        self._call_event_handlers(event)
