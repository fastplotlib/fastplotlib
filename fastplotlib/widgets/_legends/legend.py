from functools import partial
from typing import *

import numpy as np
import pygfx

from ...layouts._subplot import Subplot, Dock
from ...layouts import Plot
from ...graphics._base import Graphic
from ...graphics._features._base import FeatureEvent
from ...graphics import LineGraphic, ScatterGraphic, ImageGraphic


class Legend:
    def __init__(self, plot_area: Union[Plot, Subplot, Dock]):
        """

        Parameters
        ----------
        plot_area: Union[Plot, Subplot, Dock]
            plot area to put the legend in

        """
        self._graphics: List[Graphic] = list()

        self._items: Dict[Graphic: LegendItem] = dict()

    def graphics(self) -> Tuple[Graphic, ...]:
        return tuple(self._graphics)

    def add_graphic(self, graphic: Graphic):
        graphic.deleted.add_event_handler(partial(self.remove_graphic, graphic))

    def remove_graphic(self, graphic: Graphic):
        pass


class LegendItem:
    def __init__(
            self,
            label: str,
            color: Any,
    ):
        """

        Parameters
        ----------
        label: str

        color: Any
        """
        self._label = label
        self._color = color


class LineLegendItem(LegendItem):
    def __init__(
            self,
            line_graphic: LineGraphic,
            label: str,
            color: Any,
            thickness: float
    ):
        """

        Parameters
        ----------
        label: str

        color: Any
        """
        super().__init__(label, color)

        line_graphic.colors.add_event_handler(self._update_color)
        line_graphic.thickness.add_event_handler(self._update_thickness)

        # construct Line WorldObject
        data = np.array(
            [[0, 1],
             [0, 0],
             [0, 0]]
        )

        if thickness < 1.1:
            material = pygfx.LineThinMaterial
        else:
            material = pygfx.LineMaterial

        self._world_object = pygfx.Line(
            geometry=pygfx.Geometry(positions=data),
            material=material(thickness=thickness, color=pygfx.Color(color))
        )

    @property
    def label(self) -> str:
        return self._label

    @label.setter
    def label(self, text: str):
        pass

    def _update_color(self, ev: FeatureEvent):
        new_color = ev.pick_info["new_data"]
        self._world_object.material.color = pygfx.Color(new_color)

    def _update_thickness(self, ev: FeatureEvent):
        self._world_object.material.thickness = ev.pick_info["new_data"]
