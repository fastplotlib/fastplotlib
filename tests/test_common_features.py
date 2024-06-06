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
                np.column_stack([np.random.rand(10), np.random.rand(10)]),
                **kwargs
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


@pytest.mark.parametrize("graphic", [make_graphic(k, name="init_name") for k in graphic_kinds])
def test_name_init(graphic):
    assert graphic.name == "init_name"

    graphic.name = "new_name"

    assert graphic.name == "new_name"


@pytest.mark.parametrize("graphic", [make_graphic(k) for k in graphic_kinds])
def test_offset(graphic):
    npt.assert_almost_equal(graphic.offset, (0., 0., 0.))
    npt.assert_almost_equal(graphic.world_object.world.position, (0., 0., 0.))

    graphic.add_event_handler(return_event, "offset")

    graphic.offset = (1., 2., 3.)

    npt.assert_almost_equal(graphic.offset, (1., 2., 3.))
    npt.assert_almost_equal(graphic.world_object.world.position, (1., 2., 3.))

    global RETURN_EVENT_VALUE

    assert RETURN_EVENT_VALUE.type == "offset"
    assert RETURN_EVENT_VALUE.graphic is graphic
    assert RETURN_EVENT_VALUE.target is graphic.world_object
    npt.assert_almost_equal(RETURN_EVENT_VALUE.info["value"], (1., 2., 3.))


@pytest.mark.parametrize("graphic", [make_graphic(k, offset=(3., 4., 5.)) for k in graphic_kinds])
def test_offset_init(graphic):
    npt.assert_almost_equal(graphic.offset, (3., 4., 5.))
    npt.assert_almost_equal(graphic.world_object.world.position, (3., 4., 5.))

    graphic.offset = (6., 7., 8.)

    npt.assert_almost_equal(graphic.offset, (6., 7., 8.))
    npt.assert_almost_equal(graphic.world_object.world.position, (6., 7., 8.))


@pytest.mark.parametrize("graphic", [make_graphic(k) for k in graphic_kinds])
def test_rotation(graphic):
    npt.assert_almost_equal(graphic.rotation, (0, 0, 0, 1))
    npt.assert_almost_equal(graphic.world_object.world.rotation, (0, 0, 0, 1))

    graphic.add_event_handler(return_event, "rotation")

    graphic.rotation = (0., 0., 0.30001427, 0.95393471)

    npt.assert_almost_equal(graphic.rotation, (0., 0., 0.30001427, 0.95393471))
    npt.assert_almost_equal(graphic.world_object.world.rotation, (0., 0., 0.30001427, 0.95393471))

    global RETURN_EVENT_VALUE

    assert RETURN_EVENT_VALUE.type == "rotation"
    assert RETURN_EVENT_VALUE.graphic is graphic
    assert RETURN_EVENT_VALUE.target is graphic.world_object
    npt.assert_almost_equal(RETURN_EVENT_VALUE.info["value"], (0., 0., 0.30001427, 0.95393471))


@pytest.mark.parametrize("graphic", [make_graphic(k, rotation=(0., 0., 0.30001427, 0.95393471)) for k in graphic_kinds])
def test_rotation(graphic):
    npt.assert_almost_equal(graphic.rotation, (0., 0., 0.30001427, 0.95393471))
    npt.assert_almost_equal(graphic.world_object.world.rotation, (0., 0., 0.30001427, 0.95393471))

    graphic.rotation = (0, 0.0, 0.6, 0.8)

    npt.assert_almost_equal(graphic.rotation, (0, 0.0, 0.6, 0.8))
    npt.assert_almost_equal(graphic.world_object.world.rotation, (0, 0.0, 0.6, 0.8))


@pytest.mark.parametrize("graphic", [make_graphic(k)for k in graphic_kinds])
def test_visible(graphic):
    assert graphic.visible is True
    assert graphic.world_object.visible is True

    graphic.add_event_handler(return_event, "rotation")

    graphic.visible = False
    assert graphic.visible is False
    assert graphic.world_object.visible is False

    assert RETURN_EVENT_VALUE.type == "visible"
    assert RETURN_EVENT_VALUE.graphic is graphic
    assert RETURN_EVENT_VALUE.target is graphic.world_object
    assert RETURN_EVENT_VALUE.info["value"] == False


@pytest.mark.parametrize("graphic", [make_graphic(k, visible=False) for k in graphic_kinds])
def test_visible(graphic):
    assert graphic.visible is False
    assert graphic.world_object.visible is False

    graphic.visible = True
    assert graphic.visible is True
    assert graphic.world_object.visible is True
