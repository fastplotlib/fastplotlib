import numpy as np
from numpy import testing as npt
import pytest

import pygfx

from fastplotlib.graphics._features import ColorFeature
from .utils import generate_slice_indices, assert_pending_uploads


def generate_color_inputs(name: str) -> list[str, np.ndarray, list, tuple]:
    color = pygfx.Color(name)

    s = name
    a = np.array(color)
    l = list(color)
    t = tuple(color)

    return [s, a, l, t]


def make_colors_buffer() -> ColorFeature:
    colors = ColorFeature(colors="w", n_colors=10)
    return colors


@pytest.mark.parametrize("color_input", [*generate_color_inputs("r"), *generate_color_inputs("g"), *generate_color_inputs("b")])
def test_create_buffer(color_input):
    colors = ColorFeature(colors=color_input, n_colors=10)
    truth = np.repeat([pygfx.Color(color_input)], 10, axis=0)
    npt.assert_almost_equal(colors[:], truth)


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
# skip testing with int since that results in shape [1, 4] with np.repeat, int tested in independent unit test
@pytest.mark.parametrize("slice_method", [generate_slice_indices(i) for i in range(1, 16)])
def test_slice(color_input, slice_method: dict):
    # slicing only first dim
    colors = make_colors_buffer()

    # TODO: placeholder until I make a testing figure where we draw frames only on call
    colors.buffer._gfx_pending_uploads.clear()

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

    # make sure correct offset and size marked for pending upload
    assert_pending_uploads(colors.buffer, offset, size)

    # check that others are not touched
    others_truth = np.repeat([[1., 1., 1., 1.]], repeats=len(others), axis=0)
    npt.assert_almost_equal(colors[others], others_truth)

    # reset
    colors[:] = (1, 1, 1, 1)
    npt.assert_almost_equal(colors[:], np.repeat([[1., 1., 1., 1.]], 10, axis=0))
