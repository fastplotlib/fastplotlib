import numpy as np
import pytest

import fastplotlib as fpl
from fastplotlib.utils import global_config

RANGES = {"time": (0.0, 10.0, 1.0)}
DATA = np.random.rand(10, 16, 16).astype(np.float32)


def make_ndwidget(**kwargs):
    ndw = fpl.NDWidget(ranges=RANGES, size=(300, 400), **kwargs)
    ndw[0, 0].add_nd_image(
        DATA, ("time", "row", "col"), ("row", "col"), compute_histogram=False
    )
    return ndw


def draw(ndw):
    ndw.figure._render()
    ndw.figure.canvas.draw()


def test_defaults():
    ndw = make_ndwidget()
    ui = ndw.ui_sliders

    assert ui.title == "NDWidget controls"
    assert ui.playback
    assert ui.visible
    assert ndw.figure.imgui_windows["bottom"] is ui
    assert ndw.figure._edge_size("bottom") == ui.size > 0


def test_sliders_only_size():
    # the window shrinks when the title bar and the playback row are dropped at runtime
    ndw = make_ndwidget()
    ndw.show()
    for _ in range(2):
        draw(ndw)
    full = ndw.ui_sliders.size

    ndw.ui_sliders.title = None
    ndw.ui_sliders.playback = False
    for _ in range(2):
        draw(ndw)
    assert ndw.ui_sliders.size < full


def test_playback_off_stops_playing():
    ndw = make_ndwidget()
    ui = ndw.ui_sliders
    ui._playing["time"] = True

    ui.playback = False
    assert not ui._playing["time"]


def test_hidden_reserves_no_space():
    ndw = make_ndwidget()
    ndw.show()
    draw(ndw)
    subplot = ndw[0, 0].subplot
    _, _, _, height_with_ui = subplot.viewport.rect
    ui_size = ndw.ui_sliders.size

    # the subplot takes the space of the hidden window
    ndw.ui_sliders.visible = False
    draw(ndw)
    assert ndw.figure._edge_size("bottom") == 0
    _, _, _, height_without_ui = subplot.viewport.rect
    assert height_without_ui - height_with_ui == pytest.approx(ui_size, abs=1)

    ndw.ui_sliders.visible = True
    draw(ndw)
    assert ndw.figure._edge_size("bottom") == ndw.ui_sliders.size
    assert subplot.viewport.rect[3] == pytest.approx(height_with_ui, abs=1)


def test_ui_kwargs():
    ndw = make_ndwidget(ui_kwargs={"title": None, "playback": False})
    ui = ndw.ui_sliders

    assert ui.title is None
    assert not ui.playback
    assert ui.visible

    # shorter than the full window, before and after the first draw sets the height
    full = make_ndwidget()
    assert ui.size < full.ui_sliders.size

    ndw.show()
    full.show()
    for _ in range(2):
        draw(ndw)
        draw(full)
    assert ui.size < full.ui_sliders.size


def test_global_config():
    global_config.update(fpl.NDWidget.config.init, ui_kwargs={"playback": False})
    try:
        assert not make_ndwidget().ui_sliders.playback

        # an explicit argument wins over the config
        assert make_ndwidget(ui_kwargs={"playback": True}).ui_sliders.playback
    finally:
        fpl.NDWidget.config.init.ui_kwargs = None

    assert make_ndwidget().ui_sliders.playback


def test_size_follows_options_before_draw():
    # the reserved height follows the options as they change, without waiting for a draw, so a
    # single frame rendered after a change, as the docs gallery does, is laid out right
    ndw = make_ndwidget()
    ndw.show()
    draw(ndw)
    ui = ndw.ui_sliders
    assert ndw.figure._edge_size("bottom") == ui.expected_size == ui.size

    ui.title = None
    ui.playback = False
    assert ndw.figure._edge_size("bottom") == ui.expected_size
    reserved = ui.size
    draw(ndw)
    assert ui.size == reserved
