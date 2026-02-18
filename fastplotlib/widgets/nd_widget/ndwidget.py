from dataclasses import dataclass
from functools import partial
import os
from time import perf_counter
from typing import Any, Sequence

from imgui_bundle import imgui, icons_fontawesome_6 as fa
import numpy as np

from ...layouts import ImguiFigure, Subplot
from ...graphics import ScatterCollection, LineCollection, LineStack, ImageGraphic
from ...ui import EdgeWindow
from .base import NDGraphic, NDProcessor
from ._nd_image import NDImage, NDImageProcessor
from ._nd_positions import NDPositions, NDPositionsProcessor


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
            raise IndexError(f"index: {index} value: {val} out of bounds: [{self.start}, {self.stop}]")

        return val


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
            **kwargs
    ):
        nd = NDPositions(*args, graphic=graphic, multi=True, auto_x_range=True, linear_selector=True, **kwargs)
        self._nd_graphics.append(nd)
        self._subplot.add_graphic(nd.graphic)
        self._subplot.add_graphic(nd._linear_selector)
        nd._linear_selector.add_event_handler(partial(self._set_indices_from_selector, nd), "selection")

        return nd

    def add_nd_lines(self, *args, **kwargs):
        nd = NDPositions(*args, graphic=LineCollection, multi=True, **kwargs)
        self._nd_graphics.append(nd)
        self._subplot.add_graphic(nd.graphic)
        return nd

    def _set_indices_from_selector(self, skip_graphic: NDGraphic, ev):
        # skip the NDPosition object which has the linear selector that triggered this event
        skip_graphic._pause = True

        x = ev.info["value"]
        indices_new = list(self.ndw.indices)
        # linear selector for NDPositions always acts on the `p` dim
        indices_new[-1] = x
        self.ndw.indices = tuple(indices_new)

        # restore
        skip_graphic._pause = False

    # def __repr__(self):
    #     return "NDWidget Subplot"
    #
    # def __str__(self):
    #     return "NDWidget Subplot"


class NDWSliders(EdgeWindow):
    def __init__(self, figure, size, ndwidget):
        super().__init__(figure=figure, size=size, title="NDWidget controls", location="bottom")
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

    def update(self):
        indices_changed = False

        for dim_index, (current_index, refr) in enumerate(zip(self._ndwidget.indices, self._ndwidget.ref_ranges)):
            if isinstance(refr, ReferenceRangeContinuous):
                changed, val = imgui.slider_float(
                    v=current_index,
                    v_min=refr.start,
                    v_max=refr.stop,
                    label=refr.unit
                )

                if changed:
                    new_indices = list(self._ndwidget.indices)
                    new_indices[dim_index] = val

                    indices_changed = True

        if indices_changed:
            self._ndwidget.indices = tuple(new_indices)


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

        self._subplots: dict[Subplot, NDWSubplot] = dict()
        for subplot in self.figure:
            self._subplots[subplot] = NDWSubplot(self, subplot)

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
        for subplot in self._subplots.values():
            for ndg in subplot.nd_graphics:
                ndg.indices = new_indices

        self._indices = new_indices

    def __getitem__(self, key):
        subplot = self.figure[key]
        return self._subplots[subplot]

    def show(self, **kwargs):
        return self.figure.show(**kwargs)
