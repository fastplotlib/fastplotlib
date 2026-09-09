"""
Backend (non-screenshot) tests for graphic collections.

Covers ``LineCollection``, ``ScatterCollection``, ``ImageCollection`` and the
``LineStack`` / ``ScatterStack`` / ``ImageGrid`` layout subclasses:

* construction with every valid form of each feature, and the valid combinations
* that invalid forms and combinations raise
* the analogous setters
* get/set slicing across the ``[n_graphics, n_datapoints, xyz/RGBA]`` axes, in all valid combinations
* the numpy-like operators on accessors

Every value is verified on the individual child graphic's underlying ``GraphicFeature`` (the
per-vertex buffer or the uniform value), at three points: after construction, through the
collection getter, and through the getter again after a setter.
"""

import numpy as np
from numpy import testing as npt
import pytest

import pygfx
import cmap as cmap_lib

import fastplotlib as fpl
from fastplotlib.graphics import (
    LineCollection,
    ScatterCollection,
    ImageCollection,
    LineStack,
    ScatterStack,
    ImageGrid,
    LineGraphic,
    ScatterGraphic,
)
from fastplotlib.graphics.features import (
    VertexPositions,
    VertexColors,
    UniformColor,
    VertexCmap,
    Thickness,
    VertexPointSizes,
    UniformSize,
    VertexMarkers,
    UniformMarker,
    UniformEdgeColor,
    EdgeWidth,
    VertexRotations,
    UniformRotations,
    TextureArray,
)

from .utils import generate_color_inputs, MULTI_COLORS_TRUTH


N_GRAPHICS = 5
N_DATAPOINTS = 10

# five distinct single colors, one per graphic, and their RGBA truth
PER_GRAPHIC_COLORS = ["r", "g", "b", "cyan", "magenta"]
PER_GRAPHIC_COLORS_TRUTH = np.vstack([pygfx.Color(c) for c in PER_GRAPHIC_COLORS])


# ---------------------------------------------------------------------------
# data helpers
# ---------------------------------------------------------------------------
def lines_data(n_graphics=N_GRAPHICS, n_points=N_DATAPOINTS) -> list[np.ndarray]:
    """deterministic list of ``[n_points, 3]`` arrays, one per graphic"""
    return [
        np.column_stack(
            [
                np.arange(n_points),
                np.sin(np.arange(n_points) + i),
                np.cos(np.arange(n_points) + i),
            ]
        ).astype(np.float32)
        for i in range(n_graphics)
    ]


def jagged_lines_data(lengths=(6, 9, 7, 12, 8)) -> list[np.ndarray]:
    """per-graphic data with a different number of datapoints each (jagged)"""
    return [
        np.column_stack([np.arange(n), np.sin(np.arange(n)), np.cos(np.arange(n))]).astype(
            np.float32
        )
        for n in lengths
    ]


def data_mirror() -> np.ndarray:
    """a plain ``[n_graphics, n_datapoints, 3]`` array mirroring a rectangular collection"""
    return (
        np.arange(N_GRAPHICS * N_DATAPOINTS * 3, dtype=np.float32)
        .reshape(N_GRAPHICS, N_DATAPOINTS, 3)
    )


def colors_mirror() -> np.ndarray:
    """a plain ``[n_graphics, n_datapoints, 4]`` array of valid RGBA values in [0, 1]"""
    n = N_GRAPHICS * N_DATAPOINTS * 4
    return np.linspace(0, 1, n, dtype=np.float32).reshape(N_GRAPHICS, N_DATAPOINTS, 4)


def images_data(n=4, shape=(8, 8)) -> list[np.ndarray]:
    return [(np.arange(np.prod(shape)).reshape(shape) + i).astype(np.float32) for i in range(n)]


# ---------------------------------------------------------------------------
# slicing keys along each axis
# ---------------------------------------------------------------------------
GRAPHIC_AXIS_KEYS = {
    "int": 2,
    "all": slice(None),
    "range": slice(1, 4),
    "step": slice(None, None, 2),
    "neg": slice(-3, None),
    "fancy": [0, 2, 4],
    "bool": np.array([True, False, True, False, True]),
}

DATAPOINT_AXIS_KEYS = {
    "int": 3,
    "all": slice(None),
    "range": slice(2, 7),
    "step": slice(None, None, 3),
    "fancy": [1, 4, 8],
    "bool": np.arange(N_DATAPOINTS) > 5,
}

XYZ_KEYS = {"none": None, "int": 1, "slice": slice(0, 2)}
RGBA_KEYS = {"none": None, "int": 3, "slice": slice(0, 3)}


def as_per_graphic_list(result) -> list:
    """normalize an accessor get result to a list of per-graphic arrays"""
    if isinstance(result, np.ndarray) and result.dtype == object:
        return list(result)
    # single graphic (int graphic-key) returns one view directly
    return [result]


