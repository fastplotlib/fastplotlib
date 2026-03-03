import numpy as np
from imgui_bundle import imgui

from ...graphics import (
    ScatterCollection,
    LineCollection,
    LineStack,
    ImageGraphic,
    ImageVolumeGraphic,
)
from ...layouts import Subplot
from ...ui import EdgeWindow
from . import NDPositions
from ._index import ReferenceRangeContinuous
from .base import NDGraphic

position_graphics = [ScatterCollection, LineCollection, LineStack, ImageGraphic]
image_graphics = [ImageGraphic, ImageVolumeGraphic]


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

        # n_sliders = self._image_widget.n_sliders
        #
        # # whether or not a dimension is in play mode
        # self._playing: list[bool] = [False] * n_sliders
        #
        # # approximate framerate for playing
        # self._fps: list[int] = [20] * n_sliders
        #
        # # framerate converted to frame time
        # self._frame_time: list[float] = [1 / 20] * n_sliders
        #
        # # last timepoint that a frame was displayed from a given dimension
        # self._last_frame_time: list[float] = [perf_counter()] * n_sliders
        #
        # # loop playback
        # self._loop = False
        #
        # # auto-plays the ImageWidget's left-most dimension in docs galleries
        # if "DOCS_BUILD" in os.environ.keys():
        #     if os.environ["DOCS_BUILD"] == "1":
        #         self._playing[0] = True
        #         self._loop = True
        #
        # self.pause = False

        self._selected_subplot = self._ndwidget.figure[0, 0].name
        self._selected_nd_graphic = 0

        self._max_display_windows: dict[NDGraphic, float | int] = dict()

    def update(self):
        if imgui.begin_tab_bar("NDWidget Controls"):

            if imgui.begin_tab_item("Indices")[0]:
                for dim, current_index in self._ndwidget.indices:
                    refr = self._ndwidget.ref_ranges[dim]

                    if isinstance(refr, ReferenceRangeContinuous):
                        changed, new_index = imgui.slider_float(
                            v=current_index,
                            v_min=refr.start,
                            v_max=refr.stop,
                            label=dim,
                        )

                        # TODO: refactor all this stuff, make fully fledged UI
                        if changed:
                            self._ndwidget.indices[dim] = new_index

                        elif imgui.is_item_hovered():
                            if imgui.is_key_pressed(imgui.Key.right_arrow):
                                self._ndwidget.indices[dim] = current_index + refr.step

                            elif imgui.is_key_pressed(imgui.Key.left_arrow):
                                self._ndwidget.indices[dim] = current_index - refr.step

                imgui.end_tab_item()

            if imgui.begin_tab_item("NDGraphic properties")[0]:
                imgui.text("Subplots:")

                self._draw_nd_graphics_props_tab()

                imgui.end_tab_item()

            imgui.end_tab_bar()

    def _draw_nd_graphics_props_tab(self):
        for subplot in self._ndwidget.figure:
            if imgui.tree_node(subplot.name):
                self._draw_ndgraphics_node(subplot)
                imgui.tree_pop()

    def _draw_ndgraphics_node(self, subplot: Subplot):
        for ng in self._ndwidget[subplot].nd_graphics:
            if imgui.tree_node(str(ng)):
                if isinstance(ng, NDPositions):
                    self._draw_nd_pos_ui(subplot, ng)
                imgui.tree_pop()

    def _draw_nd_pos_ui(self, subplot: Subplot, nd_graphic: NDPositions):
        for i, cls in enumerate(position_graphics):
            if imgui.radio_button(cls.__name__, type(nd_graphic.graphic) is cls):
                nd_graphic.graphic = cls
                subplot.auto_scale()
            if i < len(position_graphics) - 1:
                imgui.same_line()

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
                v_max=type_(self._ndwidget.ref_ranges[p_dim].stop * 0.25),
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
