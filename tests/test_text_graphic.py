from numpy import testing as npt

import fastplotlib as fpl
from fastplotlib.graphics._features import (
    FeatureEvent,
    TextData,
    FontSize,
    TextFaceColor,
    TextOutlineColor,
    TextOutlineThickness,
)

import pygfx


def test_create_graphic():
    fig = fpl.Figure()
    data = "lorem ipsum"
    text = fig[0, 0].add_text(data)

    assert isinstance(text, fpl.TextGraphic)

    assert isinstance(text._text, TextData)
    assert text.text == data

    assert text.font_size == 14
    assert isinstance(text._font_size, FontSize)
    assert text.world_object.font_size == 14

    assert text.face_color == pygfx.Color("w")
    assert isinstance(text._face_color, TextFaceColor)
    assert text.world_object.material.color == pygfx.Color("w")

    assert text.outline_color == pygfx.Color("w")
    assert isinstance(text._outline_color, TextOutlineColor)
    assert text.world_object.material.outline_color == pygfx.Color("w")

    assert text.outline_thickness == 0
    assert isinstance(text._outline_thickness, TextOutlineThickness)
    assert text.world_object.material.outline_thickness == 0


EVENT_RETURN_VALUE: FeatureEvent = None


def event_handler(ev):
    global EVENT_RETURN_VALUE
    EVENT_RETURN_VALUE = ev


def check_event(graphic, feature, value):
    global EVENT_RETURN_VALUE
    assert isinstance(EVENT_RETURN_VALUE, FeatureEvent)
    assert EVENT_RETURN_VALUE.type == feature
    assert EVENT_RETURN_VALUE.graphic == graphic
    assert EVENT_RETURN_VALUE.target == graphic.world_object
    if isinstance(EVENT_RETURN_VALUE.info["value"], float):
        # floating point error
        npt.assert_almost_equal(EVENT_RETURN_VALUE.info["value"], value)
    else:
        assert EVENT_RETURN_VALUE.info["value"] == value


def test_text_changes_events():
    fig = fpl.Figure()
    data = "lorem ipsum"
    text = fig[0, 0].add_text(data)

    text.add_event_handler(
        event_handler,
        "text",
        "font_size",
        "face_color",
        "outline_color",
        "outline_thickness",
    )

    text.text = "bah"
    assert text.text == "bah"
    # TODO: seems like there isn't a way in pygfx to get the current text as a str?
    check_event(graphic=text, feature="text", value="bah")

    text.font_size = 10.0
    assert text.font_size == 10.0
    assert text.world_object.font_size == 10
    check_event(text, "font_size", 10)

    text.face_color = "r"
    assert text.face_color == pygfx.Color("r")
    assert text.world_object.material.color == pygfx.Color("r")
    check_event(text, "face_color", pygfx.Color("r"))

    text.outline_color = "b"
    assert text.outline_color == pygfx.Color("b")
    assert text.world_object.material.outline_color == pygfx.Color("b")
    check_event(text, "outline_color", pygfx.Color("b"))

    text.outline_thickness = 0.3
    npt.assert_almost_equal(text.outline_thickness, 0.3)
    npt.assert_almost_equal(text.world_object.material.outline_thickness, 0.3)
    check_event(text, "outline_thickness", 0.3)
