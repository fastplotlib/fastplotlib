import numpy as np
from numpy import testing as npt
import pytest

import pygfx

import fastplotlib as fpl
from fastplotlib.graphics._features import VertexColors, FeatureEvent
from .utils import (
    generate_slice_indices,
    generate_color_inputs,
    generate_positions_spiral_data,
)


def make_colors_buffer() -> VertexColors:
    colors = VertexColors(colors="w", n_colors=10)
    return colors


EVENT_RETURN_VALUE: FeatureEvent = None


def event_handler(ev):
    global EVENT_RETURN_VALUE
    EVENT_RETURN_VALUE = ev


@pytest.mark.parametrize(
    "color_input",
    [
        *generate_color_inputs("r"),
        *generate_color_inputs("g"),
        *generate_color_inputs("b"),
    ],
)
def test_create_buffer(color_input):
    colors = VertexColors(colors=color_input, n_colors=10)
    truth = np.repeat([pygfx.Color(color_input)], 10, axis=0)
    npt.assert_almost_equal(colors[:], truth)


@pytest.mark.parametrize("test_graphic", [False, "line", "scatter"])
def test_int(test_graphic):
    # setting single points
    if test_graphic:
        fig = fpl.Figure()

        data = generate_positions_spiral_data("xyz")
        if test_graphic == "line":
            graphic = fig[0, 0].add_line(data=data)

        elif test_graphic == "scatter":
            graphic = fig[0, 0].add_scatter(data=data)

        colors = graphic.colors
        global EVENT_RETURN_VALUE
        graphic.add_event_handler(event_handler, "colors")
    else:
        colors = make_colors_buffer()

    # TODO: placeholder until I make a testing figure where we draw frames only on call
    colors[3] = "r"
    npt.assert_almost_equal(colors[3], [1.0, 0.0, 0.0, 1.0])

    if test_graphic:
        # test event
        assert isinstance(EVENT_RETURN_VALUE, FeatureEvent)
        assert EVENT_RETURN_VALUE.graphic == graphic
        assert EVENT_RETURN_VALUE.target is graphic.world_object
        assert EVENT_RETURN_VALUE.info["key"] == 3
        npt.assert_almost_equal(
            EVENT_RETURN_VALUE.info["value"], np.array([[1, 0, 0, 1]])
        )
        assert EVENT_RETURN_VALUE.info["user_value"] == "r"

    colors[6] = [0.0, 1.0, 1.0, 1.0]
    npt.assert_almost_equal(colors[6], [0.0, 1.0, 1.0, 1.0])

    colors[7] = (0.0, 1.0, 1.0, 1.0)
    npt.assert_almost_equal(colors[6], [0.0, 1.0, 1.0, 1.0])

    colors[8] = np.array([1, 0, 1, 1])
    npt.assert_almost_equal(colors[8], [1.0, 0.0, 1.0, 1.0])

    colors[2] = [1, 0, 1, 0.5]
    npt.assert_almost_equal(colors[2], [1.0, 0.0, 1.0, 0.5])


