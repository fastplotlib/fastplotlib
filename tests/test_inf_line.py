import numpy as np
from numpy import testing as npt
import pytest

import pygfx

import fastplotlib as fpl
from fastplotlib.graphics.features import (
    InfLineAxisData,
    InfLineColors,
    UniformColor,
    GraphicFeatureEvent,
    VertexCmap
)


AXES = {"x": 0, "y": 1, "z": 2}


def make_inf_line(**kwargs):
    fig = fpl.Figure()
    return fig[0, 0].add_inf_line(**kwargs)


@pytest.mark.parametrize("axis", ["x", "y", "z"])
def test_axis_construction(axis):
    positions = np.array([0.0, 1.0, 2.0, 3.0])
    graphic = make_inf_line(data=positions, axis=axis)

    assert isinstance(graphic, fpl.InfLineGraphic)
    assert isinstance(graphic._data, InfLineAxisData)
    assert graphic.axis == axis
    assert isinstance(
        graphic.world_object.material, pygfx.LineInfiniteSegmentMaterial
    )

    # two vertices per line
    buffer = graphic.world_object.geometry.positions.data
    assert buffer.shape == (8, 3)
    assert len(graphic.data) == 4

    # value is one position per line, both endpoints share it
    npt.assert_array_equal(graphic.data.value, positions)
    npt.assert_array_equal(buffer[:, AXES[axis]], np.repeat(positions, 2))

    # the two endpoints of a line differ along another axis so the segment has a direction
    run_index = 1 if AXES[axis] == 0 else 0
    npt.assert_array_equal(buffer[1::2, run_index], np.ones(4))


def test_axis_none_construction():
    # user example: 4 vertical lines defined directly by endpoint pairs
    positions = np.array(
        [
            [0, 0, 0],
            [0, 1, 0],
            [1, 0, 0],
            [1, 1, 0],
            [2, 0, 0],
            [2, 1, 0],
            [3, 0, 0],
            [3, 1, 0],
        ],
        dtype=np.float32,
    )
    graphic = make_inf_line(data=positions, axis=None)

    assert graphic.axis is None
    assert len(graphic.data) == 4
    # value is [n_lines, 2, 3] endpoints
    assert graphic.data.value.shape == (4, 2, 3)
    npt.assert_array_equal(graphic.data.value[0], [[0, 0, 0], [0, 1, 0]])
    npt.assert_array_equal(
        graphic.world_object.geometry.positions.data, positions
    )


def test_axis_none_requires_even_points():
    with pytest.raises(ValueError):
        make_inf_line(data=np.random.rand(5, 3), axis=None)


def test_invalid_axis():
    with pytest.raises(ValueError):
        make_inf_line(data=np.arange(4.0), axis="w")


def test_axis_requires_1d():
    with pytest.raises(ValueError):
        make_inf_line(data=np.random.rand(4, 2), axis="x")


@pytest.mark.parametrize("axis", ["x", "y", "z"])
def test_per_line_position_update(axis):
    graphic = make_inf_line(data=np.array([0.0, 1.0, 2.0, 3.0]), axis=axis)

    graphic.data[1] = 5.0
    assert graphic.data.value[1] == 5.0

    buffer = graphic.world_object.geometry.positions.data
    # both endpoints of line 1 moved
    npt.assert_array_equal(buffer[2:4, AXES[axis]], [5.0, 5.0])


def test_per_line_endpoint_update():
    positions = np.array(
        [[0, 0, 0], [0, 1, 0], [1, 0, 0], [1, 1, 0]], dtype=np.float32
    )
    graphic = make_inf_line(data=positions, axis=None)

    graphic.data[0] = [[9, 0, 0], [9, 1, 0]]
    npt.assert_array_equal(
        graphic.world_object.geometry.positions.data[0:2], [[9, 0, 0], [9, 1, 0]]
    )


