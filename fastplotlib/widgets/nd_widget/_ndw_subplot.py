import numpy as np

from ... import ScatterCollection, LineCollection, LineStack, ImageGraphic
from ...layouts import Subplot
from . import NDImage, NDPositions
from .base import NDGraphic


class NDWSubplot:
    def __init__(self, ndw, subplot: Subplot):
        self.ndw = ndw
        self._subplot = subplot

        self._nd_graphics = list()

    @property
    def nd_graphics(self) -> tuple[NDGraphic]:
        return tuple(self._nd_graphics)

    def __getitem__(self, key):
        if isinstance(key, (int, np.integer)):
            return self.nd_graphics[key]

        for g in self.nd_graphics:
            if g.name == key:
                return g

        else:
            raise KeyError(f"NDGraphc with given key not found: {key}")

    def add_nd_image(self, *args, **kwargs):
        nd = NDImage(self.ndw.indices, *args, **kwargs)
        self._nd_graphics.append(nd)
        self._subplot.add_graphic(nd.graphic)
        return nd

    def add_nd_scatter(self, *args, **kwargs):
        nd = NDPositions(
            self.ndw.indices, *args, graphic=ScatterCollection, **kwargs
        )
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
            self.ndw.indices,
            *args,
            graphic=graphic,
            # x_range_mode=x_range_mode,
            linear_selector=True,
            **kwargs,
        )
        self._nd_graphics.append(nd)
        self._subplot.add_graphic(nd.graphic)
        self._subplot.add_graphic(nd._linear_selector)
        # nd._linear_selector.add_event_handler(
        #     partial(self._set_indices_from_selector, nd), "selection"
        # )

        nd.x_range_mode = x_range_mode

        return nd

    def add_nd_lines(self, *args, **kwargs):
        nd = NDPositions(*args, graphic=LineCollection, **kwargs)
        self._nd_graphics.append(nd)
        self._subplot.add_graphic(nd.graphic)
        return nd

    # def __repr__(self):
    #     return "NDWidget Subplot"
    #
    # def __str__(self):
    #     return "NDWidget Subplot"
