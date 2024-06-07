import numpy as np
from numpy import testing as npt
import pytest

import pygfx

import fastplotlib as fpl
from fastplotlib.graphics._features import (
    VertexPositions,
    VertexColors,
    VertexCmap,
    UniformColor,
    UniformSizes,
    PointsSizesFeature,
)

from .utils import generate_positions_spiral_data, generate_color_inputs


# TODO: use same functions to generate data and colors for graphics as the buffer test modules


def test_data_slice():
    pass


def test_color_slice():
    pass


def test_cmap_slice():
    pass


def test_sizes_slice():
    pass


def test_change_thickness():
    pass


def test_uniform_color():
    pass


def test_uniform_size():
    pass


@pytest.mark.parametrize(
    "data", [generate_positions_spiral_data(v) for v in ["y", "xy", "xyz"]]
)
@pytest.mark.parametrize(
    "colors", [None, *generate_color_inputs("r")]
)
@pytest.mark.parametrize(
    "uniform_colors", [None, True]
)
@pytest.mark.parametrize(
    "alpha", [None, 0.5, 0.0]
)
def test_create_line(
        data,
        colors,
        uniform_colors,
        alpha,
        # cmap,
        # cmap_values,
        # thickness
):
    # test creating line with all combinations of arguments

    fig = fpl.Figure()

    kwargs = dict()
    for kwarg in ["colors", "uniform_colors", "alpha"]:#, "cmap", "cmap_values", "thickness"]:
        if locals()[kwarg] is not None:
            # add to dict of arguments that will be passed
            kwargs[kwarg] = locals()[kwarg]

    lg = fig[0, 0].add_line(data=data, **kwargs)

    # n_datapoints must match
    assert len(lg.data.value) == len(data)

    # make sure data is correct
    match data.shape[-1]:
        case 1:  # only y-vals given
            npt.assert_almost_equal(lg.data[:, 1], data)  # y vals must match
            npt.assert_almost_equal(
                lg.data[:, 0], np.arange(data.size)
            )  # VertexData makes x-vals with arange
            npt.assert_almost_equal(lg.data[:, -1], 0)  # z-vals must be zeros
        case 2:  # xy vals given
            npt.assert_almost_equal(lg.data[:, :-1], data)  # x and y must match
            npt.assert_almost_equal(lg.data[:, -1], 0)  # z-vals must be zero
        case 3:  # xyz vals given
            npt.assert_almost_equal(lg.data[:], data[:])  # everything must match

    if alpha is None:  # default arg
        alpha = 1

    if uniform_colors is None:  # default arg
        uniform_colors = False

    # make sure colors are correct
    if not uniform_colors:
        assert isinstance(lg._colors, VertexColors)
        assert isinstance(lg.colors, VertexColors)
        if colors is None:
            # should be default, "w"
            npt.assert_almost_equal(lg.colors.value, np.repeat([[1, 1, 1, alpha]], repeats=len(lg.data), axis=0))
        else:
            # should be red, regardless of input variant (i.e. str, array, RGBA tuple, etc.
            npt.assert_almost_equal(lg.colors.value, np.repeat([[1, 0, 0, alpha]], repeats=len(lg.data), axis=0))

    else:
        assert isinstance(lg._colors, UniformColor)
        assert isinstance(lg.colors, pygfx.Color)
        if colors is None:
            # default "w"
            assert lg.colors == pygfx.Color("w")
        else:
            assert lg.colors == pygfx.Color("r")



def test_create_scatter():
    pass


def test_line_feature_events():
    pass


def test_scatter_feature_events():
    pass
