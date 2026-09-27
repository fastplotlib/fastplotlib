import numpy as np
import pytest

import fastplotlib as fpl

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
