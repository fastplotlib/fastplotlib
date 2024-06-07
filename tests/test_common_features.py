import numpy
import numpy as np
from numpy import testing as npt
import pytest

import fastplotlib as fpl
from fastplotlib.graphics._features import FeatureEvent, Name, Offset, Rotation, Visible


def make_graphic(kind: str, **kwargs):
    match kind:
        case "image":
            return fpl.ImageGraphic(np.random.rand(10, 10), **kwargs)
        case "line":
            return fpl.LineGraphic(np.random.rand(10), **kwargs)
        case "scatter":
            return fpl.ScatterGraphic(
                np.column_stack([np.random.rand(10), np.random.rand(10)]), **kwargs
            )
        case "text":
            return fpl.TextGraphic("bah", **kwargs)


graphic_kinds = [
    "image",
    "line",
    "scatter",
    "text",
]


RETURN_EVENT_VALUE: FeatureEvent = None
DECORATED_EVENT_VALUE: FeatureEvent = None


def return_event(ev: FeatureEvent):
    global RETURN_EVENT_VALUE
    RETURN_EVENT_VALUE = ev


@pytest.mark.parametrize("graphic", [make_graphic(k) for k in graphic_kinds])
def test_name(graphic):
    assert graphic.name is None

    graphic.add_event_handler(return_event, "name")

    graphic.name = "new_name"

    assert graphic.name == "new_name"

    global RETURN_EVENT_VALUE

    assert RETURN_EVENT_VALUE.type == "name"
    assert RETURN_EVENT_VALUE.graphic is graphic
    assert RETURN_EVENT_VALUE.target is graphic.world_object
    assert RETURN_EVENT_VALUE.info["value"] == "new_name"

    # check removing event handler
    RETURN_EVENT_VALUE = None
    graphic.remove_event_handler(return_event, "name")
    assert len(graphic._event_handlers["name"]) == 0

    graphic.name = "new_name2"

    assert RETURN_EVENT_VALUE is None
    assert graphic.name == "new_name2"

    # check adding event with decorator
    global DECORATED_EVENT_VALUE
    DECORATED_EVENT_VALUE = None

    @graphic.add_event_handler("name")
    def decorated_handler(ev):
        global DECORATED_EVENT_VALUE
        DECORATED_EVENT_VALUE = ev

    graphic.name = "test_dec"
    assert graphic.name == "test_dec"

    assert DECORATED_EVENT_VALUE.type == "name"
    assert DECORATED_EVENT_VALUE.graphic is graphic
    assert DECORATED_EVENT_VALUE.target is graphic.world_object
    assert DECORATED_EVENT_VALUE.info["value"] == "test_dec"


@pytest.mark.parametrize(
    "graphic", [make_graphic(k, name="init_name") for k in graphic_kinds]
)
def test_name_init(graphic):
    assert graphic.name == "init_name"

    graphic.name = "new_name"

    assert graphic.name == "new_name"


@pytest.mark.parametrize("graphic", [make_graphic(k) for k in graphic_kinds])
def test_offset(graphic):
    npt.assert_almost_equal(graphic.offset, (0.0, 0.0, 0.0))
    npt.assert_almost_equal(graphic.world_object.world.position, (0.0, 0.0, 0.0))

    graphic.add_event_handler(return_event, "offset")

    graphic.offset = (1.0, 2.0, 3.0)

    npt.assert_almost_equal(graphic.offset, (1.0, 2.0, 3.0))
    npt.assert_almost_equal(graphic.world_object.world.position, (1.0, 2.0, 3.0))

    global RETURN_EVENT_VALUE

    assert RETURN_EVENT_VALUE.type == "offset"
    assert RETURN_EVENT_VALUE.graphic is graphic
    assert RETURN_EVENT_VALUE.target is graphic.world_object
    npt.assert_almost_equal(RETURN_EVENT_VALUE.info["value"], (1.0, 2.0, 3.0))

    # check removing event handler
    RETURN_EVENT_VALUE = None
    graphic.remove_event_handler(return_event, "offset")
    assert len(graphic._event_handlers["offset"]) == 0

    graphic.offset = (4, 5, 6)

    assert RETURN_EVENT_VALUE is None
    npt.assert_almost_equal(graphic.offset, (4.0, 5.0, 6.0))

    # check adding event with decorator
    global DECORATED_EVENT_VALUE
    DECORATED_EVENT_VALUE = None

    @graphic.add_event_handler("offset")
    def decorated_handler(ev):
        global DECORATED_EVENT_VALUE
        DECORATED_EVENT_VALUE = ev

    graphic.offset = (7, 8, 9)
    npt.assert_almost_equal(graphic.offset, (7.0, 8.0, 9.0))

    assert DECORATED_EVENT_VALUE.type == "offset"
    assert DECORATED_EVENT_VALUE.graphic is graphic
    assert DECORATED_EVENT_VALUE.target is graphic.world_object
    assert DECORATED_EVENT_VALUE.info["value"] == (7.0, 8.0, 9.0)


