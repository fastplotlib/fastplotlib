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


def test_tuple():
    # setting entire array manually
    colors = make_colors_buffer()

    colors[1, :] = 0.5
    npt.assert_almost_equal(colors[1], [0.5, 0.5, 0.5, 0.5])

    colors[1, 0] = 1
    npt.assert_almost_equal(colors[1], [1., 0.5, 0.5, 0.5])

    colors[1, 2:] = 0.7
    npt.assert_almost_equal(colors[1], [1., 0.5, 0.7, 0.7])

    colors[1, -1] = 0.2
    npt.assert_almost_equal(colors[1], [1., 0.5, 0.7, 0.2])


@pytest.mark.parametrize("color_input", generate_color_inputs("red"))
@pytest.mark.parametrize("slice_method", [generate_slice_indices(i) for i in range(1, 10)])
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


def test_array():
    pass