def selected_graphic_indices(graphic_key) -> np.ndarray:
    return np.atleast_1d(np.arange(N_GRAPHICS)[graphic_key])


def expected_views(mirror: np.ndarray, graphic_key, buffer_key: tuple) -> list:
    """the per-graphic views the accessor should return for ``[graphic_key, *buffer_key]``"""
    return [
        mirror[i][buffer_key] if buffer_key else mirror[i]
        for i in selected_graphic_indices(graphic_key)
    ]


# ===========================================================================
# construction: data
# ===========================================================================
@pytest.mark.parametrize("collection_type", [LineCollection, ScatterCollection])
@pytest.mark.parametrize("as_array", [False, True])
def test_construct_data_rectangular(collection_type, as_array):
    data = lines_data()
    collection = collection_type(np.asarray(data) if as_array else data)

    assert len(collection) == N_GRAPHICS
    for i, graphic in enumerate(collection.graphics):
        assert isinstance(graphic._data, VertexPositions)
        # after construction
        npt.assert_array_equal(graphic._data.value, data[i])
        # through the getter
        npt.assert_array_equal(collection.data[i], data[i])


@pytest.mark.parametrize("collection_type", [LineCollection, ScatterCollection])
@pytest.mark.parametrize("dims", ["y", "xy", "xyz"])
def test_construct_data_dimensionality(collection_type, dims):
    # 1D (y only), 2D (xy) and 3D (xyz) per-graphic data; the child pads to [n, 3]
    base = np.column_stack(
        [np.arange(N_DATAPOINTS), np.sin(np.arange(N_DATAPOINTS)), np.cos(np.arange(N_DATAPOINTS))]
    ).astype(np.float32)
    slices = {"y": base[:, 1], "xy": base[:, :2], "xyz": base}
    per_graphic = slices[dims]
    collection = collection_type([per_graphic.copy() for _ in range(N_GRAPHICS)])

    for graphic in collection.graphics:
        value = graphic._data.value
        assert value.shape == (N_DATAPOINTS, 3)
        if dims == "y":
            npt.assert_array_equal(value[:, 1], per_graphic)
            npt.assert_array_equal(value[:, 0], np.arange(N_DATAPOINTS))  # generated x
            npt.assert_array_equal(value[:, 2], 0)  # padded z
        elif dims == "xy":
            npt.assert_array_equal(value[:, :2], per_graphic)
            npt.assert_array_equal(value[:, 2], 0)  # padded z
        else:
            npt.assert_array_equal(value, per_graphic)


def test_construct_data_jagged():
    data = jagged_lines_data()
    collection = LineCollection(data)
    assert len(collection) == len(data)
    for i, graphic in enumerate(collection.graphics):
        assert isinstance(graphic._data, VertexPositions)
        npt.assert_array_equal(graphic._data.value, data[i])
        npt.assert_array_equal(collection.data[i], data[i])


# ===========================================================================
# construction: colors  (mode is inferred from the value, there is no color_mode kwarg)
# ===========================================================================
@pytest.mark.parametrize("collection_type", [LineCollection, ScatterCollection])
@pytest.mark.parametrize("colors", generate_color_inputs("b"))
def test_construct_colors_uniform(collection_type, colors):
    # a single color (str, RGBA array, list, or tuple) -> every graphic is uniform blue
    collection = collection_type(lines_data(), colors=colors)
    for i, graphic in enumerate(collection.graphics):
        assert isinstance(graphic._colors, UniformColor)
        npt.assert_almost_equal(np.asarray(graphic._colors.value), [0, 0, 1, 1])
        npt.assert_almost_equal(collection.colors[i], [0, 0, 1, 1])


@pytest.mark.parametrize("collection_type", [LineCollection, ScatterCollection])
@pytest.mark.parametrize("as_array", [False, True])
def test_construct_colors_per_graphic_uniform(collection_type, as_array):
    # one single color per graphic (list of strings, or an [n_graphics, 4] array)
    colors = PER_GRAPHIC_COLORS_TRUTH if as_array else PER_GRAPHIC_COLORS
    collection = collection_type(lines_data(), colors=colors)
    for i, graphic in enumerate(collection.graphics):
        assert isinstance(graphic._colors, UniformColor)
        npt.assert_almost_equal(np.asarray(graphic._colors.value), PER_GRAPHIC_COLORS_TRUTH[i])
        npt.assert_almost_equal(collection.colors[i], PER_GRAPHIC_COLORS_TRUTH[i])


@pytest.mark.parametrize("collection_type", [LineCollection, ScatterCollection])
@pytest.mark.parametrize("as_array", [False, True])
def test_construct_colors_vertex(collection_type, as_array):
    # a sequence of per-datapoint colors per graphic -> per-vertex colors
    per_graphic = [MULTI_COLORS_TRUTH.astype(np.float32).copy() for _ in range(N_GRAPHICS)]
    colors = np.asarray(per_graphic) if as_array else per_graphic
    collection = collection_type(lines_data(), colors=colors)
    for graphic in collection.graphics:
        assert isinstance(graphic._colors, VertexColors)
        npt.assert_almost_equal(graphic._colors.value, MULTI_COLORS_TRUTH)


