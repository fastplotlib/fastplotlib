import numpy as np
from numpy import testing as npt

from fastplotlib.graphics._features import ColorFeature, PointsDataFeature
from fastplotlib.graphics._features.utils import parse_colors


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


def test_slice():
    # slicing only first dim
    colors = make_colors_buffer()

    colors[1:3] = "r"
    npt.assert_almost_equal(colors[1:3], [0.5, 0.5, 0.5, 0.5])



def test_array():
    pass
