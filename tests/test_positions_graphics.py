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
    UniformSize,
    PointsSizesFeature,
    Thickness,
    FeatureEvent
)

from .utils import (
    generate_positions_spiral_data,
    generate_color_inputs,
    MULTI_COLORS_TRUTH,
    generate_slice_indices,
    assert_pending_uploads,
)


TRUTH_CMAPS = {
    "jet": np.array(
        [
            [0.0, 0.0, 0.5, 1.0],
            [0.0, 0.0, 0.99910873, 1.0],
            [0.0, 0.37843138, 1.0, 1.0],
            [0.0, 0.8333333, 1.0, 1.0],
            [0.30044276, 1.0, 0.66729915, 1.0],
            [0.65464896, 1.0, 0.31309298, 1.0],
            [1.0, 0.90123457, 0.0, 1.0],
            [1.0, 0.4945534, 0.0, 1.0],
            [1.0, 0.08787218, 0.0, 1.0],
            [0.5, 0.0, 0.0, 1.0],
        ],
        dtype=np.float32,
    ),
    "viridis": np.array(
        [
            [0.267004, 0.004874, 0.329415, 1.0],
            [0.281412, 0.155834, 0.469201, 1.0],
            [0.244972, 0.287675, 0.53726, 1.0],
            [0.190631, 0.407061, 0.556089, 1.0],
            [0.147607, 0.511733, 0.557049, 1.0],
            [0.119483, 0.614817, 0.537692, 1.0],
            [0.20803, 0.718701, 0.472873, 1.0],
            [0.421908, 0.805774, 0.35191, 1.0],
            [0.699415, 0.867117, 0.175971, 1.0],
            [0.993248, 0.906157, 0.143936, 1.0],
        ],
        dtype=np.float32,
    ),
}


EVENT_RETURN_VALUE: FeatureEvent = None


def event_handler(ev):
    global EVENT_RETURN_VALUE
    EVENT_RETURN_VALUE = ev


# TODO: data slice int
def test_data_slice_int():
    pass

@pytest.mark.parametrize("graphic_type", ["line", "scatter"])
@pytest.mark.parametrize(
    "slice_method", [generate_slice_indices(i) for i in range(1, 16)]
)  # same as slice methods in the buffer tests
@pytest.mark.parametrize("test_axis", ["y", "xy", "xyz"])
def test_data_slice(graphic_type, slice_method, test_axis):
    fig = fpl.Figure()

    data = generate_positions_spiral_data("xyz")

    if graphic_type == "line":
        graphic = fig[0, 0].add_line(data=data)

    elif graphic_type == "scatter":
        graphic = fig[0, 0].add_scatter(data=data)

    s = slice_method["slice"]
    indices = slice_method["indices"]
    offset = slice_method["offset"]
    size = slice_method["size"]
    others = slice_method["others"]

    # TODO: placeholder until I make a testing figure where we draw frames only on call
    graphic.data.buffer._gfx_pending_uploads.clear()

    match test_axis:
        case "y":
            graphic.data[s, 1] = -data[s, 1]
            npt.assert_almost_equal(graphic.data[s, 1], -data[s, 1])
            npt.assert_almost_equal(graphic.data[indices, 1], -data[indices, 1])
            # make sure other points are not modified
            npt.assert_almost_equal(
                graphic.data[others, 1], data[others, 1]
            )  # other points in same dimension
            npt.assert_almost_equal(
                graphic.data[:, 2:], data[:, 2:]
            )  # dimensions that are not sliced

        case "xy":
            graphic.data[s, :-1] = -data[s, :-1]
            npt.assert_almost_equal(graphic.data[s, :-1], -data[s, :-1])
            npt.assert_almost_equal(graphic.data[indices, :-1], -data[s, :-1])
            # make sure other points are not modified
            npt.assert_almost_equal(
                graphic.data[others, :-1], data[others, :-1]
            )  # other points in the same dimensions
            npt.assert_almost_equal(
                graphic.data[:, -1], data[:, -1]
            )  # dimensions that are not touched

        case "xyz":
            graphic.data[s] = -data[s]
            npt.assert_almost_equal(graphic.data[s], -data[s])
            npt.assert_almost_equal(graphic.data[indices], -data[s])
            # make sure other points are not modified
            npt.assert_almost_equal(graphic.data[others], data[others])

    # make sure correct offset and size marked for pending upload
    assert_pending_uploads(graphic.data.buffer, offset, size)


