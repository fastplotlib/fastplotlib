import numpy as np
from numpy import testing as npt
import pytest

import fastplotlib as fpl
import pygfx
from fastplotlib.graphics.features import GraphicFeatureEvent, VertexRotations

from .utils import (
    generate_slice_indices,
    generate_positions_spiral_data,
)


EVENT_RETURN_VALUE: GraphicFeatureEvent = None


def event_handler(ev):
    global EVENT_RETURN_VALUE
    EVENT_RETURN_VALUE = ev


# some rotation angles
ROTATIONS1 = np.linspace(0, 2 * np.pi, 10)
ROTATIONS2 = np.linspace(np.pi / 2, (np.pi / 2) + (np.pi * 2), 10)


@pytest.mark.parametrize("test_graphic", [True, False])
def test_create_buffer(test_graphic):
    data = generate_positions_spiral_data("xyz")

    if test_graphic:
        fig = fpl.Figure()

        scatter = fig[0, 0].add_scatter(data, point_rotation_mode="vertex", point_rotations=ROTATIONS1)
        vertex_rotations = scatter.point_rotations
        assert isinstance(vertex_rotations, VertexRotations)
        assert vertex_rotations.buffer is scatter.world_object.geometry.rotations
    else:
        vertex_rotations = VertexRotations(ROTATIONS1, len(data))

    npt.assert_almost_equal(vertex_rotations.value, ROTATIONS1)


@pytest.mark.parametrize("test_graphic", [True, False])
@pytest.mark.parametrize("index", [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, -1, -2, -3, -4, -5, -6, -7, -8, -9, -10])
def test_int(test_graphic, index: int):
    data = generate_positions_spiral_data("xyz")

    if test_graphic:
        fig = fpl.Figure()

        scatter = fig[0, 0].add_scatter(data, point_rotation_mode="vertex", point_rotations=ROTATIONS1)
        vertex_rotations = scatter.point_rotations

        scatter.add_event_handler(event_handler, "point_rotations")
    else:
        vertex_rotations = VertexRotations(ROTATIONS1, len(data))

    # set marker at one point
    vertex_rotations[index] = ROTATIONS2[index]

    npt.assert_almost_equal(vertex_rotations[index], ROTATIONS2[index])

    # make sure other indices are unchanged
    indices = list(range(10))
    indices.pop(index)

    npt.assert_almost_equal(vertex_rotations[indices], ROTATIONS1[indices])

    if test_graphic:
        global EVENT_RETURN_VALUE
        assert EVENT_RETURN_VALUE.type == "point_rotations"
        assert isinstance(EVENT_RETURN_VALUE, GraphicFeatureEvent)
        assert EVENT_RETURN_VALUE.graphic is scatter
        assert EVENT_RETURN_VALUE.target is scatter.world_object
        assert EVENT_RETURN_VALUE.info["key"] == index
        assert EVENT_RETURN_VALUE.info["value"] == ROTATIONS2[index]


@pytest.mark.parametrize("test_graphic", [True, False])
@pytest.mark.parametrize(
    "slice_method", [generate_slice_indices(i) for i in range(1, 16)]
)
def test_slice(test_graphic, slice_method):
    data = generate_positions_spiral_data("xyz")

    if test_graphic:
        fig = fpl.Figure()

        scatter = fig[0, 0].add_scatter(data, point_rotation_mode="vertex", point_rotations=ROTATIONS1)
        vertex_rotations = scatter.point_rotations

        scatter.add_event_handler(event_handler, "point_rotations")
    else:
        vertex_rotations = VertexRotations(ROTATIONS1, len(data))

    s = slice_method["slice"]
    indices = slice_method["indices"]
    offset = slice_method["offset"]
    size = slice_method["size"]
    others = slice_method["others"]

    vertex_rotations[s] = ROTATIONS2[s]

    # test event
    if test_graphic:
        global EVENT_RETURN_VALUE
        assert isinstance(EVENT_RETURN_VALUE, GraphicFeatureEvent)
        assert EVENT_RETURN_VALUE.type == "point_rotations"
        assert EVENT_RETURN_VALUE.graphic is scatter
        assert EVENT_RETURN_VALUE.target is scatter.world_object
        if isinstance(s, slice):
            assert EVENT_RETURN_VALUE.info["key"] == s
            npt.assert_almost_equal(EVENT_RETURN_VALUE.info["value"], ROTATIONS2[s])

    npt.assert_almost_equal(vertex_rotations[s], ROTATIONS2[s])

    # make sure others aren't affected
    npt.assert_almost_equal(vertex_rotations[others], ROTATIONS1[others])