# ===========================================================================
# construction: cmap + cmap_transform
# ===========================================================================
def cmap_across_truth(name, n_graphics, transform=None):
    if transform is None:
        values = np.linspace(0, 1, n_graphics)
    else:
        transform = np.asarray(transform, dtype=float)
        transform = np.interp(
            np.linspace(0, 1, n_graphics), np.linspace(0, 1, len(transform)), transform
        )
        spread = np.ptp(transform)
        values = (transform - transform.min()) / spread if spread else np.zeros(n_graphics)
    return np.asarray(cmap_lib.Colormap(name)(values))


# cmaps to exercise: a name, a named Colormap, and a custom Colormap
CMAPS = ["jet", cmap_lib.Colormap("jet"), cmap_lib.Colormap(["r", "purple", "orange", "green"])]


@pytest.mark.parametrize("collection_type", [LineCollection, ScatterCollection])
@pytest.mark.parametrize("cmap", CMAPS)
@pytest.mark.parametrize("transform", [None, [3, 5, 2, 1, 0]])
def test_construct_cmap_across_graphics(collection_type, cmap, transform):
    # a colormap with no transform, or a 1D transform, colors each graphic one color across the map
    collection = collection_type(lines_data(), cmap=cmap, cmap_transform=transform)
    truth = cmap_across_truth(cmap, N_GRAPHICS, transform)
    for i, graphic in enumerate(collection.graphics):
        assert isinstance(graphic._colors, UniformColor)
        assert graphic._cmap is None
        npt.assert_almost_equal(np.asarray(graphic._colors.value), truth[i], decimal=5)


@pytest.mark.parametrize("collection_type", [LineCollection, ScatterCollection])
@pytest.mark.parametrize("cmaps", [[c] * N_GRAPHICS for c in CMAPS] + [(CMAPS * N_GRAPHICS)[:N_GRAPHICS]])
def test_construct_cmap_per_graphic(collection_type, cmaps):
    # an iterable of cmaps with a 2D [n_graphics, n_datapoints] transform colors each graphic's datapoints
    transform = np.random.rand(N_GRAPHICS, N_DATAPOINTS)
    collection = collection_type(lines_data(), cmap=cmaps, cmap_transform=transform)
    lut = np.linspace(0, 1, 8)
    for graphic, expected in zip(collection.graphics, cmaps):
        assert isinstance(graphic._cmap, VertexCmap)
        assert graphic._colors is None
        npt.assert_almost_equal(graphic._cmap.value(lut), cmap_lib.Colormap(expected)(lut))


# ===========================================================================
# construction: per-graphic scalar / vector features (single value vs one per graphic)
# ===========================================================================
def test_construct_thickness():
    single = LineCollection(lines_data(), thickness=4.0)
    assert all(g._thickness.value == 4.0 for g in single.graphics)
    npt.assert_array_equal(single.thickness[:], [4.0] * N_GRAPHICS)

    per_graphic = LineCollection(lines_data(), thickness=[1, 2, 3, 4, 5])
    assert [g._thickness.value for g in per_graphic.graphics] == [1, 2, 3, 4, 5]


def test_construct_offsets_rotations_scales():
    offsets = np.arange(N_GRAPHICS * 3).reshape(N_GRAPHICS, 3).astype(float)
    collection = LineCollection(lines_data(), offsets=offsets)
    for i, graphic in enumerate(collection.graphics):
        npt.assert_array_equal(graphic._offset.value, offsets[i])
        npt.assert_array_equal(graphic.world_object.world.position, offsets[i])

    # a single offset goes to every graphic
    collection = LineCollection(lines_data(), offsets=(1, 2, 3))
    for graphic in collection.graphics:
        npt.assert_array_equal(graphic._offset.value, [1, 2, 3])


def test_construct_names_visibles():
    names = [f"line-{i}" for i in range(N_GRAPHICS)]
    collection = LineCollection(lines_data(), names=names, visibles=[True, False, True, False, True])
    assert [g.name for g in collection.graphics] == names
    assert [g._visible.value for g in collection.graphics] == [True, False, True, False, True]


@pytest.mark.parametrize("pattern", ["--", ":", (2, 3)])
def test_construct_dash_pattern(pattern):
    collection = LineCollection(lines_data(), dash_pattern=pattern)
    for graphic in collection.graphics:
        assert graphic._dash_pattern.value == pattern


@pytest.mark.parametrize("collection_type", [LineCollection, ScatterCollection])
def test_construct_size_space(collection_type):
    collection = collection_type(lines_data(), size_space="world")
    assert all(g.size_space == "world" for g in collection.graphics)