def test_sizes_slice():
    pass


def test_change_thickness():
    pass


@pytest.mark.parametrize("graphic_type", ["line", "scatter"])
@pytest.mark.parametrize("colors", [None, *generate_color_inputs("b")])
@pytest.mark.parametrize("uniform_color", [True, False])
@pytest.mark.parametrize("alpha", [1.0, 0.5, 0.0])
def test_uniform_color(graphic_type, colors, uniform_color, alpha):
    fig = fpl.Figure()

    kwargs = dict()
    for kwarg in ["colors", "uniform_color", "alpha"]:
        if locals()[kwarg] is not None:
            # add to dict of arguments that will be passed
            kwargs[kwarg] = locals()[kwarg]

    data = generate_positions_spiral_data("xy")

    if graphic_type == "line":
        graphic = fig[0, 0].add_line(data=data, **kwargs)
    elif graphic_type == "scatter":
        graphic = fig[0, 0].add_scatter(data=data, **kwargs)

    if uniform_color:
        assert isinstance(graphic._colors, UniformColor)
        assert isinstance(graphic.colors, pygfx.Color)
        if colors is None:
            # default white
            assert graphic.colors == pygfx.Color([1, 1, 1, alpha])
        else:
            # should be blue
            assert graphic.colors == pygfx.Color([0, 0, 1, alpha])

        # check pygfx material
        npt.assert_almost_equal(
            graphic.world_object.material.color, np.asarray(graphic.colors)
        )
    else:
        assert isinstance(graphic._colors, VertexColors)
        assert isinstance(graphic.colors, VertexColors)
        if colors is None:
            # default white
            npt.assert_almost_equal(
                graphic.colors.value,
                np.repeat([[1, 1, 1, alpha]], repeats=len(graphic.data), axis=0),
            )
        else:
            # blue
            npt.assert_almost_equal(
                graphic.colors.value,
                np.repeat([[0, 0, 1, alpha]], repeats=len(graphic.data), axis=0),
            )

        # check geometry
        npt.assert_almost_equal(
            graphic.world_object.geometry.colors.data, graphic.colors.value
        )


@pytest.mark.parametrize("graphic_type", ["line", "scatter"])
@pytest.mark.parametrize(
    "data", [generate_positions_spiral_data(v) for v in ["y", "xy", "xyz"]]
)
def test_positions_graphics_data(
    graphic_type,
    data,
):
    # tests with different ways of passing positions data, x, xy and xyz
    fig = fpl.Figure()

    if graphic_type == "line":
        graphic = fig[0, 0].add_line(data=data)

    elif graphic_type == "scatter":
        graphic = fig[0, 0].add_scatter(data=data)

    assert isinstance(graphic._data, VertexPositions)
    assert isinstance(graphic.data, VertexPositions)

    # n_datapoints must match
    assert len(graphic.data.value) == len(data)

    # make sure data is correct
    match data.shape[-1]:
        case 1:  # only y-vals given
            npt.assert_almost_equal(graphic.data[:, 1], data)  # y vals must match
            npt.assert_almost_equal(
                graphic.data[:, 0], np.arange(data.size)
            )  # VertexData makes x-vals with arange
            npt.assert_almost_equal(graphic.data[:, -1], 0)  # z-vals must be zeros
        case 2:  # xy vals given
            npt.assert_almost_equal(graphic.data[:, :-1], data)  # x and y must match
            npt.assert_almost_equal(graphic.data[:, -1], 0)  # z-vals must be zero
        case 3:  # xyz vals given
            npt.assert_almost_equal(graphic.data[:], data[:])  # everything must match


