import numpy as np
from numpy import testing as npt
import pytest

from fastplotlib.graphics._features import PointsDataFeature
from .utils import generate_slice_indices, assert_pending_uploads


def generate_data(inputs: str) -> np.ndarray:
    """
    Generates a spiral/spring

    Only 10 points so a very pointy spiral but easier to spot changes :D
    """
    xs = np.linspace(0, 10 * np.pi, 10)
    ys = np.sin(xs)
    zs = np.cos(xs)

    match inputs:
        case "y":
            data = ys

        case "xy":
            data = np.column_stack([xs, ys])

        case "xyz":
            data = np.column_stack([xs, ys, zs])

    return data.astype(np.float32)


@pytest.mark.parametrize("data", [generate_data(v) for v in ["y", "xy", "xyz"]])
def test_create_buffer(data):
    points_data = PointsDataFeature(data)

    if data.ndim == 1:
        # only y-vals specified
        npt.assert_almost_equal(points_data[:, 1], generate_data("y"))
        # x-vals are auto generated just using arange
        npt.assert_almost_equal(points_data[:, 0], np.arange(data.size))

    elif data.shape[1] == 2:
        # test 2D
        npt.assert_almost_equal(points_data[:, :-1], generate_data("xy"))
        npt.assert_almost_equal(points_data[:, -1], 0.)


    elif data.shape[1] == 3:
        # test 3D spiral
        npt.assert_almost_equal(points_data[:], generate_data("xyz"))


def test_int():
    data = generate_data("xyz")
    # test setting single points
    points = PointsDataFeature(data)

    # set all x, y, z points, create a kink in the spiral
    points[2] = 1.
    npt.assert_almost_equal(points[2], 1.)
    # make sure other points are not affected
    indices = list(range(10))
    indices.pop(2)
    npt.assert_almost_equal(points[indices], data[indices])


@pytest.mark.parametrize("slice_method", [generate_slice_indices(i) for i in range(1, 16)])  # int tested separately
@pytest.mark.parametrize("test_axis", ["y", "xy", "xyz"])
def test_slice(slice_method: dict, test_axis: str):
    data = generate_data("xyz")

    s = slice_method["slice"]
    indices = slice_method["indices"]
    offset = slice_method["offset"]
    size = slice_method["size"]
    others = slice_method["others"]

    points = PointsDataFeature(data)
    # TODO: placeholder until I make a testing figure where we draw frames only on call
    points.buffer._gfx_pending_uploads.clear()

    match test_axis:
        case "y":
            points[s, 1] = -data[s, 1]
            npt.assert_almost_equal(points[s, 1], -data[s, 1])
            npt.assert_almost_equal(points[indices, 1], -data[indices, 1])
            # make sure other points are not modified
            npt.assert_almost_equal(points[others, 1], data[others, 1])  # other points in same dimension
            npt.assert_almost_equal(points[:, 2:], data[:, 2:])  # dimensions that are not sliced

        case "xy":
            points[s, :-1] = -data[s, :-1]
            npt.assert_almost_equal(points[s, :-1], -data[s, :-1])
            npt.assert_almost_equal(points[indices, :-1], -data[s, :-1])
            # make sure other points are not modified
            npt.assert_almost_equal(points[others, :-1], data[others, :-1])  # other points in the same dimensions
            npt.assert_almost_equal(points[:, -1], data[:, -1])  # dimensions that are not touched

        case "xyz":
            points[s] = -data[s]
            npt.assert_almost_equal(points[s], -data[s])
            npt.assert_almost_equal(points[indices], -data[s])
            # make sure other points are not modified
            npt.assert_almost_equal(points[others], data[others])

    # make sure correct offset and size marked for pending upload
    assert_pending_uploads(points.buffer, offset, size)