# ===========================================================================
# construction: invalid forms / combinations raise
# ===========================================================================
def test_construct_wrong_per_graphic_length_raises():
    # one value per graphic, but the wrong number of them
    with pytest.raises(IndexError):
        LineCollection(lines_data(), thickness=[1, 2, 3])
    with pytest.raises(IndexError):
        LineCollection(lines_data(), colors=["r", "g", "b"])


def test_construct_cmap_transform_wrong_n_graphics_raises():
    # a per-graphic (2D) transform must have one row per graphic
    with pytest.raises(ValueError):
        LineCollection(lines_data(), cmap="jet", cmap_transform=np.random.rand(3, N_DATAPOINTS))


def test_construct_cmap_transform_without_cmap_raises():
    with pytest.raises(ValueError):
        LineCollection(lines_data(), cmap_transform=[0, 1, 2, 3, 4])
    with pytest.raises(ValueError):
        ScatterCollection(lines_data(), cmap_transform=[0, 1, 2, 3, 4])


def test_construct_cmap_overrides_colors():
    # cmap and colors together is not an error; cmap wins, matching a single graphic
    collection = LineCollection(lines_data(), cmap="jet", colors="r")
    truth = cmap_across_truth("jet", N_GRAPHICS)
    for i, graphic in enumerate(collection.graphics):
        npt.assert_almost_equal(np.asarray(graphic._colors.value), truth[i], decimal=5)


# ===========================================================================
# setting: cmap / cmap_transform / cmap_range (symmetric with the constructor)
# ===========================================================================
@pytest.mark.parametrize("collection_type", [LineCollection, ScatterCollection])
@pytest.mark.parametrize("cmap", CMAPS)
@pytest.mark.parametrize("transform", [None, [3, 5, 2, 1, 0]])
def test_set_cmap_across_graphics(collection_type, cmap, transform):
    # setting a single cmap, and a 1D transform, colors each graphic one color, matching construction
    collection = collection_type(lines_data())
    collection.cmap = cmap
    if transform is not None:
        collection.cmap_transform = transform
    truth = cmap_across_truth(cmap, N_GRAPHICS, transform)
    for i, graphic in enumerate(collection.graphics):
        assert isinstance(graphic._colors, UniformColor)
        assert graphic._cmap is None
        npt.assert_almost_equal(np.asarray(graphic._colors.value), truth[i], decimal=5)


@pytest.mark.parametrize("collection_type", [LineCollection, ScatterCollection])
@pytest.mark.parametrize("cmaps", [[c] * N_GRAPHICS for c in CMAPS] + [(CMAPS * N_GRAPHICS)[:N_GRAPHICS]])
def test_set_cmap_per_graphic(collection_type, cmaps):
    # setting an iterable of cmaps with a 2D transform colors each graphic's datapoints
    transform = np.random.rand(N_GRAPHICS, N_DATAPOINTS)
    collection = collection_type(lines_data())
    collection.cmap = cmaps
    collection.cmap_transform = transform
    lut = np.linspace(0, 1, 8)
    for graphic, expected in zip(collection.graphics, cmaps):
        assert isinstance(graphic._cmap, VertexCmap)
        assert graphic._colors is None
        npt.assert_almost_equal(graphic._cmap.value(lut), cmap_lib.Colormap(expected)(lut))


@pytest.mark.parametrize("collection_type", [LineCollection, ScatterCollection])
def test_set_cmap_range(collection_type):
    # setting cmap_range on a per-graphic collection updates each graphic's range
    transform = np.random.rand(N_GRAPHICS, N_DATAPOINTS)
    collection = collection_type(lines_data(), cmap=["jet"] * N_GRAPHICS, cmap_transform=transform)
    collection.cmap_range = (0.0, 5.0)
    for graphic in collection.graphics:
        assert graphic.cmap_range == (0.0, 5.0)


@pytest.mark.parametrize("collection_type", [LineCollection, ScatterCollection])
def test_set_cmap_mismatch_raises(collection_type):
    # a single cmap needs a 1D transform; an iterable of cmaps needs a 2D transform
    collection = collection_type(lines_data())
    collection.cmap = "jet"
    with pytest.raises(ValueError):
        collection.cmap_transform = np.random.rand(N_GRAPHICS, N_DATAPOINTS)

    collection = collection_type(lines_data())
    collection.cmap = ["jet"] * N_GRAPHICS
    with pytest.raises(ValueError):
        collection.cmap_transform = [0, 1, 2, 3, 4]


@pytest.mark.parametrize("collection_type", [LineCollection, ScatterCollection])
def test_set_cmap_transform_without_cmap_raises(collection_type):
    collection = collection_type(lines_data())
    with pytest.raises(ValueError):
        collection.cmap_transform = [0, 1, 2, 3, 4]


