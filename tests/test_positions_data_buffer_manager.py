import numpy as np
from numpy import testing as npt
import pytest

import fastplotlib as fpl
from fastplotlib.graphics._features import VertexPositions
from .utils import (
    generate_slice_indices,
    assert_pending_uploads,
    generate_positions_spiral_data,
)


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


def test_int():
    data = generate_positions_spiral_data("xyz")
    # test setting single points
    points = VertexPositions(data)

    # set all x, y, z points, create a kink in the spiral
    points[2] = 1.0
    npt.assert_almost_equal(points[2], 1.0)
    # make sure other points are not affected
    indices = list(range(10))
    indices.pop(2)
    npt.assert_almost_equal(points[indices], data[indices])

    # reset
    points = data
    npt.assert_almost_equal(points[:], data)

    # just set y value
    points[3, 1] = 1.0
    npt.assert_almost_equal(points[3, 1], 1.0)
    # make sure others not modified
    npt.assert_almost_equal(points[3, 0], data[3, 0])
    npt.assert_almost_equal(points[3, 2], data[3, 2])
    indices = list(range(10))
    indices.pop(3)
    npt.assert_almost_equal(points[indices], data[indices])


@pytest.mark.parametrize("graphic_type", [None, "line", "scatter"])
@pytest.mark.parametrize(
    "slice_method", [generate_slice_indices(i) for i in range(1, 16)]
)  # int tested separately
@pytest.mark.parametrize("test_axis", ["y", "xy", "xyz"])
def test_slice(graphic_type, slice_method: dict, test_axis: str):
    data = generate_positions_spiral_data("xyz")

    if graphic_type is not None:
        fig = fpl.Figure()

        if graphic_type == "line":
            graphic = fig[0, 0].add_line(data=data)

        elif graphic_type == "scatter":
            graphic = fig[0, 0].add_scatter(data=data)

        points = graphic.data

    else:
        points = VertexPositions(data)

    s = slice_method["slice"]
    indices = slice_method["indices"]
    offset = slice_method["offset"]
    size = slice_method["size"]
    others = slice_method["others"]

    # TODO: placeholder until I make a testing figure where we draw frames only on call
    points.buffer._gfx_pending_uploads.clear()

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

        case "xyz":
            points[s] = -data[s]
            npt.assert_almost_equal(points[s], -data[s])
            npt.assert_almost_equal(points[indices], -data[s])
            # make sure other points are not modified
            npt.assert_almost_equal(points[others], data[others])

    # make sure correct offset and size marked for pending upload
    assert_pending_uploads(points.buffer, offset, size)
