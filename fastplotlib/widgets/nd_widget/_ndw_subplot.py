from typing import Literal
import numpy as np

from ... import ScatterCollection, ScatterStack, LineCollection, LineStack, ImageGraphic
from ...layouts import Subplot
from . import NDImage, NDPositions
from ._base import NDGraphic


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
        nd = NDImage(self.ndw.indices, self._subplot, *args, **kwargs)
        self._nd_graphics.append(nd)

        return nd

    def add_nd_scatter(self, *args, **kwargs):
        # TODO: better func signature here, send all kwargs to processor_kwargs
        nd = NDPositions(self.ndw.indices, self._subplot, *args, graphic_type=ScatterCollection, **kwargs)
        self._nd_graphics.append(nd)

        return nd

    def add_nd_timeseries(
        self,
        *args,
        graphic_type: type[LineCollection | LineStack | ScatterStack | ImageGraphic] = LineStack,
        x_range_mode: Literal["fixed", "auto"] | None = "auto",
        **kwargs,
    ):
        nd = NDPositions(
            self.ndw.indices,
            self._subplot,
            *args,
            graphic_type=graphic_type,
            linear_selector=True,
            x_range_mode=x_range_mode,
            **kwargs,
        )
        self._nd_graphics.append(nd)
        self._subplot.add_graphic(nd._linear_selector)

        # need plot_area to exist before these this can be called
        nd.x_range_mode = x_range_mode

        # probably don't want to maintain aspect
        self._subplot.camera.maintain_aspect = False

        return nd

    def add_nd_lines(self, *args, **kwargs):
        nd = NDPositions(self.ndw.indices, self._subplot, *args, graphic_type=LineCollection, **kwargs)
        self._nd_graphics.append(nd)
        return nd
