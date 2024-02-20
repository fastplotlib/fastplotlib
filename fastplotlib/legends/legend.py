from functools import partial
from collections import OrderedDict
from typing import *

import numpy as np
import pygfx

from fastplotlib.graphics._base import Graphic
from fastplotlib.graphics._features._base import FeatureEvent
from fastplotlib.graphics import LineGraphic, ScatterGraphic, ImageGraphic


y_bottom = np.array(
    [
        True,
        False,
        True,
        False,
        True,
        False,
        True,
        False,
        False,
        False,
        False,
        False,
        True,
        True,
        True,
        True,
        True,
        True,
        False,
        False,
        True,
        True,
        False,
        False,
    ]
)


class LegendItem:
    def __init__(
            self,
            label: str,
            color: pygfx.Color,
    ):
        """

        Parameters
        ----------
        label: str

        color: pygfx.Color
        """
        self._label = label
        self._color = color


class LineLegendItem(LegendItem):
    def __init__(
            self,
            graphic: LineGraphic,
            label: str,
            position: Tuple[int, int]
    ):
        """

        Parameters
        ----------
        graphic: LineGraphic

        label: str

        position: [x, y]
        """

        if label is not None:
            pass

        elif graphic.name is not None:
            pass

        else:
            raise ValueError("Must specify `label` or Graphic must have a `name` to auto-use as the label")

        if np.unique(graphic.colors(), axis=0).shape[0] > 1:
            raise ValueError("Use colorbars for multi-colored lines, not legends")

        color = pygfx.Color(np.unique(graphic.colors(), axis=0).ravel())

        super().__init__(label, color)

        graphic.colors.add_event_handler(self._update_color)
        graphic.thickness.add_event_handler(self._update_thickness)

        # construct Line WorldObject
        data = np.array(
            [[0, 0, 0],
             [3, 0, 0]],
            dtype=np.float32
        )

        if graphic.thickness() < 1.1:
            material = pygfx.LineThinMaterial
        else:
            material = pygfx.LineMaterial

        self._line_world_object = pygfx.Line(
            geometry=pygfx.Geometry(positions=data),
            material=material(thickness=graphic.thickness(), color=pygfx.Color(color))
        )

        self._line_world_object.world.x = -20 + position[0]
        self._line_world_object.world.y = self._line_world_object.world.y + position[1]

        self._label_world_object = pygfx.Text(
            geometry=pygfx.TextGeometry(
                text=str(label),
                font_size=6,
                screen_space=False,
                anchor="middle-left",
            ),
            material=pygfx.TextMaterial(
                color="w",
                outline_color="w",
                outline_thickness=0,
            )
        )
        self._label_world_object.world.x = self._label_world_object.world.x - 10 + position[0]
        self._label_world_object.world.y = self._label_world_object.world.y + position[1]

        self.world_object = pygfx.Group()
        self.world_object.add(self._line_world_object, self._label_world_object)
        self.world_object.world.z = 2

    @property
    def label(self) -> str:
        return self._label

    @label.setter
    def label(self, text: str):
        self._label_world_object.geometry.set_text(text)

    def _update_color(self, ev: FeatureEvent):
        new_color = ev.pick_info["new_data"]
        if np.unique(new_color, axis=0).shape[0] > 1:
            raise ValueError("LegendError: LineGraphic colors no longer appropriate for legend")

        self._line_world_object.material.color = pygfx.Color(new_color[0])

    def _update_thickness(self, ev: FeatureEvent):
        self._line_world_object.material.thickness = ev.pick_info["new_data"]


class Legend(Graphic):
    def __init__(self, plot_area, *args, **kwargs):
        """

        Parameters
        ----------
        plot_area: Union[Plot, Subplot, Dock]
            plot area to put the legend in

        """
        self._graphics: List[Graphic] = list()

        # hex id of Graphic, i.e. graphic.loc are the keys
        self._items: OrderedDict[str: LegendItem] = OrderedDict()

        super().__init__(**kwargs)

        group = pygfx.Group()
        self._set_world_object(group)

        self._mesh = pygfx.Mesh(
            pygfx.box_geometry(50, 10, 1),
            pygfx.MeshBasicMaterial(color=pygfx.Color([0.1, 0.1, 0.1, 1]), wireframe_thickness=10)
        )

        self.world_object.add(self._mesh)

        plot_area.add_graphic(self)

    def graphics(self) -> Tuple[Graphic, ...]:
        return tuple(self._graphics)

    def add_graphic(self, graphic: Graphic, label: str = None):
        if isinstance(graphic, LineGraphic):
            y_pos = len(self._items) * -10
            legend_item = LineLegendItem(graphic, label, position=(0, y_pos))

            self._mesh.geometry.positions.data[y_bottom, 1] += y_pos
            self._mesh.geometry.positions.update_range()

            self.world_object.add(legend_item.world_object)

        else:
            raise ValueError("Legend only supported for LineGraphic and ScatterGraphic")

        self._items[graphic.loc] = legend_item
        graphic.deleted.add_event_handler(partial(self.remove_graphic, graphic))

    def remove_graphic(self, graphic: Graphic):
        self._graphics.remove(graphic)
        legend_item = self._items.pop(graphic.loc)
        self.world_object.remove(legend_item.world_object)

        # figure out logic of removing items and re-ordering
        # for i, (graphic_loc, legend_item) in enumerate(self._items.items()):
        #     pass

    def __getitem__(self, graphic: Graphic) -> LegendItem:
        if not isinstance(graphic, Graphic):
            raise TypeError("Must index Legend with Graphics")

        if graphic.loc not in self._items.keys():
            raise KeyError("Graphic not in legend")

        return self._items[graphic.loc]