# ===========================================================================
# get slicing matrix: data  [n_graphics, n_datapoints, xyz]
# ===========================================================================
@pytest.mark.parametrize("gname", GRAPHIC_AXIS_KEYS)
@pytest.mark.parametrize("dname", DATAPOINT_AXIS_KEYS)
@pytest.mark.parametrize("cname", XYZ_KEYS)
def test_data_get_slicing(gname, dname, cname):
    gkey, dkey, ckey = GRAPHIC_AXIS_KEYS[gname], DATAPOINT_AXIS_KEYS[dname], XYZ_KEYS[cname]
    mirror = data_mirror()
    collection = LineCollection([mirror[i].copy() for i in range(N_GRAPHICS)])

    buffer_key = (dkey,) if ckey is None else (dkey, ckey)
    key = (gkey, *buffer_key)

    got = as_per_graphic_list(collection.data[key])
    expected = expected_views(mirror, gkey, buffer_key)
    assert len(got) == len(expected)
    for g, e in zip(got, expected):
        npt.assert_array_equal(g, e)


# ===========================================================================
# set slicing matrix: data  [n_graphics, n_datapoints, xyz]
# ===========================================================================
@pytest.mark.parametrize("gname", GRAPHIC_AXIS_KEYS)
@pytest.mark.parametrize("dname", DATAPOINT_AXIS_KEYS)
@pytest.mark.parametrize("cname", XYZ_KEYS)
def test_data_set_slicing(gname, dname, cname):
    gkey, dkey, ckey = GRAPHIC_AXIS_KEYS[gname], DATAPOINT_AXIS_KEYS[dname], XYZ_KEYS[cname]
    mirror = data_mirror()
    collection = LineCollection([mirror[i].copy() for i in range(N_GRAPHICS)])

    buffer_key = (dkey,) if ckey is None else (dkey, ckey)
    key = (gkey, *buffer_key)

    value = -7.0
    collection.data[key] = value
    for i in selected_graphic_indices(gkey):
        mirror[i][buffer_key] = value

    # every child buffer matches the mirror
    for i in range(N_GRAPHICS):
        npt.assert_array_equal(collection.graphics[i]._data.value, mirror[i])
    # and the getter reflects the new values
    got = as_per_graphic_list(collection.data[key])
    for g, e in zip(got, expected_views(mirror, gkey, buffer_key)):
        npt.assert_array_equal(g, e)


# ===========================================================================
# whole-graphic data set (buffer_key is empty): replaces the buffer, may resize
# ===========================================================================
@pytest.mark.parametrize("gname", ["all", "int", "range", "fancy", "bool"])
def test_data_whole_graphic_get(gname):
    gkey = GRAPHIC_AXIS_KEYS[gname]
    mirror = data_mirror()
    collection = LineCollection([mirror[i].copy() for i in range(N_GRAPHICS)])
    got = as_per_graphic_list(collection.data[gkey])
    for g, e in zip(got, expected_views(mirror, gkey, ())):
        npt.assert_array_equal(g, e)


def test_data_whole_graphic_set_same_shape():
    collection = LineCollection(lines_data())
    new = np.zeros((N_DATAPOINTS, 3), dtype=np.float32)
    collection.data[:] = new
    for graphic in collection.graphics:
        npt.assert_array_equal(graphic._data.value, new)


def test_data_whole_graphic_set_resizes_buffer():
    collection = LineCollection(lines_data())  # N_DATAPOINTS per graphic
    smaller = np.column_stack([np.arange(4), np.arange(4), np.arange(4)]).astype(np.float32)
    collection.data[:] = smaller
    for graphic in collection.graphics:
        assert graphic._data.value.shape == (4, 3)
        npt.assert_array_equal(graphic._data.value, smaller)


def test_data_property_setter_resizes():
    # the `collection.data = ...` property mirrors `collection.data[:] = ...`
    collection = LineCollection(lines_data())
    new = np.stack([np.column_stack([np.arange(3)] * 3)] * N_GRAPHICS).astype(np.float32)
    collection.data = new
    for i, graphic in enumerate(collection.graphics):
        assert graphic._data.value.shape == (3, 3)
        npt.assert_array_equal(graphic._data.value, new[i])


# ===========================================================================
# get/set slicing matrix: colors  [n_graphics, n_datapoints, RGBA]
# ===========================================================================
@pytest.mark.parametrize("gname", GRAPHIC_AXIS_KEYS)
@pytest.mark.parametrize("dname", DATAPOINT_AXIS_KEYS)
@pytest.mark.parametrize("cname", RGBA_KEYS)
def test_colors_get_slicing(gname, dname, cname):
    gkey, dkey, ckey = GRAPHIC_AXIS_KEYS[gname], DATAPOINT_AXIS_KEYS[dname], RGBA_KEYS[cname]
    mirror = colors_mirror()
    collection = LineCollection(
        lines_data(), colors=[mirror[i].copy() for i in range(N_GRAPHICS)]
    )
    buffer_key = (dkey,) if ckey is None else (dkey, ckey)
    key = (gkey, *buffer_key)

    got = as_per_graphic_list(collection.colors[key])
    for g, e in zip(got, expected_views(mirror, gkey, buffer_key)):
        npt.assert_array_equal(g, e)


