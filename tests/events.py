from functools import partial
import pytest
import numpy as np
from numpy import testing as npt
import pygfx

import fastplotlib as fpl
from fastplotlib.graphics._features import FeatureEvent


def make_positions_data() -> np.ndarray:
    xs = np.linspace(0, 10 * np.pi, 10)
    ys = np.sin(xs)
    return np.column_stack([xs, ys])


def make_line_graphic() -> fpl.LineGraphic:
    return fpl.LineGraphic(make_positions_data())


def make_scatter_graphic() -> fpl.ScatterGraphic:
    return fpl.ScatterGraphic(make_positions_data())


event_instance: FeatureEvent = None


def event_handler(event):
    global event_instance
    event_instance = event


decorated_event_instance: FeatureEvent = None


@pytest.mark.parametrize("graphic", [make_line_graphic(), make_scatter_graphic()])
def test_positions_data_event(graphic: fpl.LineGraphic | fpl.ScatterGraphic):
    global decorated_event_instance
    global event_instance

    value = np.cos(np.linspace(0, 10 * np.pi, 10))[3:8]

    info = {"key": (slice(3, 8, None), 1), "value": value}

    expected = FeatureEvent(type="data", info=info)

    def validate(graphic, handler, expected_feature_event, event_to_test):
        assert expected_feature_event.type == event_to_test.type
        assert expected_feature_event.info["key"] == event_to_test.info["key"]

        npt.assert_almost_equal(
            expected_feature_event.info["value"], event_to_test.info["value"]
        )

        # should only have one event handler
        assert graphic._event_handlers["data"] == {handler}

        # make sure wrappers are correct
        wrapper_map = tuple(graphic._event_handler_wrappers["data"])[0]
        assert wrapper_map[0] is handler
        assert isinstance(wrapper_map[1], partial)
        assert wrapper_map[1].func == graphic._handle_event
        assert wrapper_map[1].args[0] is handler

        # test remove handler
        graphic.remove_event_handler(handler, "data")
        assert len(graphic._event_handlers["click"]) == 0
        assert len(graphic._event_handler_wrappers["click"]) == 0
        assert len(graphic.world_object._event_handlers["click"]) == 0

        # reset data
        graphic.data[:, :-1] = make_positions_data()
        event_to_test = None

    # test decorated function
    @graphic.add_event_handler("data")
    def decorated_handler(event):
        global decorated_event_instance
        decorated_event_instance = event

    # test decorated
    graphic.data[3:8, 1] = value
    validate(graphic, decorated_handler, expected, decorated_event_instance)

    # test regular
    graphic.add_event_handler(event_handler, "data")
    graphic.data[3:8, 1] = value

    validate(graphic, event_handler, expected, event_instance)

    event_instance = None
