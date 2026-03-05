import os
from time import perf_counter

import numpy as np
from imgui_bundle import imgui, imgui_ctx, icons_fontawesome_6 as fa

from ...graphics import (
    ScatterCollection,
    LineCollection,
    LineStack,
    ImageGraphic,
    ImageVolumeGraphic,
)
from ...utils import quick_min_max
from ...layouts import Subplot
from ...ui import EdgeWindow, StandardRightClickMenu
from ._index import RangeContinuous
from ._base import NDGraphic
from ._nd_positions import NDPositions
from ._nd_image import NDImage

position_graphics = [ScatterCollection, LineCollection, LineStack, ImageGraphic]


class NDWidgetUI(EdgeWindow):
    def __init__(self, figure, size, ndwidget):
        super().__init__(
            figure=figure,
            size=size,
            title="NDWidget controls",
            location="bottom",
            window_flags=imgui.WindowFlags_.no_collapse
            | imgui.WindowFlags_.no_resize
            | imgui.WindowFlags_.no_title_bar,
        )
        self._ndwidget = ndwidget

        ref_ranges = self._ndwidget.ref_ranges

        # whether or not a dimension is in play mode
        self._playing = {dim: False for dim in ref_ranges.keys()}

        # approximate framerate for playing
        self._fps = {dim: 20 for dim in ref_ranges.keys()}

        # framerate converted to frame time
        self._frame_time = {dim: 1 / 20 for dim in ref_ranges.keys()}

        # last timepoint that a frame was displayed from a given dimension
        self._last_frame_time = {dim: perf_counter() for dim in ref_ranges.keys()}

        # loop playback
        self._loop = {dim: False for dim in ref_ranges.keys()}

        # auto-plays the ImageWidget's left-most dimension in docs galleries
        if "DOCS_BUILD" in os.environ.keys():
            if os.environ["DOCS_BUILD"] == "1":
                self._playing[0] = True
                self._loop = True

        self._max_display_windows: dict[NDGraphic, float | int] = dict()

    def _set_index(self, dim, index):
        if index >= self._ndwidget.ref_ranges[dim].stop:
            if self._loop[dim]:
                index = self._ndwidget.ref_ranges[dim].start
            else:
                index = self._ndwidget.ref_ranges[dim].stop
                self._playing[dim] = False

        self._ndwidget.indices[dim] = index

    def update(self):
        now = perf_counter()

        for dim, current_index in self._ndwidget.indices:
            # push id since we have the same buttons for each dim
            imgui.push_id(f"{self._id_counter}_{dim}")

            rr = self._ndwidget.ref_ranges[dim]

            if self._playing[dim]:
                # show pause button if playing
                if imgui.button(label=fa.ICON_FA_PAUSE):
                    # if pause button clicked, then set playing to false
                    self._playing[dim] = False

                # if in play mode and enough time has elapsed w.r.t. the desired framerate, increment the index
                if now - self._last_frame_time[dim] >= self._frame_time[dim]:
                    self._set_index(dim, current_index + rr.step)
                    self._last_frame_time[dim] = now

            else:
                # we are not playing, so display play button
                if imgui.button(label=fa.ICON_FA_PLAY):
                    # if play button is clicked, set last frame time to 0 so that index increments on next render
                    self._last_frame_time[dim] = 0
                    # set playing to True since play button was clicked
                    self._playing[dim] = True

            imgui.same_line()
            # step back one frame button
            if imgui.button(label=fa.ICON_FA_BACKWARD_STEP) and not self._playing[dim]:
                self._set_index(dim, current_index - rr.step)

            imgui.same_line()
            # step forward one frame button
            if imgui.button(label=fa.ICON_FA_FORWARD_STEP) and not self._playing[dim]:
                self._set_index(dim, current_index + rr.step)

            imgui.same_line()
            # stop button
            if imgui.button(label=fa.ICON_FA_STOP):
                self._playing[dim] = False
                self._last_frame_time[dim] = 0
                self._ndwidget.indices[dim] = rr.start

            imgui.same_line()
            # loop checkbox
            _, self._loop[dim] = imgui.checkbox(
                label=fa.ICON_FA_ROTATE, v=self._loop[dim]
            )
            if imgui.is_item_hovered(0):
                imgui.set_tooltip("loop playback")

            imgui.same_line()
            imgui.text("framerate :")
            imgui.same_line()
            imgui.set_next_item_width(100)
            # framerate int entry
            fps_changed, value = imgui.input_int(
                label="fps", v=self._fps[dim], step_fast=5
            )
            if imgui.is_item_hovered(0):
                imgui.set_tooltip(
                    "framerate is approximate and less reliable as it approaches your monitor refresh rate"
                )
            if fps_changed:
                if value < 1:
                    value = 1
                if value > 50:
                    value = 50
                self._fps[dim] = value
                self._frame_time[dim] = 1 / value

            imgui.text(str(dim))
            imgui.same_line()
            # so that slider occupies full width
            imgui.set_next_item_width(self.width * 0.85)

            if isinstance(rr, RangeContinuous):
                changed, new_index = imgui.slider_float(
                    v=current_index,
                    v_min=rr.start,
                    v_max=rr.stop - rr.step,
                    label=f"##{dim}",
                )

                # TODO: refactor all this stuff, make fully fledged UI
                if changed:
                    self._ndwidget.indices[dim] = new_index

                elif imgui.is_item_hovered():
                    if imgui.is_key_pressed(imgui.Key.right_arrow):
                        self._set_index(dim, current_index + rr.step)

                    elif imgui.is_key_pressed(imgui.Key.left_arrow):
                        self._set_index(dim, current_index - rr.step)

            imgui.pop_id()


