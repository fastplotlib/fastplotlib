import numpy as np
from numpy import testing as npt
import pytest

import fastplotlib as fpl
from fastplotlib.graphics._features import VertexPositions, FeatureEvent
from .utils import (
    generate_slice_indices,
    generate_positions_spiral_data,
)


EVENT_RETURN_VALUE: FeatureEvent = None


def event_handler(ev):
    global EVENT_RETURN_VALUE
    EVENT_RETURN_VALUE = ev


@pytest.mark.parametrize(
    "data", [generate_positions_spiral_data(v) for v in ["y", "xy", "xyz"]]
)
def test_create_buffer(data):
    points_data = VertexPositions(data)

    if data.ndim == 1:
        # only y-vals specified
        npt.assert_almost_equal(points_data[:, 1], generate_positions_spiral_data("y"))
        # x-vals are auto generated just using arange
        npt.assert_almost_equal(points_data[:, 0], np.arange(data.size))

    elif data.shape[1] == 2:
        # test 2D
        npt.assert_almost_equal(
            points_data[:, :-1], generate_positions_spiral_data("xy")
        )
        npt.assert_almost_equal(points_data[:, -1], 0.0)

    elif data.shape[1] == 3:
        # test 3D spiral
        npt.assert_almost_equal(points_data[:], generate_positions_spiral_data("xyz"))


@pytest.mark.parametrize("test_graphic", [False, "line", "scatter"])
def test_int(test_graphic):
    # test setting single points

    data = generate_positions_spiral_data("xyz")
    if test_graphic:
        fig = fpl.Figure()

        if test_graphic == "line":
            graphic = fig[0, 0].add_line(data=data)

        elif test_graphic == "scatter":
            graphic = fig[0, 0].add_scatter(data=data)

        points = graphic.data
        global EVENT_RETURN_VALUE
        graphic.add_event_handler(event_handler, "data")
    else:
        points = VertexPositions(data)

    # set all x, y, z points, create a kink in the spiral
    points[2] = 1.0
    npt.assert_almost_equal(points[2], 1.0)
    # make sure other points are not affected
    indices = list(range(10))
    indices.pop(2)
    npt.assert_almost_equal(points[indices], data[indices])

    # check event
    if test_graphic:
        assert isinstance(EVENT_RETURN_VALUE, FeatureEvent)
        assert EVENT_RETURN_VALUE.graphic == graphic
        assert EVENT_RETURN_VALUE.target is graphic.world_object
        assert EVENT_RETURN_VALUE.info["key"] == 2
        npt.assert_almost_equal(EVENT_RETURN_VALUE.info["value"], 1.0)

    # reset
    if test_graphic:
        graphic.data = data
    else:
        points[:] = data
    npt.assert_almost_equal(points[:], data)

    # check event
    if test_graphic:
        assert isinstance(EVENT_RETURN_VALUE, FeatureEvent)
        assert EVENT_RETURN_VALUE.graphic == graphic
        assert EVENT_RETURN_VALUE.target is graphic.world_object
        assert EVENT_RETURN_VALUE.info["key"] == slice(None)
        npt.assert_almost_equal(EVENT_RETURN_VALUE.info["value"], data)

    # just set y value
    points[3, 1] = 1.0
    npt.assert_almost_equal(points[3, 1], 1.0)
    # make sure others not modified
    npt.assert_almost_equal(points[3, 0], data[3, 0])
    npt.assert_almost_equal(points[3, 2], data[3, 2])
    indices = list(range(10))
    indices.pop(3)
    npt.assert_almost_equal(points[indices], data[indices])


@pytest.mark.parametrize("test_graphic", [False, "line", "scatter"])
@pytest.mark.parametrize(
    "slice_method", [generate_slice_indices(i) for i in range(1, 16)]
)  # int tested separately
@pytest.mark.parametrize("test_axis", ["y", "xy", "xyz"])
def test_slice(test_graphic, slice_method: dict, test_axis: str):
    data = generate_positions_spiral_data("xyz")

    if test_graphic:
        fig = fpl.Figure()

        if test_graphic == "line":
            graphic = fig[0, 0].add_line(data=data)

        elif test_graphic == "scatter":
            graphic = fig[0, 0].add_scatter(data=data)

        points = graphic.data
        global EVENT_RETURN_VALUE
        graphic.add_event_handler(event_handler, "data")
    else:
        points = VertexPositions(data)

    s = slice_method["slice"]
    indices = slice_method["indices"]
    offset = slice_method["offset"]
    size = slice_method["size"]
    others = slice_method["others"]

    match test_axis:
        case "y":
            points[s, 1] = -data[s, 1]
            npt.assert_almost_equal(points[s, 1], -data[s, 1])
            npt.assert_almost_equal(points[indices, 1], -data[indices, 1])
            # make sure other points are not modified
            npt.assert_almost_equal(
                points[others, 1], data[others, 1]
            )  # other points in same dimension
            npt.assert_almost_equal(
                points[:, 2:], data[:, 2:]
            )  # dimensions that are not sliced

            # check event
            if test_graphic:
                assert isinstance(EVENT_RETURN_VALUE, FeatureEvent)
                assert EVENT_RETURN_VALUE.graphic == graphic
                assert EVENT_RETURN_VALUE.target is graphic.world_object
                if isinstance(s, slice):
                    assert EVENT_RETURN_VALUE.info["key"] == (s, 1)
                else:
                    npt.assert_almost_equal(EVENT_RETURN_VALUE.info["key"][0], s)
                    assert EVENT_RETURN_VALUE.info["key"][1] == 1
                npt.assert_almost_equal(EVENT_RETURN_VALUE.info["value"], -data[s, 1])

        case "xy":
            points[s, :-1] = -data[s, :-1]
            npt.assert_almost_equal(points[s, :-1], -data[s, :-1])
            npt.assert_almost_equal(points[indices, :-1], -data[s, :-1])
            # make sure other points are not modified
            npt.assert_almost_equal(
                points[others, :-1], data[others, :-1]
            )  # other points in the same dimensions
            npt.assert_almost_equal(
                points[:, -1], data[:, -1]
            )  # dimensions that are not touched

            # check event
            if test_graphic:
                assert isinstance(EVENT_RETURN_VALUE, FeatureEvent)
                assert EVENT_RETURN_VALUE.graphic == graphic
                assert EVENT_RETURN_VALUE.target is graphic.world_object
                if isinstance(s, slice):
                    assert EVENT_RETURN_VALUE.info["key"] == (s, slice(None, -1, None))
                else:
                    npt.assert_almost_equal(EVENT_RETURN_VALUE.info["key"][0], s)
                    assert EVENT_RETURN_VALUE.info["key"][1] == slice(None, -1, None)
                npt.assert_almost_equal(EVENT_RETURN_VALUE.info["value"], -data[s, :-1])

        case "xyz":
            points[s] = -data[s]
            npt.assert_almost_equal(points[s], -data[s])
            npt.assert_almost_equal(points[indices], -data[s])
            # make sure other points are not modified
            npt.assert_almost_equal(points[others], data[others])

            # check event
            if test_graphic:
                assert isinstance(EVENT_RETURN_VALUE, FeatureEvent)
                assert EVENT_RETURN_VALUE.graphic == graphic
                assert EVENT_RETURN_VALUE.target is graphic.world_object
                if isinstance(s, slice):
                    assert EVENT_RETURN_VALUE.info["key"] == s
                else:
                    npt.assert_almost_equal(EVENT_RETURN_VALUE.info["key"], s)
                npt.assert_almost_equal(EVENT_RETURN_VALUE.info["value"], -data[s])