@pytest.mark.parametrize("gname", GRAPHIC_AXIS_KEYS)
@pytest.mark.parametrize("dname", DATAPOINT_AXIS_KEYS)
@pytest.mark.parametrize("cname", RGBA_KEYS)
def test_colors_set_slicing(gname, dname, cname):
    # once a datapoint/channel key is present, colors are set with raw numeric values
    gkey, dkey, ckey = GRAPHIC_AXIS_KEYS[gname], DATAPOINT_AXIS_KEYS[dname], RGBA_KEYS[cname]
    mirror = colors_mirror()
    collection = LineCollection(
        lines_data(), colors=[mirror[i].copy() for i in range(N_GRAPHICS)]
    )
    buffer_key = (dkey,) if ckey is None else (dkey, ckey)
    key = (gkey, *buffer_key)

    value = 0.25
    collection.colors[key] = value
    for i in selected_graphic_indices(gkey):
        mirror[i][buffer_key] = value

    for i in range(N_GRAPHICS):
        npt.assert_array_equal(collection.graphics[i]._colors.value, mirror[i])
    got = as_per_graphic_list(collection.colors[key])
    for g, e in zip(got, expected_views(mirror, gkey, buffer_key)):
        npt.assert_array_equal(g, e)


@pytest.mark.parametrize("colors", generate_color_inputs("r"))
def test_colors_whole_graphic_set_spec(colors):
    # a whole-graphic set (no datapoint/channel key) accepts a color spec, parsed to RGBA
    collection = LineCollection(
        lines_data(), colors=[np.ones((N_DATAPOINTS, 4), np.float32) for _ in range(N_GRAPHICS)]
    )
    collection.colors[:] = colors
    for graphic in collection.graphics:
        npt.assert_almost_equal(
            graphic._colors.value, np.tile([1, 0, 0, 1], (N_DATAPOINTS, 1))
        )


def test_colors_datapoint_slice_rejects_color_spec():
    # indexing into the datapoints means raw numbers; a color-name string is a type error
    collection = LineCollection(
        lines_data(), colors=[np.ones((N_DATAPOINTS, 4), np.float32) for _ in range(N_GRAPHICS)]
    )
    with pytest.raises(TypeError):
        collection.colors[:, 2:5] = "r"


# ===========================================================================
# setters on per-graphic scalar / vector features, and the property setters
# ===========================================================================
def test_set_thickness():
    collection = LineCollection(lines_data())
    collection.thickness[:] = 6.0
    assert all(g._thickness.value == 6.0 for g in collection.graphics)

    collection.thickness[:] = [1, 2, 3, 4, 5]
    assert [g._thickness.value for g in collection.graphics] == [1, 2, 3, 4, 5]

    # property setter is equivalent to `[:] =`
    collection.thickness = 9.0
    assert all(g._thickness.value == 9.0 for g in collection.graphics)

    # a single graphic
    collection.thickness[2] = 3.0
    assert collection.graphics[2]._thickness.value == 3.0


def test_set_offsets():
    collection = LineCollection(lines_data())
    collection.offsets[:] = (1, 2, 3)
    for graphic in collection.graphics:
        npt.assert_array_equal(graphic._offset.value, [1, 2, 3])

    per_graphic = np.arange(N_GRAPHICS * 3).reshape(N_GRAPHICS, 3).astype(float)
    collection.offsets[:] = per_graphic
    for i, graphic in enumerate(collection.graphics):
        npt.assert_array_equal(graphic._offset.value, per_graphic[i])
        npt.assert_array_equal(graphic.world_object.world.position, per_graphic[i])


def test_set_visibles():
    collection = LineCollection(lines_data())
    collection.visibles[:] = False
    assert all(g._visible.value is False for g in collection.graphics)
    assert all(g.world_object.visible is False for g in collection.graphics)


def test_cmap_property_setter_colors_across():
    # assigning to `collection.cmap` colors each graphic one color across the map
    collection = LineCollection(lines_data())
    collection.cmap = "viridis"
    truth = cmap_across_truth("viridis", N_GRAPHICS)
    for i, graphic in enumerate(collection.graphics):
        npt.assert_almost_equal(np.asarray(graphic._colors.value), truth[i], decimal=5)


# ===========================================================================
# scatter-specific features
# ===========================================================================
def test_scatter_sizes_uniform():
    collection = ScatterCollection(lines_data(), sizes=5)
    assert all(isinstance(g._sizes, UniformSize) for g in collection.graphics)
    assert all(g._sizes.value == 5 for g in collection.graphics)

    collection.sizes[:] = 8
    assert all(g._sizes.value == 8 for g in collection.graphics)
    collection.sizes[:] = [1, 2, 3, 4, 5]
    assert [g._sizes.value for g in collection.graphics] == [1, 2, 3, 4, 5]


