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


@pytest.mark.parametrize("color1", generate_color_inputs("red"))
@pytest.mark.parametrize("color2", generate_color_inputs("green"))
@pytest.mark.parametrize("color3", generate_color_inputs("blue"))
def test_slice(color1, color2, color3):
    # slicing only first dim
    colors = make_colors_buffer()

    colors[1:3] = color1
    truth = np.repeat([pygfx.Color(color1)], repeats=2, axis=0)
    npt.assert_almost_equal(colors[1:3], truth)

    colors[:] = "w"
    npt.assert_almost_equal(colors[:], np.repeat([[1., 1., 1., 1.]], 10, axis=0))

    colors[2:8:2] = color2  # set index 2, 4, 6 to color2
    truth = np.repeat([pygfx.Color(color2)], repeats=3, axis=0)
    npt.assert_almost_equal(colors[2:8:2], truth)
    # make sure others are not changed
    others = [0, 1, 3, 5, 7, 8, 9]
    npt.assert_almost_equal(colors[others], np.repeat([[1., 1., 1., 1.]], repeats=7, axis=0))

    # set the others to color3
    colors[others] = color3
    truth = np.repeat([pygfx.Color(color3)], repeats=len(others), axis=0)
    npt.assert_almost_equal(colors[others], truth)
    # make sure color2 items are not touched
    npt.assert_almost_equal(colors[2:8:2], np.repeat([pygfx.Color(color2)], repeats=3, axis=0))

    # reset
    colors[:] = (1, 1, 1, 1)

    # negative slicing
    colors[-5:] = color1
    truth = np.repeat([pygfx.Color(color1)], repeats=5, axis=0)
    npt.assert_almost_equal(colors[-5:], truth)

    # set some to color2
    colors[-5:-1:2] = color2
    truth = np.repeat([pygfx.Color(color2)], 2, axis=0)
    npt.assert_almost_equal(colors[[5, 7]], truth)
    # make sure non-sliced not touched
    npt.assert_almost_equal(colors[[6, 8, 9]], np.repeat([pygfx.Color(color1)], 3, axis=0))
    # make sure white non-sliced not touched
    npt.assert_almost_equal(colors[:-5], np.repeat([[1., 1., 1., 1.]], 5, axis=0))

    # negative slicing backwards, set points 5, 3
    colors[-5:1:-2] = color3
    truth = np.repeat([pygfx.Color(color3)], repeats=2, axis=0)
    npt.assert_almost_equal(colors[[5, 3]], truth)
    # make sure others are not touched
    npt.assert_almost_equal(colors[[0, 1, 2]], np.repeat([[1., 1., 1., 1.]], repeats=3, axis=0))
    # this point should be color2
    npt.assert_almost_equal(colors[7], np.array(pygfx.Color(color2)))
    # point 4 should be completely untouched
    npt.assert_almost_equal(colors[4], [1, 1, 1, 1])
    # rest should be color1
    npt.assert_almost_equal(colors[[6, 8, 9]], np.repeat([pygfx.Color(color1)], 3, axis=0))


def test_array():
    pass