@pytest.mark.parametrize("axis", ["x", "y"])
def test_resize(axis):
    graphic = make_inf_line(data=np.array([0.0, 1.0, 2.0]), axis=axis)
    assert len(graphic.data) == 3

    graphic.data = np.array([0.0, 1.0, 2.0, 3.0, 4.0])
    assert len(graphic.data) == 5
    assert graphic.world_object.geometry.positions.data.shape == (10, 3)
    npt.assert_array_equal(graphic.data.value, [0, 1, 2, 3, 4])


def test_uniform_color():
    graphic = make_inf_line(data=np.arange(4.0), axis="x", colors="gray")
    assert isinstance(graphic._colors, UniformColor)
    assert graphic.colors == pygfx.Color("gray")


def test_per_line_colors():
    graphic = make_inf_line(
        data=np.arange(3.0), axis="x", colors=["r", "g", "b"]
    )
    assert isinstance(graphic._colors, InfLineColors)

    # one color per line, buffer has two vertices per line
    assert graphic.colors.value.shape == (3, 4)
    cbuffer = graphic.world_object.geometry.colors.data
    assert cbuffer.shape == (6, 4)

    # each line's two vertices share the color
    for i in range(3):
        npt.assert_array_equal(cbuffer[2 * i], cbuffer[2 * i + 1])

    npt.assert_array_equal(graphic.colors.value[0], [1, 0, 0, 1])  # red

    # per-line color update
    graphic.colors[2] = "yellow"
    npt.assert_array_equal(cbuffer[4], cbuffer[5])
    npt.assert_array_equal(graphic.colors.value[2], [1, 1, 0, 1])


def test_cmap():
    graphic = make_inf_line(data=np.arange(5.0), axis="y", cmap="jet")
    assert isinstance(graphic._cmap, VertexCmap)
    assert graphic.cmap.name == "matlab:jet"

    # a cmap replaces colors, the colormap is sampled through texcoords instead
    assert graphic._colors is None
    assert graphic.colors is None
    assert graphic.world_object.material.color_mode == "vertex_map"
    assert isinstance(graphic.world_object.material.map, pygfx.TextureMap)

    # two vertices per line, the default transform spans the colormap
    texcoords = graphic.world_object.geometry.texcoords.data
    assert texcoords.shape == (2 * len(graphic.data),)
    npt.assert_almost_equal(texcoords, np.linspace(0, 1, 2 * len(graphic.data)))

    # the transform is the texcoords, and its (min, max) is mapped onto the colormap
    npt.assert_almost_equal(graphic.cmap_transform, texcoords)
    assert graphic.cmap_range == (0.0, 1.0)
    assert graphic.world_object.material.maprange == graphic.cmap_range


def test_cmap_runtime():
    graphic = make_inf_line(data=np.arange(5.0), axis="x", cmap="jet")

    previous_map = graphic.world_object.material.map
    graphic.cmap = "plasma"
    assert graphic.cmap.name == "bids:plasma"
    # the material gets the new colormap texture
    assert graphic.world_object.material.map is not previous_map

    # one transform value per line is resampled over the two vertices of each line
    graphic.cmap_transform = np.array([0.0, 1.0, 2.0, 1.0, 0.0])
    texcoords = graphic.world_object.geometry.texcoords.data
    assert texcoords.shape == (2 * len(graphic.data),)
    npt.assert_almost_equal(
        texcoords,
        np.interp(np.linspace(0, 1, 10), np.linspace(0, 1, 5), [0.0, 1.0, 2.0, 1.0, 0.0]),
        decimal=5,
    )
    # the range follows the resampled transform
    npt.assert_almost_equal(graphic.cmap_range, (texcoords.min(), texcoords.max()))
    assert graphic.world_object.material.maprange == graphic.cmap_range

    # one color per line needs a transform per vertex, both endpoints of a line sharing a value
    graphic.cmap_transform = np.repeat([0.0, 1.0, 2.0, 1.0, 0.0], 2)
    texcoords = graphic.world_object.geometry.texcoords.data
    for i in range(len(graphic.data)):
        npt.assert_almost_equal(texcoords[2 * i], texcoords[2 * i + 1])


