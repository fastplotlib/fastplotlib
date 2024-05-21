import numpy as np
from numpy import testing as npt
import pytest

import pygfx

from fastplotlib.graphics._features import ColorFeature, PointsDataFeature
from fastplotlib.graphics._features.utils import parse_colors


# TODO: parameterize every test where the color is given in as str, array, tuple, and list


def generate_color_inputs(name: str) -> list[str, np.ndarray, list, tuple]:
    color = pygfx.Color(name)

    s = name
    a = np.array(color)
    l = list(color)
    t = tuple(color)

    return [s, a, l, t]


def generate_slice_indices(kind: int):
    n_elements = 10
    a = np.arange(n_elements)

    match kind:
        case 0:
            # simplest, just int
            s = 2
            indices = [2]

        case 1:
            # everything
            s = slice(None, None, None)
            indices = list(range(10))

        case 2:
            # positive continuous range
            s = slice(1, 5, None)
            indices = list(range(1, 5))

        case 3:
            # positive stepped range
            s = slice(2, 8, 2)
            indices = [2, 4, 6]

        case 4:
            # negative continuous range
            s = slice(-5, None, None)
            indices = [5, 6, 7, 8, 9]

        case 5:
            # negative backwards
            s = slice(-5, None, -1)
            indices = [5, 4, 3, 2, 1, 0]

        case 5:
            # negative backwards stepped
            s = slice(-5, None, -2)
            indices = [5, 3, 1]

        case 6:
            # negative stepped forward
            s = slice(-5, None, 2)
            indices = [5, 7, 9]

        case 7:
            # both negative
            s = slice(-8, -2, None)
            indices = [2, 3, 4, 5, 6, 7]

        case 8:
            # both negative and stepped
            s = slice(-8, -2, 2)
            indices = [2, 4, 6]

        case 9:
            # positive, negative, negative
            s = slice(8, -9, -2)
            indices = [8, 6, 4, 2]

        case 10:
            # only stepped forward
            s = slice(None, None, 2)
            indices = [0, 2, 4, 6, 8]

        case 11:
            # only stepped backward
            s = slice(None, None, -3)
            indices = [9, 6, 3, 0]

        case 12:
            # list indices
            s = [2, 5, 9]
            indices = [2, 5, 9]

        case 13:
            # bool indices
            s = a > 5
            indices = [6, 7, 8, 9]

        case 14:
            # list indices with negatives
            s = [1, 4, -2]
            indices = [1, 4, 8]

        case 15:
            # array indices
            s = np.array([1, 4, -7, 9])
            indices = [1, 4, 3, 9]

    others = [i for i in a if i not in indices]

    return {"slice": s, "indices": indices, "others": others}


def make_colors_buffer() -> ColorFeature:
    colors = ColorFeature(colors="w", n_colors=10)
    return colors


def make_points_buffer():
    pass


def test_int():
    # setting single points
    colors = make_colors_buffer()
    # TODO: placeholder until I make a testing figure where we draw frames only on call
    colors.buffer._gfx_pending_uploads.clear()

    colors[3] = "r"
    npt.assert_almost_equal(colors[3], [1., 0., 0., 1.])
    assert colors.buffer._gfx_pending_uploads[-1] == (3, 1)

    colors[6] = [0., 1., 1., 1.]
    npt.assert_almost_equal(colors[6], [0., 1., 1., 1.])

    colors[7] = (0., 1., 1., 1.)
    npt.assert_almost_equal(colors[6], [0., 1., 1., 1.])

    colors[8] = np.array([1, 0, 1, 1])
    npt.assert_almost_equal(colors[8], [1., 0., 1., 1.])

    colors[2] = [1, 0, 1, 0.5]
    npt.assert_almost_equal(colors[2], [1., 0., 1., 0.5])


@pytest.mark.parametrize("slice_method", [generate_slice_indices(i) for i in range(0, 16)])
def test_tuple(slice_method):
    # setting entire array manually
    colors = make_colors_buffer()

    s = slice_method["slice"]
    indices = slice_method["indices"]
    others = slice_method["others"]

    # set all RGBA vals
    colors[s, :] = 0.5
    truth = np.repeat([[0.5, 0.5, 0.5, 0.5]], repeats=len(indices), axis=0)
    npt.assert_almost_equal(colors[indices], truth)

    # check others are not modified
    others_truth = np.repeat([[1., 1., 1., 1.]], repeats=len(others), axis=0)
    npt.assert_almost_equal(colors[others], others_truth)

    # reset
    colors[:] = (1, 1, 1, 1)
    npt.assert_almost_equal(colors[:], np.repeat([[1., 1., 1., 1.]], 10, axis=0))

    # set just R values
    colors[s, 0] = 0.5
    truth = np.repeat([[0.5, 1., 1., 1.]], repeats=len(indices), axis=0)
    # check others not modified
    npt.assert_almost_equal(colors[indices], truth)
    npt.assert_almost_equal(colors[others], others_truth)

    # reset
    colors[:] = (1, 1, 1, 1)
    npt.assert_almost_equal(colors[:], np.repeat([[1., 1., 1., 1.]], 10, axis=0))

    # set green and blue
    colors[s, 1:-1] = 0.7
    truth = np.repeat([[1., 0.7, 0.7, 1.0]], repeats=len(indices), axis=0)
    npt.assert_almost_equal(colors[indices], truth)
    npt.assert_almost_equal(colors[others], others_truth)

    # reset
    colors[:] = (1, 1, 1, 1)
    npt.assert_almost_equal(colors[:], np.repeat([[1., 1., 1., 1.]], 10, axis=0))

    # set only alpha
    colors[s, -1] = 0.2
    truth = np.repeat([[1., 1., 1., 0.2]], repeats=len(indices), axis=0)
    npt.assert_almost_equal(colors[indices], truth)
    npt.assert_almost_equal(colors[others], others_truth)


@pytest.mark.parametrize("color_input", generate_color_inputs("red"))
@pytest.mark.parametrize("slice_method", [generate_slice_indices(i) for i in range(1, 16)])
def test_slice(color_input, slice_method: dict):
    # slicing only first dim
    colors = make_colors_buffer()

    s = slice_method["slice"]
    indices = slice_method["indices"]
    others = slice_method["others"]

    colors[s] = color_input
    truth = np.repeat([pygfx.Color(color_input)], repeats=len(indices), axis=0)
    # check that correct indices are modified
    npt.assert_almost_equal(colors[s], truth)
    # check that others are not touched
    others_truth = np.repeat([[1., 1., 1., 1.]], repeats=len(others), axis=0)
    npt.assert_almost_equal(colors[others], others_truth)

    # reset
    colors[:] = (1, 1, 1, 1)
    npt.assert_almost_equal(colors[:], np.repeat([[1., 1., 1., 1.]], 10, axis=0))