@pytest.mark.parametrize("graphic_type", ["line", "scatter"])
@pytest.mark.parametrize("colors", [None, *generate_color_inputs("r")])
@pytest.mark.parametrize("uniform_color", [None, False])
@pytest.mark.parametrize("alpha", [None, 0.5, 0.0])
def test_positions_graphic_vertex_colors(
    graphic_type,
    colors,
    uniform_color,
    alpha,
):
    fig = fpl.Figure()

    kwargs = dict()
    for kwarg in ["colors", "uniform_color", "alpha"]:
        if locals()[kwarg] is not None:
            # add to dict of arguments that will be passed
            kwargs[kwarg] = locals()[kwarg]

    data = generate_positions_spiral_data("xy")

    if graphic_type == "line":
        graphic = fig[0, 0].add_line(data=data, **kwargs)
    elif graphic_type == "scatter":
        graphic = fig[0, 0].add_scatter(data=data, **kwargs)

    if alpha is None:  # default arg
        alpha = 1

    # color per vertex
    # uniform colors is default False, or set to False
    assert isinstance(graphic._colors, VertexColors)
    assert isinstance(graphic.colors, VertexColors)
    assert len(graphic.colors) == len(graphic.data)

    if colors is None:
        # default
        npt.assert_almost_equal(
            graphic.colors.value,
            np.repeat([[1, 1, 1, alpha]], repeats=len(graphic.data), axis=0),
        )
    else:
        if len(colors) != len(graphic.data):
            # should be single red, regardless of input variant (i.e. str, array, RGBA tuple, etc.
            npt.assert_almost_equal(
                graphic.colors.value,
                np.repeat([[1, 0, 0, alpha]], repeats=len(graphic.data), axis=0),
            )
        else:
            # multi colors
            # use the truth for multi colors test that is pre-set
            npt.assert_almost_equal(graphic.colors.value, MULTI_COLORS_TRUTH)


@pytest.mark.parametrize("graphic_type", ["line", "scatter"])
@pytest.mark.parametrize("colors", [None, *generate_color_inputs("r")])
@pytest.mark.parametrize("uniform_color", [None, False])
@pytest.mark.parametrize("cmap", ["jet"])
@pytest.mark.parametrize(
    "transform", [None, [3, 5, 2, 1, 0, 6, 9, 7, 4, 8], np.arange(9, -1, -1)]
)
@pytest.mark.parametrize("alpha", [None, 0.5, 0.0])
def test_cmap(
    graphic_type,
    colors,
    uniform_color,
    cmap,
    transform,
    alpha,
):
    fig = fpl.Figure()

    kwargs = dict()
    for kwarg in ["cmap", "transform", "colors", "uniform_color", "alpha"]:
        if locals()[kwarg] is not None:
            # add to dict of arguments that will be passed
            kwargs[kwarg] = locals()[kwarg]

    data = generate_positions_spiral_data("xy")

    if graphic_type == "line":
        graphic = fig[0, 0].add_line(data=data, **kwargs)
    elif graphic_type == "scatter":
        graphic = fig[0, 0].add_scatter(data=data, **kwargs)

    if alpha is None:
        alpha = 1.0

    truth = TRUTH_CMAPS[cmap].copy()
    truth[:, -1] = alpha

    # permute if transform is provided
    if transform is not None:
        truth = truth[transform]
        npt.assert_almost_equal(graphic.cmap.transform, transform)

    assert isinstance(graphic._cmap, VertexCmap)

    assert graphic.cmap.name == cmap

    # make sure buffer is identical
    # cmap overrides colors argument
    assert graphic.colors.buffer is graphic.cmap.buffer

    npt.assert_almost_equal(graphic.cmap.value, truth)
    npt.assert_almost_equal(graphic.colors.value, truth)

    # test changing cmap but not transform
    graphic.cmap = "viridis"
    truth = TRUTH_CMAPS["viridis"].copy()
    truth[:, -1] = alpha

    if transform is not None:
        truth = truth[transform]

    assert graphic.cmap.name == "viridis"
    npt.assert_almost_equal(graphic.cmap.value, truth)
    npt.assert_almost_equal(graphic.colors.value, truth)

    # test changing transform
    transform = np.random.rand(10)
    graphic.cmap.transform = transform
    npt.assert_almost_equal(graphic.cmap.transform, transform)

    truth = TRUTH_CMAPS["viridis"].copy()
    truth = truth[transform.argsort()]
    truth[:, -1] = alpha

    npt.assert_almost_equal(graphic.cmap.value, truth)
    npt.assert_almost_equal(graphic.colors.value, truth)


