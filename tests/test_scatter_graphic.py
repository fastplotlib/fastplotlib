import numpy as np
from numpy import testing as npt
import pytest

import pygfx

import fastplotlib as fpl
from fastplotlib.graphics.features import (
    UniformMarker,
    VertexMarkers,
    VertexColors,
    UniformEdgeColor,
    EdgeWidth,
    TextureArray,
)

from fastplotlib.graphics.features._scatter import marker_names
from .utils import (
    generate_positions_spiral_data,
    generate_color_inputs,
    MULTI_COLORS_TRUTH,
)


@pytest.mark.parametrize("marker", list("osD+x^v<>*"))
def test_uniform_markers(marker):
    fig = fpl.Figure()

    data = generate_positions_spiral_data("xyz")

    scatter = fig[0, 0].add_scatter(data, markers=marker, uniform_marker=True)

    marker_full_name = marker_names.get(marker)

    assert isinstance(scatter.world_object.material, pygfx.PointsMarkerMaterial)
    assert scatter.world_object.material.marker_mode == pygfx.MarkerMode.uniform
    assert isinstance(scatter._markers, UniformMarker)

    assert scatter.markers == marker_full_name
    assert scatter.world_object.material.marker == marker_full_name


@pytest.mark.parametrize("to_type", [list, tuple, np.array])
@pytest.mark.parametrize("uniform_marker", [True, False])
def test_incompatible_marker_args(to_type, uniform_marker):
    markers = ["o"] * 3 + ["s"] * 3 + ["+"] * 3 + ["x"]

    markers = to_type(markers)

    data = generate_positions_spiral_data("xyz")

    fig = fpl.Figure()

    if uniform_marker:
        with pytest.raises(TypeError):
            scatter = fig[0, 0].add_scatter(data, markers=markers, uniform_marker=True)

    else:
        scatter = fig[0, 0].add_scatter(data, markers=markers, uniform_marker=False)
        assert isinstance(scatter._markers, VertexMarkers)
        assert scatter.world_object.material.marker_mode == pygfx.MarkerMode.vertex


def test_uniform_custom_sdf():
    lower_right_triangle_sdf = """
    // hardcode square root of 2
    let m_sqrt_2 = 1.4142135;

    // given a distance from an origin point, this defines the hypotenuse of a lower right triangle
    let distance = (-coord.x + coord.y) / m_sqrt_2;

    // return distance for this position
    return distance * size;
    """

    data = generate_positions_spiral_data("xyz")

    fig = fpl.Figure()

    scatter = fig[0, 0].add_scatter(
        data, markers="custom", uniform_marker=True, custom_sdf=lower_right_triangle_sdf
    )

    assert scatter.markers == "custom"
    assert scatter.world_object.material.marker == "custom"
    assert scatter.world_object.material.custom_sdf == lower_right_triangle_sdf

# test with both list[str] and 2D numpy array inputs as colors
@pytest.mark.parametrize("edge_colors",[generate_color_inputs("multi")[0], generate_color_inputs("multi")[1]])
def test_edge_colors(edge_colors):
    fig = fpl.Figure()

    data = generate_positions_spiral_data("xyz")

    scatter = fig[0, 0].add_scatter(
        data=data,
        edge_colors=edge_colors,
        uniform_edge_color=False,
    )

    assert isinstance(scatter._edge_colors, VertexColors)

    npt.assert_almost_equal(scatter.edge_colors.value, MULTI_COLORS_TRUTH)

    assert (
        scatter.edge_colors.buffer is scatter.world_object.geometry.edge_colors
    )


@pytest.mark.parametrize("edge_color", ["r", (1, 0, 0), [1, 0, 0], np.array([1, 0, 0])])
def test_uniform_edge_colors(edge_color):
    fig = fpl.Figure()

    data = generate_positions_spiral_data("xyz")

    scatter = fig[0, 0].add_scatter(
        data=data, edge_colors=edge_color, uniform_edge_color=True
    )

    assert isinstance(scatter._edge_colors, UniformEdgeColor)
    assert scatter.edge_colors == pygfx.Color(edge_color)
    assert scatter.world_object.material.edge_color == pygfx.Color(edge_color)


@pytest.mark.parametrize("edge_colors", [generate_color_inputs("multi")[0],generate_color_inputs("multi")[1]])
@pytest.mark.parametrize("uniform_edge_color", [False, True])
def test_incompatible_edge_colors_args(edge_colors, uniform_edge_color):
    fig = fpl.Figure()

    data = generate_positions_spiral_data("xyz")

    if uniform_edge_color:
        with pytest.raises(TypeError):
            scatter = fig[0, 0].add_scatter(
                data=data,
                edge_colors=edge_colors,
                uniform_edge_color=uniform_edge_color,
            )


@pytest.mark.parametrize("edge_width", [0.0, 0.5, 1.0, 5.0])
def test_edge_width(edge_width):
    fig = fpl.Figure()

    data = generate_positions_spiral_data("xyz")

    scatter = fig[0, 0].add_scatter(
        data=data,
        edge_width=edge_width,
    )

    assert isinstance(scatter._edge_width, EdgeWidth)
    assert scatter.world_object.material.edge_width == edge_width
    assert scatter.edge_width == edge_width


def test_sprite():
    image = np.array(
        [
            [1, 0, 1],
            [0, 1, 0],
            [1, 1, 1],
        ]
    )

    data = generate_positions_spiral_data("xyz")

    fig = fpl.Figure()

    scatter = fig[0, 0].add_scatter(
        data=data,
        mode="image",
        image=image,
    )

    # make sure the image is a fpl TextureArray
    assert isinstance(scatter.image, TextureArray)
    # make sure the sprite is the TextureArray buffer, i.e. a pygfx.Texture
    assert scatter.world_object.material.sprite is scatter.image.buffer[0, 0]
    assert scatter.image.buffer.size == 1

    npt.assert_almost_equal(scatter.image.value, image)
    npt.assert_almost_equal(scatter.image.buffer[0, 0].data, image)
