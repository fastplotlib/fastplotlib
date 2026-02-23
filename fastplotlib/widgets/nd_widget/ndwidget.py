from dataclasses import dataclass
from functools import partial
import os
from time import perf_counter
from typing import Any, Sequence

from imgui_bundle import imgui, icons_fontawesome_6 as fa
import numpy as np

from ...layouts import ImguiFigure, Subplot
from ...graphics import ScatterCollection, LineCollection, LineStack, ImageGraphic, ImageVolumeGraphic
from ...ui import EdgeWindow
from .base import NDGraphic, NDProcessor
from ._nd_image import NDImage, NDImageProcessor
from ._nd_positions import NDPositions, NDPositionsProcessor


position_graphics = [ScatterCollection, LineCollection, LineStack, ImageGraphic]
image_graphics = [ImageGraphic, ImageVolumeGraphic]


@dataclass
class ReferenceRangeContinuous:
    start: int | float
    stop: int | float
    step: int | float
    unit: str

    def __getitem__(self, index: int):
        """return the value at the index w.r.t. the step size"""
        # if index is negative, turn to positive index
        if index < 0:
            raise ValueError("negative indexing not supported")

        val = self.start + (self.step * index)
        if not self.start <= val <= self.stop:
            raise IndexError(
                f"index: {index} value: {val} out of bounds: [{self.start}, {self.stop}]"
            )

        return val

    @property
    def range(self) -> int | float:
        return self.stop - self.start


@dataclass
class ReferenceRangeDiscrete:
    options: Sequence[Any]
    unit: str

    def __getitem__(self, index: int):
        if index > len(self.options):
            raise IndexError

        return self.options[index]

    def __len__(self):
        return len(self.options)


class NDWSubplot:
    def __init__(self, ndw, subplot: Subplot):
        self.ndw = ndw
        self._subplot = subplot

        self._nd_graphics = list()

    @property
    def nd_graphics(self) -> list[NDGraphic]:
        return self._nd_graphics

    def __getitem__(self, key):
        if isinstance(key, (int, np.integer)):
            return self.nd_graphics[key]

        for g in self.nd_graphics:
            if g.name == key:
                return g

        else:
            raise KeyError(f"NDGraphc with given key not found: {key}")

    def add_nd_image(self, *args, **kwargs):
        nd = NDImage(*args, **kwargs)
        self._nd_graphics.append(nd)
        self._subplot.add_graphic(nd.graphic)
        return nd

    def add_nd_scatter(self, *args, **kwargs):
        nd = NDPositions(*args, graphic=ScatterCollection, multi=True, **kwargs)
        self._nd_graphics.append(nd)
        self._subplot.add_graphic(nd.graphic)

        return nd

    def add_nd_timeseries(
        self,
        *args,
        graphic: type[LineCollection | LineStack | ImageGraphic] = LineStack,
        x_range_mode="fixed-window",
        **kwargs,
    ):
        nd = NDPositions(
            *args,
            graphic=graphic,
            multi=True,
            x_range_mode=x_range_mode,
            linear_selector=True,
            **kwargs,
        )
        self._nd_graphics.append(nd)
        self._subplot.add_graphic(nd.graphic)
        self._subplot.add_graphic(nd._linear_selector)
        nd._linear_selector.add_event_handler(
            partial(self._set_indices_from_selector, nd), "selection"
        )

        nd.x_range_mode = x_range_mode

        return nd

    def add_nd_lines(self, *args, **kwargs):
        nd = NDPositions(*args, graphic=LineCollection, multi=True, **kwargs)
        self._nd_graphics.append(nd)
        self._subplot.add_graphic(nd.graphic)
        return nd

    def _set_indices_from_selector(self, skip_graphic: NDGraphic, ev):
        # skip the NDPosition object which has the linear selector that triggered this event
        skip_graphic._block_update_indices = True

        x = ev.info["value"]
        indices_new = list(self.ndw.indices)
        # linear selector for NDPositions always acts on the `p` dim
        indices_new[-1] = x
        self.ndw.indices = tuple(indices_new)

        # restore
        skip_graphic._block_update_indices = False

    # def __repr__(self):
    #     return "NDWidget Subplot"
    #
    # def __str__(self):
    #     return "NDWidget Subplot"