@pytest.mark.parametrize(
    "graphic", [make_graphic(k, offset=(3.0, 4.0, 5.0)) for k in graphic_kinds]
)
def test_offset_init(graphic):
    npt.assert_almost_equal(graphic.offset, (3.0, 4.0, 5.0))
    npt.assert_almost_equal(graphic.world_object.world.position, (3.0, 4.0, 5.0))

    graphic.offset = (6.0, 7.0, 8.0)

    npt.assert_almost_equal(graphic.offset, (6.0, 7.0, 8.0))
    npt.assert_almost_equal(graphic.world_object.world.position, (6.0, 7.0, 8.0))


@pytest.mark.parametrize("graphic", [make_graphic(k) for k in graphic_kinds])
def test_rotation(graphic):
    npt.assert_almost_equal(graphic.rotation, (0, 0, 0, 1))
    npt.assert_almost_equal(graphic.world_object.world.rotation, (0, 0, 0, 1))

    graphic.add_event_handler(return_event, "rotation")

    graphic.rotation = (0.0, 0.0, 0.30001427, 0.95393471)

    npt.assert_almost_equal(graphic.rotation, (0.0, 0.0, 0.30001427, 0.95393471))
    npt.assert_almost_equal(
        graphic.world_object.world.rotation, (0.0, 0.0, 0.30001427, 0.95393471)
    )

    global RETURN_EVENT_VALUE

    assert RETURN_EVENT_VALUE.type == "rotation"
    assert RETURN_EVENT_VALUE.graphic is graphic
    assert RETURN_EVENT_VALUE.target is graphic.world_object
    npt.assert_almost_equal(
        RETURN_EVENT_VALUE.info["value"], (0.0, 0.0, 0.30001427, 0.95393471)
    )

    # check removing event handler
    RETURN_EVENT_VALUE = None
    graphic.remove_event_handler(return_event, "rotation")
    assert len(graphic._event_handlers["rotation"]) == 0

    graphic.rotation = (0, 0, 0, 1)

    assert RETURN_EVENT_VALUE is None
    npt.assert_almost_equal(graphic.rotation, (0, 0, 0, 1))

    # check adding event with decorator
    global DECORATED_EVENT_VALUE
    DECORATED_EVENT_VALUE = None

    @graphic.add_event_handler("rotation")
    def decorated_handler(ev):
        global DECORATED_EVENT_VALUE
        DECORATED_EVENT_VALUE = ev

    graphic.rotation = (0, 0, 0.6, 0.8)
    npt.assert_almost_equal(graphic.rotation, (0, 0, 0.6, 0.8))

    assert DECORATED_EVENT_VALUE.type == "rotation"
    assert DECORATED_EVENT_VALUE.graphic is graphic
    assert DECORATED_EVENT_VALUE.target is graphic.world_object
    assert DECORATED_EVENT_VALUE.info["value"] == (0, 0, 0.6, 0.8)


@pytest.mark.parametrize(
    "graphic",
    [
        make_graphic(k, rotation=(0.0, 0.0, 0.30001427, 0.95393471))
        for k in graphic_kinds
    ],
)
def test_rotation(graphic):
    npt.assert_almost_equal(graphic.rotation, (0.0, 0.0, 0.30001427, 0.95393471))
    npt.assert_almost_equal(
        graphic.world_object.world.rotation, (0.0, 0.0, 0.30001427, 0.95393471)
    )

    graphic.rotation = (0, 0.0, 0.6, 0.8)

    npt.assert_almost_equal(graphic.rotation, (0, 0.0, 0.6, 0.8))
    npt.assert_almost_equal(graphic.world_object.world.rotation, (0, 0.0, 0.6, 0.8))


@pytest.mark.parametrize("graphic", [make_graphic(k) for k in graphic_kinds])
def test_visible(graphic):
    assert graphic.visible is True
    assert graphic.world_object.visible is True

    graphic.add_event_handler(return_event, "rotation")

    graphic.visible = False
    assert graphic.visible is False
    assert graphic.world_object.visible is False

    global RETURN_EVENT_VALUE

    assert RETURN_EVENT_VALUE.type == "visible"
    assert RETURN_EVENT_VALUE.graphic is graphic
    assert RETURN_EVENT_VALUE.target is graphic.world_object
    assert RETURN_EVENT_VALUE.info["value"] is False

    # check removing event handler
    RETURN_EVENT_VALUE = None
    graphic.remove_event_handler(return_event, "visible")
    assert len(graphic._event_handlers["visible"]) == 0

    graphic.visible = True

    assert RETURN_EVENT_VALUE is None
    assert graphic.visible is True

    # check adding event with decorator
    global DECORATED_EVENT_VALUE
    DECORATED_EVENT_VALUE = None

    @graphic.add_event_handler("visible")
    def decorated_handler(ev):
        global DECORATED_EVENT_VALUE
        DECORATED_EVENT_VALUE = ev

    graphic.visible = False
    assert graphic.visible is False

    assert DECORATED_EVENT_VALUE.type == "visible"
    assert DECORATED_EVENT_VALUE.graphic is graphic
    assert DECORATED_EVENT_VALUE.target is graphic.world_object
    assert DECORATED_EVENT_VALUE.info["value"] is False


@pytest.mark.parametrize(
    "graphic", [make_graphic(k, visible=False) for k in graphic_kinds]
)
def test_visible(graphic):
    assert graphic.visible is False
    assert graphic.world_object.visible is False

    graphic.visible = True
    assert graphic.visible is True
    assert graphic.world_object.visible is True