def test_scatter_sizes_vertex():
    per_graphic = [np.linspace(1, 5, N_DATAPOINTS).astype(np.float32) for _ in range(N_GRAPHICS)]
    collection = ScatterCollection(lines_data(), sizes=per_graphic)
    for i, graphic in enumerate(collection.graphics):
        assert isinstance(graphic._sizes, VertexPointSizes)
        npt.assert_almost_equal(graphic._sizes.value, per_graphic[i])

    # within-graphic slicing
    collection.sizes[:, 2:5] = 7.0
    for graphic in collection.graphics:
        npt.assert_almost_equal(graphic._sizes.value[2:5], 7.0)


def test_scatter_markers_uniform_and_vertex():
    uniform = ScatterCollection(lines_data(), markers="s")
    assert all(isinstance(g._markers, UniformMarker) for g in uniform.graphics)
    assert all(g._markers.value == "square" for g in uniform.graphics)
    uniform.markers[:] = "o"
    assert all(g._markers.value == "circle" for g in uniform.graphics)

    vertex = ScatterCollection(lines_data(), markers=[["o"] * N_DATAPOINTS for _ in range(N_GRAPHICS)])
    assert all(isinstance(g._markers, VertexMarkers) for g in vertex.graphics)


def test_scatter_edge_colors_and_width():
    collection = ScatterCollection(lines_data(), edge_colors="red", edge_width=2.0)
    assert all(isinstance(g._edge_colors, UniformEdgeColor) for g in collection.graphics)
    assert all(isinstance(g._edge_width, EdgeWidth) for g in collection.graphics)
    assert all(g._edge_width.value == 2.0 for g in collection.graphics)

    collection.edge_width[:] = 3.0
    assert all(g._edge_width.value == 3.0 for g in collection.graphics)
    collection.edge_colors[:] = "blue"
    for graphic in collection.graphics:
        # UniformEdgeColor stores the raw user input, so normalize through pygfx.Color to verify
        npt.assert_almost_equal(np.asarray(pygfx.Color(graphic._edge_colors.value)), [0, 0, 1, 1])


@pytest.mark.parametrize(
    "value,expected_type",
    [
        (None, type(None)),
        (0.5, UniformRotations),
        ([np.linspace(0, 1, N_DATAPOINTS).astype(np.float32)] * N_GRAPHICS, VertexRotations),
    ],
)
def test_scatter_point_rotations(value, expected_type):
    kwargs = {} if value is None else {"point_rotations": value}
    collection = ScatterCollection(lines_data(), **kwargs)
    for graphic in collection.graphics:
        assert isinstance(graphic._point_rotations, expected_type)


# ===========================================================================
# image collection
# ===========================================================================
def test_image_construct_and_scalar_features():
    images = images_data()
    collection = ImageCollection(images, vmin=0, vmax=100, cmap="gray", gamma=1.5)
    for i, graphic in enumerate(collection.graphics):
        assert isinstance(graphic._data, TextureArray)
        npt.assert_array_equal(graphic._data.value, images[i])
        assert graphic._vmin.value == 0
        assert graphic._vmax.value == 100
        assert graphic._cmap.value == "gray"
        assert graphic._gamma.value == 1.5


def test_image_scalar_feature_setters():
    collection = ImageCollection(images_data(), vmin=0, vmax=100)
    collection.vmin[:] = 10
    assert all(g._vmin.value == 10 for g in collection.graphics)
    # one value per image
    collection.vmax[:] = [1, 2, 3, 4]
    assert [g._vmax.value for g in collection.graphics] == [1, 2, 3, 4]
    collection.cmap[:] = "viridis"
    assert all(g._cmap.value == "viridis" for g in collection.graphics)


def test_image_data_get_set_slicing():
    images = images_data()
    collection = ImageCollection(images, vmin=0, vmax=100)
    # get
    for i, graphic in enumerate(collection.graphics):
        npt.assert_array_equal(collection.data[i], images[i])
    # set a within-image region
    collection.data[:, 0:2, 0:2] = -5.0
    for graphic in collection.graphics:
        npt.assert_array_equal(graphic._data.value[0:2, 0:2], -5.0)


# ===========================================================================
# operators
# ===========================================================================
def test_operators_scalar_feature():
    collection = LineCollection(lines_data())
    collection.thickness[:] = [1, 2, 3, 4, 5]

    mask = collection.thickness < 3
    assert isinstance(mask, np.ndarray) and mask.dtype == bool
    npt.assert_array_equal(mask, [True, True, False, False, False])

    npt.assert_array_equal(collection.thickness + 1, [2, 3, 4, 5, 6])  # arithmetic
    npt.assert_array_equal(10 - collection.thickness, [9, 8, 7, 6, 5])  # reflected
    npt.assert_array_equal(abs(-collection.thickness), [1, 2, 3, 4, 5])  # unary


