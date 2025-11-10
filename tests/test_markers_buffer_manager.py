import numpy as np
from numpy import testing as npt
import pytest

import fastplotlib as fpl
import pygfx
from fastplotlib.graphics.features import GraphicFeatureEvent, VertexMarkers
from fastplotlib.graphics.features._scatter import marker_names, vectorized_user_markers_to_std_markers

from .utils import (
    generate_slice_indices,
    generate_positions_spiral_data,
)


EVENT_RETURN_VALUE: GraphicFeatureEvent = None


def event_handler(ev):
    global EVENT_RETURN_VALUE
    EVENT_RETURN_VALUE = ev


MARKERS1 = list("osD+x^v<>*")
MARKERS2 = list(">+vx<so^*D")

marker_values_int = list()
for m in MARKERS1:
    m = marker_names[m]
    marker_values_int.append(pygfx.MarkerInt[m])

MARKERS1_INT = np.asarray(marker_values_int)

marker_values_int = list()
for m in MARKERS2:
    m = marker_names[m]
    marker_values_int.append(pygfx.MarkerInt[m])

MARKERS2_INT = np.asarray(marker_values_int)


@pytest.mark.parametrize("test_graphic", [True, False])
def test_create_buffer(test_graphic):
    data = generate_positions_spiral_data("xyz")

    if test_graphic:
        fig = fpl.Figure()

        scatter = fig[0, 0].add_scatter(data, markers=MARKERS1)
        vertex_markers = scatter.markers
        assert isinstance(vertex_markers, VertexMarkers)
        assert vertex_markers.buffer is scatter.world_object.geometry.markers
    else:
        vertex_markers = VertexMarkers(MARKERS1, len(data))

    marker_values_str = np.asarray(list(map(marker_names.get, MARKERS1)))

    assert (vertex_markers.value == marker_values_str).all()
    npt.assert_equal(vertex_markers.value_int, MARKERS1_INT)
    assert (vertex_markers.buffer.data is vertex_markers.value_int)


@pytest.mark.parametrize("test_graphic", [True, False])
@pytest.mark.parametrize("index", [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, -1, -2, -3, -4, -5, -6, -7, -8, -9, -10])
def test_int(test_graphic, index: int):
    data = generate_positions_spiral_data("xyz")

    if test_graphic:
        fig = fpl.Figure()

        scatter = fig[0, 0].add_scatter(data, markers=MARKERS1)
        scatter.add_event_handler(event_handler, "markers")
        vertex_markers = scatter.markers
    else:
        vertex_markers = VertexMarkers(MARKERS1, len(data))

    # set a marker at one spot
    vertex_markers[index] = MARKERS2[index]

    assert vertex_markers.value[index] == marker_names[MARKERS2[index]]
    assert vertex_markers.value_int[index] == MARKERS2_INT[index]

    # make sure all others are unchanged
    indices = list(range(10))
    indices.pop(index)

    # these are int32 so assert equal should be fine
    npt.assert_equal(vertex_markers[indices], MARKERS1_INT[indices])
    npt.assert_equal(vertex_markers.value_int[indices], MARKERS1_INT[indices])

    if test_graphic:
        global EVENT_RETURN_VALUE
        assert EVENT_RETURN_VALUE.type == "markers"
        assert isinstance(EVENT_RETURN_VALUE, GraphicFeatureEvent)
        assert EVENT_RETURN_VALUE.graphic is scatter
        assert EVENT_RETURN_VALUE.target is scatter.world_object
        assert EVENT_RETURN_VALUE.info["key"] == index
        assert EVENT_RETURN_VALUE.info["value"] == MARKERS2[index]


@pytest.mark.parametrize("test_graphic", [True, False])
@pytest.mark.parametrize(
    "slice_method", [generate_slice_indices(i) for i in range(1, 16)]
)
def test_slice(test_graphic, slice_method):
    data = generate_positions_spiral_data("xyz")

    if test_graphic:
        fig = fpl.Figure()

        scatter = fig[0, 0].add_scatter(data, markers=MARKERS1)
        scatter.add_event_handler(event_handler, "markers")
        vertex_markers = scatter.markers

    else:
        vertex_markers = VertexMarkers(MARKERS1, len(data))

    s = slice_method["slice"]
    indices = slice_method["indices"]
    offset = slice_method["offset"]
    size = slice_method["size"]
    others = slice_method["others"]

    vertex_markers[s] = np.asarray(MARKERS2)[s]

    # test event too
    if test_graphic:
        global EVENT_RETURN_VALUE
        assert isinstance(EVENT_RETURN_VALUE, GraphicFeatureEvent)
        assert EVENT_RETURN_VALUE.type == "markers"
        assert EVENT_RETURN_VALUE.graphic is scatter
        assert EVENT_RETURN_VALUE.target is scatter.world_object
        if isinstance(s, slice):
            assert EVENT_RETURN_VALUE.info["key"] == s
            assert (EVENT_RETURN_VALUE.info["value"] == np.asarray(MARKERS2)[s]).all()

    assert (vertex_markers.value[s] == vectorized_user_markers_to_std_markers(MARKERS2)[s]).all()
    # these are int32 so assert equal should be fine
    npt.assert_equal(vertex_markers.value_int[s], MARKERS2_INT[s])

    # make sure other points aren't affected
    assert (vertex_markers.value[others] == vectorized_user_markers_to_std_markers(np.asarray(MARKERS1)[others])).all()
    npt.assert_equal(vertex_markers.value_int[others], MARKERS1_INT[others])