@pytest.mark.parametrize("graphic_type", ["line", "scatter"])
@pytest.mark.parametrize("cmap", ["jet"])
@pytest.mark.parametrize(
    "colors", [None, *generate_color_inputs("multi")]
)  # cmap arg overrides colors
@pytest.mark.parametrize(
    "uniform_color", [True]  # none of these will work with a uniform buffer
)
def test_incompatible_cmap_color_args(graphic_type, cmap, colors, uniform_color):
    fig = fpl.Figure()

    kwargs = dict()
    for kwarg in ["cmap", "colors", "uniform_color"]:
        if locals()[kwarg] is not None:
            # add to dict of arguments that will be passed
            kwargs[kwarg] = locals()[kwarg]

    data = generate_positions_spiral_data("xy")

    if graphic_type == "line":
        with pytest.raises(TypeError):
            graphic = fig[0, 0].add_line(data=data, **kwargs)
    elif graphic_type == "scatter":
        with pytest.raises(TypeError):
            graphic = fig[0, 0].add_scatter(data=data, **kwargs)


@pytest.mark.parametrize("graphic_type", ["line", "scatter"])
@pytest.mark.parametrize(
    "colors", [*generate_color_inputs("multi")]
)
@pytest.mark.parametrize(
    "uniform_color", [True]  # none of these will work with a uniform buffer
)
def test_incompatible_color_args(graphic_type, colors, uniform_color):
    fig = fpl.Figure()

    kwargs = dict()
    for kwarg in ["colors", "uniform_color"]:
        if locals()[kwarg] is not None:
            # add to dict of arguments that will be passed
            kwargs[kwarg] = locals()[kwarg]

    data = generate_positions_spiral_data("xy")

    if graphic_type == "line":
        with pytest.raises(TypeError):
            graphic = fig[0, 0].add_line(data=data, **kwargs)
    elif graphic_type == "scatter":
        with pytest.raises(TypeError):
            graphic = fig[0, 0].add_scatter(data=data, **kwargs)


@pytest.mark.parametrize(
    "sizes", [None, 5.0, np.linspace(3, 8, 10, dtype=np.float32)]
)
@pytest.mark.parametrize(
    "uniform_size", [None, False]
)
def test_sizes(sizes, uniform_size):
    fig = fpl.Figure()

    kwargs = dict()
    for kwarg in ["sizes"]:
        if locals()[kwarg] is not None:
            # add to dict of arguments that will be passed
            kwargs[kwarg] = locals()[kwarg]

    data = generate_positions_spiral_data("xy")

    graphic = fig[0, 0].add_scatter(data=data, **kwargs)

    assert isinstance(graphic.sizes, PointsSizesFeature)
    assert isinstance(graphic._sizes, PointsSizesFeature)
    assert len(data) == len(graphic.sizes)

    if sizes is None:
        sizes = 1  # default sizes

    npt.assert_almost_equal(graphic.sizes.value, sizes)
    npt.assert_almost_equal(graphic.world_object.geometry.sizes.data, graphic.sizes.value)


@pytest.mark.parametrize(
    "sizes", [None, 5.0]
)
@pytest.mark.parametrize(
    "uniform_size", [True]
)
def test_uniform_size(sizes, uniform_size):
    fig = fpl.Figure()

    kwargs = dict()
    for kwarg in ["sizes", "uniform_size"]:
        if locals()[kwarg] is not None:
            # add to dict of arguments that will be passed
            kwargs[kwarg] = locals()[kwarg]

    data = generate_positions_spiral_data("xy")

    graphic = fig[0, 0].add_scatter(data=data, **kwargs)

    assert isinstance(graphic.sizes, (float, int))
    assert isinstance(graphic._sizes, UniformSize)

    if sizes is None:
        sizes = 1  # default sizes

    npt.assert_almost_equal(graphic.sizes, sizes)
    npt.assert_almost_equal(graphic.world_object.material.size, sizes)


@pytest.mark.parametrize(
    "thickness", [None, 0.5, 5.0]
)
def test_thickness(thickness):
    fig = fpl.Figure()

    kwargs = dict()
    for kwarg in ["thickness"]:
        if locals()[kwarg] is not None:
            # add to dict of arguments that will be passed
            kwargs[kwarg] = locals()[kwarg]

    data = generate_positions_spiral_data("xy")

    graphic = fig[0, 0].add_line(data=data, **kwargs)

    if thickness is None:
        thickness = 2.0  # default thickness

    assert isinstance(graphic._thickness, Thickness)

    assert graphic.thickness == thickness
    assert graphic.world_object.material.thickness == thickness

    if thickness == 0.5:
        assert isinstance(graphic.world_object.material, pygfx.LineThinMaterial)

    else:
        assert isinstance(graphic.world_object.material, pygfx.LineMaterial)
