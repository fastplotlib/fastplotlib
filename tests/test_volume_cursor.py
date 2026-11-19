import numpy as np
from numpy import testing as npt
import pytest

import fastplotlib as fpl


SHAPE_ZYX = (8, 20, 30)


def make_figure():
    fig = fpl.Figure(shape=(1, 3), cameras=["2d", "2d", "3d"], size=(600, 200))
    volume = fig[0, 2].add_image_volume(np.random.rand(*SHAPE_ZYX).astype(np.float32))
    return fig, volume


def test_lines_and_slices_follow_position():
    fig, volume = make_figure()
    cursor = fpl.VolumeCursor(position=(1, 2, 3))
    cursor.add_subplot(fig[0, 0], axes=("x", "y"))
    cursor.add_subplot(fig[0, 1], axes=("x", "z"))
    cursor.add_volume(volume)

    cursor.position = (10, 5, 4)

    line_v, line_h = cursor._subplots[fig[0, 0]][1].children
    assert line_v.local.x == 10
    assert line_h.local.y == 5
    line_v, line_h = cursor._subplots[fig[0, 1]][1].children
    assert line_v.local.x == 10
    assert line_h.local.y == 4

    slices = cursor.slices(volume)
    npt.assert_allclose(slices["x"].plane, (1, 0, 0, -10))
    npt.assert_allclose(slices["y"].plane, (0, 1, 0, -5))
    npt.assert_allclose(slices["z"].plane, (0, 0, 1, -4))
    outline_z = cursor._volumes[volume][1]["z"].geometry.positions.data
    npt.assert_allclose(outline_z[:, 2], 4)


def test_slices_share_the_volume_buffer_and_follow_its_contrast():
    fig, volume = make_figure()
    cursor = fpl.VolumeCursor()
    cursor.add_volume(volume)

    for graphic in cursor.slices(volume).values():
        assert graphic.data.buffer is volume.data.buffer

    volume.vmin, volume.vmax = 0.2, 0.7
    for graphic in cursor.slices(volume).values():
        assert graphic.vmin == pytest.approx(0.2)
        assert graphic.vmax == pytest.approx(0.7)


def test_event_handler_gets_the_new_position_once():
    fig, volume = make_figure()
    cursor = fpl.VolumeCursor()
    received = list()
    cursor.add_event_handler(received.append)

    cursor.position = (1, 2, 3)
    cursor.position = (1, 2, 3)

    assert received == [(1.0, 2.0, 3.0)]


def test_visible_hides_lines_slices_and_outlines():
    fig, volume = make_figure()
    cursor = fpl.VolumeCursor()
    cursor.add_subplot(fig[0, 0], axes=("x", "y"))
    cursor.add_volume(volume)

    cursor.visible = False

    assert not cursor._subplots[fig[0, 0]][1].visible
    assert not any(graphic.visible for graphic in cursor.slices(volume).values())
    assert not any(outline.visible for outline in cursor._volumes[volume][1].values())


def test_remove_volume_deletes_its_slices():
    fig, volume = make_figure()
    cursor = fpl.VolumeCursor()
    cursor.add_volume(volume)
    cursor.remove_volume(volume)

    assert len(fig[0, 2].graphics) == 1


@pytest.mark.parametrize("axes", [("x", "x"), ("x",), ("x", "w")])
def test_bad_axes_raise(axes):
    fig, volume = make_figure()
    with pytest.raises(ValueError):
        fpl.VolumeCursor().add_subplot(fig[0, 0], axes=axes)
