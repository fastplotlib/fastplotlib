import numpy as np
from numpy import testing as npt
import pytest

import pygfx
import cmap as cmap_lib

import fastplotlib as fpl
from fastplotlib.graphics.features import (
    VertexPositions,
    VertexColors,
    VertexCmap,
    VertexCmapTransform,
    VertexCmapRange,
    UniformColor,
    UniformSize,
    VertexPointSizes,
    Thickness,
    GraphicFeatureEvent,
)

from .utils import (
    generate_positions_spiral_data,
    generate_color_inputs,
    MULTI_COLORS_TRUTH,
)

EVENT_RETURN_VALUE: GraphicFeatureEvent = None


def event_handler(ev):
    global EVENT_RETURN_VALUE
    EVENT_RETURN_VALUE = ev


def test_sizes_slice():
    pass


@pytest.mark.parametrize("graphic_type", ["line", "scatter"])
@pytest.mark.parametrize("colors", ["w", *generate_color_inputs("b")])
def test_uniform_colors(graphic_type, colors):
    fig = fpl.Figure()

    data = generate_positions_spiral_data("xy")

    if graphic_type == "line":
        graphic = fig[0, 0].add_line(data=data, colors=colors)
    elif graphic_type == "scatter":
        graphic = fig[0, 0].add_scatter(data=data, colors=colors)

    assert isinstance(graphic._colors, UniformColor)
    assert isinstance(graphic.colors, pygfx.Color)
    assert graphic.world_object.material.color_mode == pygfx.ColorMode.uniform

    if isinstance(colors, str) and colors == "w":
        # default white
        assert graphic.colors == pygfx.Color([1, 1, 1])
    else:
        # should be blue
        assert graphic.colors == pygfx.Color([0, 0, 1])

    # check pygfx material
    npt.assert_almost_equal(
        graphic.world_object.material.color, np.asarray(graphic.colors)
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
@pytest.mark.parametrize("colors", [*generate_color_inputs("multi")])
def test_positions_graphic_vertex_colors(
    graphic_type,
    colors,
):
    # test different ways of passing vertex colors
    fig = fpl.Figure()

    data = generate_positions_spiral_data("xy")

    if graphic_type == "line":
        graphic = fig[0, 0].add_line(data=data, colors=colors)
    elif graphic_type == "scatter":
        graphic = fig[0, 0].add_scatter(data=data, colors=colors)

    # color per vertex
    assert isinstance(graphic._colors, VertexColors)
    assert isinstance(graphic.colors, VertexColors)
    assert len(graphic.colors) == len(graphic.data)
    assert graphic.world_object.material.color_mode == pygfx.ColorMode.vertex
    assert graphic.world_object.geometry.colors is graphic.colors._fpl_buffer

    # multi colors
    # use the truth for multi colors test that is pre-set
    npt.assert_almost_equal(graphic.colors.value, MULTI_COLORS_TRUTH)


@pytest.mark.parametrize("graphic_type", ["line", "scatter"])
@pytest.mark.parametrize("cmap", ["jet", cmap_lib.Colormap(["orange", "purple", "green"])])
@pytest.mark.parametrize(
    "cmap_transform", [None, [3, 5, 2, 1, 0, 6, 9, 7, 4, 8], np.arange(9, -1, -1)]
)
def test_cmap(
    graphic_type,
    cmap,
    cmap_transform,
):
    # test different ways of passing cmap args
    fig = fpl.Figure()

    data = generate_positions_spiral_data("xy")

    if graphic_type == "line":
        graphic = fig[0, 0].add_line(data=data, cmap=cmap, cmap_transform=cmap_transform)
    elif graphic_type == "scatter":
        graphic = fig[0, 0].add_scatter(data=data, cmap=cmap, cmap_transform=cmap_transform)

    # verify types
    assert isinstance(graphic._cmap, VertexCmap)
    assert isinstance(graphic.cmap, cmap_lib.Colormap)
    assert isinstance(graphic._cmap_transform, VertexCmapTransform)
    assert isinstance(graphic._cmap_range, VertexCmapRange)
    assert graphic.world_object.material.color_mode == pygfx.ColorMode.vertex_map

    assert isinstance(graphic.world_object.material.map, pygfx.TextureMap)
    assert isinstance(graphic.world_object.geometry.texcoords, pygfx.Buffer)

    if cmap_transform is None:
        transform = np.linspace(0, 1, len(data))
        npt.assert_almost_equal(
            graphic.cmap_transform, transform
        )
        npt.assert_almost_equal(
            graphic.world_object.geometry.texcoords.data, transform
        )
    else:
        npt.assert_almost_equal(graphic.cmap_range, [min(cmap_transform), max(cmap_transform)])
        npt.assert_almost_equal(
            graphic.world_object.geometry.texcoords.data, np.asarray(cmap_transform)
        )

    # verify buffer values
    npt.assert_almost_equal(graphic.world_object.material.map.texture.data, cmap_lib.Colormap(cmap).to_pygfx().texture.data)

    # test changing cmap but not transform
    graphic.cmap = "viridis"

    assert graphic.cmap.name == "bids:viridis"
    npt.assert_almost_equal(graphic.world_object.material.map.texture.data, cmap_lib.Colormap("viridis").to_pygfx().texture.data)

    # test changing transform
    cmap_transform = np.random.rand(10)

    graphic.cmap_transform = cmap_transform

    npt.assert_almost_equal(graphic.cmap_transform, cmap_transform)
    npt.assert_almost_equal(graphic.world_object.geometry.texcoords.data, cmap_transform)


@pytest.mark.parametrize("sizes", [2, 5.0, np.linspace(3, 8, 10, dtype=np.float32)])
def test_sizes(sizes):
    # test scatter sizes
    fig = fpl.Figure()

    data = generate_positions_spiral_data("xy")

    graphic = fig[0, 0].add_scatter(data=data, sizes=sizes)

    if isinstance(sizes, np.ndarray):
        assert isinstance(graphic.sizes, VertexPointSizes)
        assert isinstance(graphic._sizes, VertexPointSizes)
        assert len(data) == len(graphic.sizes)
        assert graphic.world_object.material.size_mode == pygfx.SizeMode.vertex

        npt.assert_almost_equal(graphic.sizes.value, sizes)
        npt.assert_almost_equal(
            graphic.world_object.geometry.sizes.data, graphic.sizes.value
        )
    else:
        assert isinstance(graphic.sizes, float)
        assert isinstance(graphic._sizes, UniformSize)
        assert graphic.world_object.material.size_mode == pygfx.SizeMode.uniform

        assert graphic.sizes == graphic._sizes.value == sizes

    # change sizes
    new_sizes = 10
    graphic.sizes = new_sizes
    if isinstance(sizes, np.ndarray):
        # broadcast
        assert (graphic.sizes.value == new_sizes).all()
    else:
        assert graphic.sizes == new_sizes

    # also test uniform -> vertex switch
    new_sizes = np.abs(np.sin(np.linspace(0, 2 * np.pi, len(data))))
    graphic.sizes = new_sizes

    assert isinstance(graphic.sizes, VertexPointSizes)
    assert graphic.world_object.material.size_mode == pygfx.SizeMode.vertex
    assert graphic.world_object.geometry.sizes is graphic.sizes._fpl_buffer


@pytest.mark.parametrize("thickness", [None, 0.5, 5.0])
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

    # the thin line material is selected via the `thin` flag, not the thickness value
    assert not graphic.thin
    assert isinstance(graphic.world_object.material, pygfx.LineMaterial)
    assert not isinstance(graphic.world_object.material, pygfx.LineThinMaterial)


@pytest.mark.parametrize(
    "pattern,expected",
    [
        ("--", (5, 5)),
        ("dashed", (5, 5)),
        (":", (0, 2)),
        ("-.", (5, 2, 1, 2)),
        ((2, 3), (2, 3)),
    ],
)
def test_dash_pattern(pattern, expected):
    fig = fpl.Figure()
    data = generate_positions_spiral_data("xy")

    graphic = fig[0, 0].add_line(data=data, dash_pattern=pattern)

    # value returns the user input verbatim, the material receives the parsed tuple
    assert graphic.dash_pattern == pattern
    assert tuple(graphic.world_object.material.dash_pattern) == expected

    # can be changed after creation
    graphic.dash_pattern = "solid"
    assert tuple(graphic.world_object.material.dash_pattern) == ()


def test_thin():
    fig = fpl.Figure()
    data = generate_positions_spiral_data("xy")

    # non-thin by default
    graphic = fig[0, 0].add_line(data=data, thickness=5.0)
    assert graphic.thin is False
    assert not isinstance(graphic.world_object.material, pygfx.LineThinMaterial)

    # the material is swapped when toggling `thin` after creation, keeping the geometry
    geometry = graphic.world_object.geometry
    graphic.thin = True
    assert graphic.thin is True
    assert isinstance(graphic.world_object.material, pygfx.LineThinMaterial)
    assert graphic.world_object.geometry is geometry

    graphic.thin = False
    assert not isinstance(graphic.world_object.material, pygfx.LineThinMaterial)
    assert isinstance(graphic.world_object.material, pygfx.LineMaterial)

    # can also be set at construction
    thin_graphic = fig[0, 0].add_line(data=data, thin=True)
    assert isinstance(thin_graphic.world_object.material, pygfx.LineThinMaterial)


def test_thin_ignores_dash_pattern_warns():
    fig = fpl.Figure()
    data = generate_positions_spiral_data("xy")

    # constructing a thin line with a dash pattern warns that dashing is ignored
    with pytest.warns(UserWarning, match="dash_pattern.*ignored"):
        fig[0, 0].add_line(data=data, thin=True, dash_pattern="--")

    # setting the dash pattern on a thin line also warns
    graphic = fig[0, 0].add_line(data=data, thin=True)
    with pytest.warns(UserWarning, match="dash_pattern.*ignored"):
        graphic.dash_pattern = "--"


@pytest.mark.parametrize("graphic_type", ["line", "scatter"])
@pytest.mark.parametrize("size_space", ["screen", "world", "model"])
def test_size_space(graphic_type, size_space):
    fig = fpl.Figure()

    kwargs = dict()
    for kwarg in ["size_space"]:
        if locals()[kwarg] is not None:
            # add to dict of arguments that will be passed
            kwargs[kwarg] = locals()[kwarg]

    data = generate_positions_spiral_data("xy")

    if size_space is None:
        size_space = "screen"  # default space

    # size_space is really an alias for pygfx.utils.enums.CoordSpace
    if graphic_type == "line":
        graphic = fig[0, 0].add_line(data=data, **kwargs)

        # test getter
        assert graphic.world_object.material.thickness_space == size_space
        assert graphic.size_space == size_space

        # test setter
        graphic.size_space = "world"
        assert graphic.size_space == "world"
        assert graphic.world_object.material.thickness_space == "world"

    elif graphic_type == "scatter":

        # test getter
        graphic = fig[0, 0].add_scatter(data=data, **kwargs)
        assert graphic.world_object.material.size_space == size_space
        assert graphic.size_space == size_space

        # test setter
        graphic.size_space = "world"
        assert graphic.size_space == "world"
        assert graphic.world_object.material.size_space == "world"
