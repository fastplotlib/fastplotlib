from functools import partial
from collections import OrderedDict
from typing import *

import numpy as np
import pygfx

from ..graphics._base import Graphic
from ..graphics._features._base import FeatureEvent
from ..graphics import LineGraphic, ScatterGraphic, ImageGraphic
from ..utils import mesh_masks


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
            parent,
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

        self._parent = parent

        super().__init__(label, color)

        graphic.colors.add_event_handler(self._update_color)

        # construct Line WorldObject
        data = np.array(
            [[0, 0, 0],
             [3, 0, 0]],
            dtype=np.float32
        )

        material = pygfx.LineMaterial

        self._line_world_object = pygfx.Line(
            geometry=pygfx.Geometry(positions=data),
            material=material(thickness=8, color=self._color)
        )

        # self._line_world_object.world.x = position[0]

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

        self.world_object = pygfx.Group()
        self.world_object.add(self._line_world_object, self._label_world_object)

        self.world_object.world.x = position[0]
        # add 10 to x to account for space for the line
        self._label_world_object.world.x = position[0] + 10

        self.world_object.world.y = position[1]
        self.world_object.world.z = 2

        self.world_object.add_event_handler(partial(self._highlight_graphic, graphic), "click")

    @property
    def label(self) -> str:
        return self._label

    @label.setter
    def label(self, text: str):
        self._parent._check_label_unique(text)
        self._label_world_object.geometry.set_text(text)

    def _update_color(self, ev: FeatureEvent):
        new_color = ev.pick_info["new_data"]
        if np.unique(new_color, axis=0).shape[0] > 1:
            raise ValueError("LegendError: LineGraphic colors no longer appropriate for legend")

        self._color = new_color[0]
        self._line_world_object.material.color = pygfx.Color(self._color)

    def _highlight_graphic(self, graphic, ev):
        graphic_color = pygfx.Color(np.unique(graphic.colors(), axis=0).ravel())

        if graphic_color == self._parent.highlight_color:
            graphic.colors = self._color
        else:
            # hacky but fine for now
            orig_color = pygfx.Color(self._color)
            graphic.colors = self._parent.highlight_color
            self._color = orig_color


class Legend(Graphic):
    def __init__(
            self,
            plot_area,
            highlight_color: Union[str, tuple, np.ndarray] = "w",
            *args,
            **kwargs
    ):
        """

        Parameters
        ----------
        plot_area: Union[Plot, Subplot, Dock]
            plot area to put the legend in

        highlight_color: Union[str, tuple, np.ndarray], default "w"
            highlight color

        """
        self._graphics: List[Graphic] = list()

        # hex id of Graphic, i.e. graphic.loc are the keys
        self._items: OrderedDict[str: LegendItem] = OrderedDict()

        super().__init__(**kwargs)

        group = pygfx.Group()
        self._legend_items_group = pygfx.Group()
        self._set_world_object(group)

        self._mesh = pygfx.Mesh(
            pygfx.box_geometry(50, 10, 1),
            pygfx.MeshBasicMaterial(color=pygfx.Color([0.1, 0.1, 0.1, 1]), wireframe_thickness=10)
        )

        self.world_object.add(self._mesh)
        self.world_object.add(self._legend_items_group)

        self.highlight_color = pygfx.Color(highlight_color)

        plot_area.add_graphic(self)

    def graphics(self) -> Tuple[Graphic, ...]:
        return tuple(self._graphics)

    def _check_label_unique(self, label):
        for legend_item in self._items.values():
            if legend_item.label == label:
                raise ValueError(
                    f"You have passed the label '{label}' which is already used for another legend item. "
                    f"All labels within a legend must be unique."
                )

    def add_graphic(self, graphic: Graphic, label: str = None):
        if graphic in self._graphics:
            raise KeyError(
                f"Graphic already exists in legend with label: '{self._items[graphic.loc].label}'"
            )

        self._check_label_unique(label)

        if isinstance(graphic, LineGraphic):
            y_pos = len(self._items) * -10
            legend_item = LineLegendItem(self, graphic, label, position=(0, y_pos))

            self._legend_items_group.add(legend_item.world_object)

            self._reset_mesh_dims()

        else:
            raise ValueError("Legend only supported for LineGraphic and ScatterGraphic")

        self._graphics.append(graphic)
        self._items[graphic.loc] = legend_item
        graphic.deleted.add_event_handler(partial(self.remove_graphic, graphic))

    def _reset_mesh_dims(self):
        bbox = self._legend_items_group.get_world_bounding_box()

        width, height, _ = bbox.ptp(axis=0)

        self._mesh.geometry.positions.data[mesh_masks.x_right] = width + 7
        self._mesh.geometry.positions.data[mesh_masks.x_left] = -5
        self._mesh.geometry.positions.data[mesh_masks.y_bottom] = 0
        self._mesh.geometry.positions.data[mesh_masks.y_bottom] = -height - 3
        self._mesh.geometry.positions.update_range()

    def remove_graphic(self, graphic: Graphic):
        self._graphics.remove(graphic)
        legend_item = self._items.pop(graphic.loc)
        self._legend_items_group.remove(legend_item.world_object)
        self._reset_item_positions()

    def _reset_item_positions(self):
        for i, (graphic_loc, legend_item) in enumerate(self._items.items()):
            y_pos = i * -10
            legend_item.world_object.world.y = y_pos

        self._reset_mesh_dims()

    def reorder(self, labels: Iterable[str]):
        all_labels = [legend_item.label for legend_item in self._items.values()]

        if not set(labels) == set(all_labels):
            raise ValueError("Must pass all existing legend labels")

        new_items = OrderedDict()

        for label in labels:
            for graphic_loc, legend_item in self._items.items():
                if label == legend_item.label:
                    new_items[graphic_loc] = self._items.pop(graphic_loc)
                    break

        self._items = new_items
        self._reset_item_positions()

    def __getitem__(self, graphic: Graphic) -> LegendItem:
        if not isinstance(graphic, Graphic):
            raise TypeError("Must index Legend with Graphics")

        if graphic.loc not in self._items.keys():
            raise KeyError("Graphic not in legend")

        return self._items[graphic.loc]