class RightClickMenu(StandardRightClickMenu):
    def __init__(self, figure):
        self._ndwidget = None
        self._ndgraphic_windows = set()

        super().__init__(figure=figure)

    def set_nd_widget(self, ndw):
        self._ndwidget = ndw

    def _extra_menu(self):
        if self._ndwidget is None:
            return

        if imgui.begin_menu("ND Graphics"):
            subplot = self.get_subplot()
            for ndg in self._ndwidget[subplot].nd_graphics:
                name = ndg.name if ndg.name is not None else hex(id(ndg))
                if imgui.menu_item(
                    f"{name}", "", False
                )[0]:
                    self._ndgraphic_windows.add(ndg)

            imgui.end_menu()

    def update(self):
        super().update()
        subplot = self.get_subplot()

        for ndg in list(self._ndgraphic_windows):  # set -> list so we can change size during iteration
            name = ndg.name if ndg.name is not None else hex(id(ndg))
            imgui.set_next_window_size((0, 0))
            _, open = imgui.begin(name, True)

            if isinstance(ndg, NDPositions):
                self._draw_nd_pos_ui(subplot, ndg)

            elif isinstance(ndg, NDImage):
                self._draw_nd_image_ui(subplot, ndg)

            if not open:
                self._ndgraphic_windows.remove(ndg)

            imgui.end()

    def _draw_nd_image_ui(self, subplot, nd_image: NDImage):
        _min, _max = quick_min_max(nd_image.graphic.data.value)
        changed, vmin = imgui.slider_float(
            "vmin", nd_image.graphic.vmin, v_min=_min, v_max=_max
        )
        if changed:
            nd_image.graphic.vmin = vmin

        changed, vmax = imgui.slider_float(
            "vmax", nd_image.graphic.vmax, v_min=_min, v_max=_max
        )
        if changed:
            nd_image.graphic.vmax = vmax

        changed, new_gamma = imgui.slider_float(
            "gamma", nd_image.graphic._material.gamma, 0.01, 5
        )
        if changed:
            nd_image.graphic._material.gamma = new_gamma

    def _draw_nd_pos_ui(self, subplot: Subplot, nd_graphic: NDPositions):
        for i, cls in enumerate(position_graphics):
            if imgui.radio_button(cls.__name__, type(nd_graphic.graphic) is cls):
                nd_graphic.graphic = cls
                subplot.auto_scale()

        changed, val = imgui.checkbox(
            "use display window", nd_graphic.display_window is not None
        )

        p_dim = nd_graphic.processor.spatial_dims[1]

        if changed:
            if not val:
                nd_graphic.display_window = None
            else:
                # pick a value 10% of the reference range
                nd_graphic.display_window = self._ndwidget.ref_ranges[p_dim].range * 0.1

        if nd_graphic.display_window is not None:
            if isinstance(nd_graphic.display_window, (int, np.integer)):
                slider = imgui.slider_int
                input_ = imgui.input_int
                type_ = int
            else:
                slider = imgui.slider_float
                input_ = imgui.input_float
                type_ = float

            changed, new = slider(
                "display window",
                v=nd_graphic.display_window,
                v_min=type_(0),
                v_max=type_(self._ndwidget.ref_ranges[p_dim].stop * 0.1),
            )

            if changed:
                nd_graphic.display_window = new

        options = [None, "fixed-window", "view-range"]
        changed, option = imgui.combo(
            "x-range mode",
            options.index(nd_graphic.x_range_mode),
            [str(o) for o in options],
        )
        if changed:
            nd_graphic.x_range_mode = options[option]