def test_operators_multicomponent_feature():
    collection = LineCollection(lines_data(), colors=["r", "r", "g", "b", "r"])
    result = collection.colors == (1, 0, 0, 1)
    # object array of per-graphic [4] bool arrays, no stacking
    assert isinstance(result, np.ndarray) and result.dtype == object
    red_mask = np.array([np.all(x) for x in result])
    npt.assert_array_equal(red_mask, [True, True, False, False, True])
    assert len(collection.data[red_mask]) == 3


def test_operators_jagged():
    collection = LineCollection(jagged_lines_data(lengths=(5, 8, 6)))
    result = collection.data < 0.5
    assert isinstance(result, np.ndarray) and result.dtype == object
    assert [x.shape for x in result] == [(5, 3), (8, 3), (6, 3)]


# ===========================================================================
# container behavior
# ===========================================================================
def test_len_iter_getitem_contains():
    collection = LineCollection(lines_data())
    assert len(collection) == N_GRAPHICS

    assert collection.graphics[0] in collection
    assert list(iter(collection))[0] is collection.graphics[0]


def test_add_remove_graphic():
    collection = LineCollection(lines_data(n_graphics=3))
    graphic = LineGraphic(lines_data(n_graphics=1)[0])
    collection.add_graphic(graphic)
    assert len(collection) == 4
    assert collection.graphics[-1] is graphic

    collection.remove_graphic(graphic)
    assert len(collection) == 3
    assert graphic not in collection


def test_add_graphic_wrong_type_raises():
    collection = LineCollection(lines_data())
    with pytest.raises(TypeError):
        collection.add_graphic(ScatterGraphic(lines_data(n_graphics=1)[0]))


def test_add_graphic_wrong_mode_raises():
    # a vertex-colors collection cannot take a uniform-color graphic
    collection = LineCollection(
        lines_data(), colors=[np.ones((N_DATAPOINTS, 4), np.float32) for _ in range(N_GRAPHICS)]
    )
    with pytest.raises(TypeError):
        collection.add_graphic(LineGraphic(lines_data(n_graphics=1)[0], colors="r"))


# ===========================================================================
# layout: stacks and image grid
# ===========================================================================
@pytest.mark.parametrize("collection_type", [LineStack, ScatterStack])
@pytest.mark.parametrize("separation_axis", ["x", "y", "xy"])
def test_stack_offsets(collection_type, separation_axis):
    data = lines_data()
    separation = np.array([3.0, 5.0, 7.0])
    stack = collection_type(data, separation=tuple(separation), separation_axis=separation_axis)

    axes = [{"x": 0, "y": 1, "z": 2}[a] for a in separation_axis]
    extents = np.concatenate([d[:, axes] for d in data]).max(axis=0)
    expected = np.zeros((N_GRAPHICS, 3))
    expected[:, axes] = np.arange(N_GRAPHICS)[:, None] * (extents + separation[axes])

    offsets = np.array([g.offset for g in stack.graphics])
    npt.assert_allclose(offsets, expected, atol=1e-5)


def test_stack_separation_setter_restacks():
    stack = LineStack(lines_data(), separation=(0, 1, 0), separation_axis="y")
    before = np.array([g.offset[1] for g in stack.graphics])
    stack.separation = (0, 10, 0)
    after = np.array([g.offset[1] for g in stack.graphics])
    assert not np.allclose(before, after)


def test_stack_invalid_separation_axis_raises():
    with pytest.raises(ValueError):
        LineStack(lines_data(), separation_axis="w")


def test_image_grid_offsets():
    # non-square images so the row/column steps are distinguishable
    images = [np.zeros((6, 10), dtype=np.float32) for _ in range(4)]
    grid = ImageGrid(images, shape=(2, 2), separation=(1, 2))  # (row_sep, col_sep)
    offsets = np.array([g.offset for g in grid.graphics])
    # cell = largest image (6 rows, 10 cols); x step = 10 + 2, y step = -(6 + 1)
    expected = np.array(
        [[0, 0, 0], [12, 0, 0], [0, -7, 0], [12, -7, 0]], dtype=float
    )
    npt.assert_allclose(offsets, expected)


def test_image_grid_explicit_offsets():
    images = images_data(n=3)
    offsets = np.array([[0, 0, 0], [5, 0, 0], [10, 0, 0]], dtype=float)
    grid = ImageGrid(images, offsets=offsets)
    npt.assert_allclose([g.offset for g in grid.graphics], offsets)


def test_image_grid_shape_too_small_raises():
    with pytest.raises(ValueError):
        ImageGrid(images_data(n=4), shape=(1, 2))


# ===========================================================================
# jagged collections end-to-end
# ===========================================================================
def test_jagged_get_set():
    data = jagged_lines_data()
    collection = LineCollection(data)

    views = collection.data[:]
    assert [v.shape for v in views] == [d.shape for d in data]

    # a within-graphic set valid for every graphic (all have >= 6 points)
    collection.data[:, 0:5, 2] = 9.0
    for graphic in collection.graphics:
        npt.assert_array_equal(graphic._data.value[0:5, 2], 9.0)