class NDWSliders(EdgeWindow):
    def __init__(self, figure, size, ndwidget):
        super().__init__(
            figure=figure, size=size, title="NDWidget controls", location="bottom",
            window_flags=imgui.WindowFlags_.no_collapse
        | imgui.WindowFlags_.no_resize | imgui.WindowFlags_.no_title_bar
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
        indices_changed = False

        if imgui.begin_tab_bar("NDWidget Controls"):

            if imgui.begin_tab_item("Indices")[0]:
                for dim_index, (current_index, refr) in enumerate(
                    zip(self._ndwidget.indices, self._ndwidget.ref_ranges)
                ):
                    if isinstance(refr, ReferenceRangeContinuous):
                        changed, new_index = imgui.slider_float(
                            v=current_index,
                            v_min=refr.start,
                            v_max=refr.stop,
                            label=refr.unit,
                        )

                        # TODO: refactor all this stuff, make fully fledged UI
                        if changed:
                            new_indices = list(self._ndwidget.indices)
                            new_indices[dim_index] = new_index

                            indices_changed = True

                        elif imgui.is_item_hovered():
                            if imgui.is_key_pressed(imgui.Key.right_arrow):
                                new_index = current_index + refr.step
                                new_indices = list(self._ndwidget.indices)
                                new_indices[dim_index] = new_index

                                indices_changed = True

                            if imgui.is_key_pressed(imgui.Key.left_arrow):
                                new_index = current_index - refr.step
                                new_indices = list(self._ndwidget.indices)
                                new_indices[dim_index] = new_index

                                indices_changed = True

                if indices_changed:
                    self._ndwidget.indices = tuple(new_indices)

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

        changed, val = imgui.checkbox("use display window", nd_graphic.display_window is not None)
        if changed:
            if not val:
                nd_graphic.display_window = None
            else:
                # pick a value 10% of the reference range
                nd_graphic.display_window = self._ndwidget.ref_ranges[0].range * 0.1

        if nd_graphic.display_window is not None:
            if isinstance(
                    nd_graphic.display_window, (int, np.integer)
            ):
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
                v_max=type_(self._ndwidget.ref_ranges[0].stop * 0.25),
            )

            if changed:
                nd_graphic.display_window = new

        options = [None, "fixed-window", "view-range"]
        changed, option = imgui.combo("x-range mode", options.index(nd_graphic.x_range_mode), [str(o) for o in options])
        if changed:
            nd_graphic.x_range_mode = options[option]


class NDWidget:
    def __init__(self, ref_ranges: list[tuple], **kwargs):
        self._ref_ranges = list()

        for r in ref_ranges:
            if len(r) == 4:
                # assume start, stop, step, unit
                refr = ReferenceRangeContinuous(*r)
            elif len(r) == 2:
                refr = ReferenceRangeDiscrete(*r)
            else:
                raise ValueError

            self._ref_ranges.append(refr)

        self._figure = ImguiFigure(**kwargs)

        self._subplots_nd: dict[Subplot, NDWSubplot] = dict()
        for subplot in self.figure:
            self._subplots_nd[subplot] = NDWSubplot(self, subplot)

        # starting index for all dims
        self._indices = tuple(refr[0] for refr in self.ref_ranges)

        # hard code the expected height so that the first render looks right in tests, docs etc.
        ui_size = 57 + (50 * len(self.indices))

        self._sliders_ui = NDWSliders(self.figure, ui_size, self)
        self.figure.add_gui(self._sliders_ui)

    @property
    def figure(self) -> ImguiFigure:
        return self._figure

    @property
    def ref_ranges(self) -> tuple[ReferenceRangeContinuous | ReferenceRangeDiscrete]:
        return tuple(self._ref_ranges)

    @property
    def indices(self) -> tuple:
        return self._indices

    @indices.setter
    def indices(self, new_indices: tuple[Any]):
        for subplot in self._subplots_nd.values():
            for ndg in subplot.nd_graphics:
                ndg.indices = new_indices

        self._indices = new_indices

    def __getitem__(self, key: str | tuple[int, int] | Subplot):
        if not isinstance(key, Subplot):
            key = self.figure[key]
        return self._subplots_nd[key]

    def show(self, **kwargs):
        return self.figure.show(**kwargs)