@pytest.mark.parametrize("test_graphic", [False, "line", "scatter"])
@pytest.mark.parametrize(
    "slice_method", [generate_slice_indices(i) for i in range(0, 16)]
)
def test_tuple(test_graphic, slice_method):
    # setting entire array manually
    if test_graphic:
        fig = fpl.Figure()

        data = generate_positions_spiral_data("xyz")
        if test_graphic == "line":
            graphic = fig[0, 0].add_line(data=data)

        elif test_graphic == "scatter":
            graphic = fig[0, 0].add_scatter(data=data)

        colors = graphic.colors
        global EVENT_RETURN_VALUE
        graphic.add_event_handler(event_handler, "colors")
    else:
        colors = make_colors_buffer()

    s = slice_method["slice"]
    indices = slice_method["indices"]
    others = slice_method["others"]

    # set all RGBA vals
    colors[s, :] = 0.5
    truth = np.repeat([[0.5, 0.5, 0.5, 0.5]], repeats=len(indices), axis=0)
    npt.assert_almost_equal(colors[indices], truth)

    if test_graphic:
        # test event
        assert isinstance(EVENT_RETURN_VALUE, FeatureEvent)
        assert EVENT_RETURN_VALUE.graphic == graphic
        assert EVENT_RETURN_VALUE.target is graphic.world_object
        assert EVENT_RETURN_VALUE.info["key"] == (s, slice(None))
        npt.assert_almost_equal(EVENT_RETURN_VALUE.info["value"], truth)
        assert EVENT_RETURN_VALUE.info["user_value"] == 0.5

    # check others are not modified
    others_truth = np.repeat([[1.0, 1.0, 1.0, 1.0]], repeats=len(others), axis=0)
    npt.assert_almost_equal(colors[others], others_truth)

    # reset
    if test_graphic:
        # test setter
        graphic.colors = "w"
    else:
        colors[:] = [1, 1, 1, 1]
    truth = np.repeat([[1.0, 1.0, 1.0, 1.0]], 10, axis=0)
    npt.assert_almost_equal(colors[:], truth)

    if test_graphic:
        # test event
        assert isinstance(EVENT_RETURN_VALUE, FeatureEvent)
        assert EVENT_RETURN_VALUE.graphic == graphic
        assert EVENT_RETURN_VALUE.target is graphic.world_object
        assert EVENT_RETURN_VALUE.info["key"] == slice(None)
        npt.assert_almost_equal(EVENT_RETURN_VALUE.info["value"], truth)
        assert EVENT_RETURN_VALUE.info["user_value"] == "w"

    # set just R values
    colors[s, 0] = 0.5
    truth = np.repeat([[0.5, 1.0, 1.0, 1.0]], repeats=len(indices), axis=0)
    # check others not modified
    npt.assert_almost_equal(colors[indices], truth)
    npt.assert_almost_equal(colors[others], others_truth)

    # reset
    colors[:] = (1, 1, 1, 1)
    npt.assert_almost_equal(colors[:], np.repeat([[1.0, 1.0, 1.0, 1.0]], 10, axis=0))

    # set green and blue
    colors[s, 1:-1] = 0.7
    truth = np.repeat([[1.0, 0.7, 0.7, 1.0]], repeats=len(indices), axis=0)
    npt.assert_almost_equal(colors[indices], truth)
    npt.assert_almost_equal(colors[others], others_truth)

    # reset
    colors[:] = (1, 1, 1, 1)
    npt.assert_almost_equal(colors[:], np.repeat([[1.0, 1.0, 1.0, 1.0]], 10, axis=0))

    # set only alpha
    colors[s, -1] = 0.2
    truth = np.repeat([[1.0, 1.0, 1.0, 0.2]], repeats=len(indices), axis=0)
    npt.assert_almost_equal(colors[indices], truth)
    npt.assert_almost_equal(colors[others], others_truth)


@pytest.mark.parametrize("color_input", generate_color_inputs("red"))
# skip testing with int since that results in shape [1, 4] with np.repeat, int tested in independent unit test
@pytest.mark.parametrize(
    "slice_method", [generate_slice_indices(i) for i in range(1, 16)]
)
@pytest.mark.parametrize("test_graphic", [False, "line", "scatter"])
def test_slice(color_input, slice_method: dict, test_graphic: bool):
    # slicing only first dim
    if test_graphic:
        fig = fpl.Figure()

        data = generate_positions_spiral_data("xyz")
        if test_graphic == "line":
            graphic = fig[0, 0].add_line(data=data)

        elif test_graphic == "scatter":
            graphic = fig[0, 0].add_scatter(data=data)

        colors = graphic.colors

        global EVENT_RETURN_VALUE
        graphic.add_event_handler(event_handler, "colors")
    else:
        colors = make_colors_buffer()

    s = slice_method["slice"]
    indices = slice_method["indices"]
    offset = slice_method["offset"]
    size = slice_method["size"]
    others = slice_method["others"]

    colors[s] = color_input
    truth = np.repeat([pygfx.Color(color_input)], repeats=len(indices), axis=0)
    # check that correct indices are modified
    npt.assert_almost_equal(colors[s], truth)
    npt.assert_almost_equal(colors[indices], truth)

    # check event
    if test_graphic:
        global EVENT_RETURN_VALUE

        assert isinstance(EVENT_RETURN_VALUE, FeatureEvent)
        assert EVENT_RETURN_VALUE.graphic == graphic
        assert EVENT_RETURN_VALUE.target is graphic.world_object
        if isinstance(s, slice):
            assert EVENT_RETURN_VALUE.info["key"] == s
        else:
            npt.assert_almost_equal(EVENT_RETURN_VALUE.info["key"], s)
        npt.assert_almost_equal(EVENT_RETURN_VALUE.info["value"], truth)
        if isinstance(color_input, str):
            assert EVENT_RETURN_VALUE.info["user_value"] == color_input
        else:
            npt.assert_almost_equal(EVENT_RETURN_VALUE.info["user_value"], color_input)

    # check that others are not touched
    others_truth = np.repeat([[1.0, 1.0, 1.0, 1.0]], repeats=len(others), axis=0)
    npt.assert_almost_equal(colors[others], others_truth)

    # reset
    colors[:] = (1, 1, 1, 1)
    npt.assert_almost_equal(colors[:], np.repeat([[1.0, 1.0, 1.0, 1.0]], 10, axis=0))