def test_empty_key_is_noop():
    graphic = make_inf_line(data=np.arange(4.0), axis="x", colors=["r", "g", "b", "y"])
    before = graphic.data.value.copy()

    # an all-False mask selects nothing and must be a no-op, not raise
    graphic.data[np.zeros(4, dtype=bool)] = 10.0
    graphic.colors[np.zeros(4, dtype=bool)] = "cyan"

    npt.assert_array_equal(graphic.data.value, before)


def test_endpoint_indexing():
    positions = np.array(
        [[0, 0, 0], [0, 1, 0], [1, 0, 0], [1, 1, 0]], dtype=np.float32
    )
    graphic = make_inf_line(data=positions, axis=None)

    # getter and setter are symmetric down to individual endpoints
    npt.assert_array_equal(graphic.data[0, 0], [0, 0, 0])
    graphic.data[0, 0] = [9, 9, 9]
    npt.assert_array_equal(graphic.world_object.geometry.positions.data[0], [9, 9, 9])
    # the other endpoint of line 0 is untouched
    npt.assert_array_equal(graphic.world_object.geometry.positions.data[1], [0, 1, 0])


def test_channel_color_indexing():
    graphic = make_inf_line(data=np.arange(3.0), axis="x", colors=["r", "g", "b"])

    # set only the RGB channels of line 0, leaving alpha unchanged
    graphic.colors[0, :-1] = [1.0, 1.0, 0.0]
    cbuffer = graphic.world_object.geometry.colors.data
    npt.assert_array_equal(cbuffer[0], [1.0, 1.0, 0.0, 1.0])
    npt.assert_array_equal(cbuffer[0], cbuffer[1])  # both vertices updated


@pytest.mark.parametrize(
    "pattern,expected",
    [
        ("--", (5, 5)),
        ("dashed", (5, 5)),
        (":", (0, 2)),
        ("dotted", (0, 2)),
        ("-.", (5, 2, 1, 2)),
        ((2, 3), (2, 3)),
    ],
)
def test_dash_pattern(pattern, expected):
    graphic = make_inf_line(data=np.arange(3.0), axis="x", dash_pattern=pattern)
    # value returns the user's input verbatim
    assert graphic.dash_pattern == pattern
    # the material receives the parsed tuple
    assert tuple(graphic.world_object.material.dash_pattern) == expected


@pytest.mark.parametrize("start,end", [(True, True), (False, True), (True, False)])
def test_start_end_is_infinite(start, end):
    graphic = make_inf_line(
        data=np.arange(3.0), axis="x", start_is_infinite=start, end_is_infinite=end
    )
    assert graphic.start_is_infinite is start
    assert graphic.end_is_infinite is end
    assert graphic.world_object.material.start_is_infinite is start
    assert graphic.world_object.material.end_is_infinite is end

    graphic.start_is_infinite = not start
    assert graphic.world_object.material.start_is_infinite is (not start)


def test_thin_not_supported():
    graphic = make_inf_line(data=np.arange(3.0), axis="x")
    assert graphic.thin is False
    with pytest.raises(NotImplementedError):
        graphic.thin = True


def test_selectors_not_supported():
    graphic = make_inf_line(data=np.arange(3.0), axis="x")
    for method in (
        graphic.add_linear_selector,
        graphic.add_linear_region_selector,
        graphic.add_rectangle_selector,
        graphic.add_polygon_selector,
    ):
        with pytest.raises(NotImplementedError):
            method()


def test_events():
    graphic = make_inf_line(
        data=np.arange(3.0), axis="x", colors=["r", "g", "b"]
    )

    events = dict()

    @graphic.add_event_handler("data")
    def _on_data(ev: GraphicFeatureEvent):
        events["data"] = ev

    @graphic.add_event_handler("colors")
    def _on_colors(ev: GraphicFeatureEvent):
        events["colors"] = ev

    @graphic.add_event_handler("dash_pattern")
    def _on_dash(ev: GraphicFeatureEvent):
        events["dash_pattern"] = ev

    graphic.data[0] = 10.0
    graphic.colors[1] = "cyan"
    graphic.dash_pattern = "--"

    assert set(events) == {"data", "colors", "dash_pattern"}
    assert events["dash_pattern"].info["value"] == "--"
