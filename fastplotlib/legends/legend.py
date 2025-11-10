from functools import partial
from collections import OrderedDict
from typing import Iterable

import numpy as np
import pygfx

from ..utils.enums import RenderQueue
from ..graphics import Graphic
from ..graphics.features import GraphicFeatureEvent
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
        self, parent, graphic: LineGraphic, label: str, position: tuple[int, int]
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
            raise ValueError(
                "Must specify `label` or Graphic must have a `name` to auto-use as the label"
            )

        # for now only support lines with a single color
        if np.unique(graphic.colors.value, axis=0).shape[0] > 1:
            raise ValueError("Use colorbars for multi-colored lines, not legends")

        color = pygfx.Color(np.unique(graphic.colors.value, axis=0).ravel())

        self._parent = parent

        super().__init__(label, color)

        graphic.colors.add_event_handler(self._update_color)

        # construct Line WorldObject
        data = np.array([[0, 0, 0], [3, 0, 0]], dtype=np.float32)

        self._line_world_object = pygfx.Line(
            geometry=pygfx.Geometry(positions=data),
            material=pygfx.LineMaterial(
                alpha_mode="blend",
                render_queue=RenderQueue.overlay,
                thickness=8,
                color=self._color,
                depth_write=False,
                depth_test=False,
            ),
        )

        # self._line_world_object.world.x = position[0]

        self._label_world_object = pygfx.Text(
            text=str(label),
            font_size=6,
            screen_space=False,
            anchor="middle-left",
            material=pygfx.TextMaterial(
                alpha_mode="blend",
                aa=True,
                render_queue=RenderQueue.overlay,
                color="w",
                outline_color="w",
                outline_thickness=0,
                depth_write=False,
                depth_test=False,
            ),
        )

        self.world_object = pygfx.Group()
        self.world_object.add(self._line_world_object, self._label_world_object)

        self.world_object.world.x = position[0]
        # add 10 to x to account for space for the line
        self._label_world_object.world.x = position[0] + 10

        self.world_object.world.y = position[1]

        self.world_object.add_event_handler(
            partial(self._highlight_graphic, graphic), "click"
        )

    @property
    def label(self) -> str:
        return self._label

    @label.setter
    def label(self, text: str):
        self._parent._check_label_unique(text)
        self._label_world_object.geometry.set_text(text)

    def _update_color(self, ev: GraphicFeatureEvent):
        new_color = ev.info["value"]
        if np.unique(new_color, axis=0).shape[0] > 1:
            raise ValueError(
                "LegendError: LineGraphic colors no longer appropriate for legend"
            )

        self._color = new_color[0]
        self._line_world_object.material.color = pygfx.Color(self._color)

    def _highlight_graphic(self, graphic: Graphic, ev):
        graphic_color = pygfx.Color(np.unique(graphic.colors.value, axis=0).ravel())

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
        highlight_color: str | tuple | np.ndarray = "w",
        max_rows: int = 5,
        *args,
        **kwargs,
    ):
        """

        Parameters
        ----------
        plot_area: Union[Plot, Subplot, Dock]
            plot area to put the legend in

        highlight_color: Union[str, tuple, np.ndarray], default "w"
            highlight color

        max_rows: int, default 5
            maximum number of rows allowed in the legend

        """
        self._graphics: list[Graphic] = list()

        # hex id of Graphic, i.e. graphic._fpl_address are the keys
        self._items: OrderedDict[str:LegendItem] = OrderedDict()

        super().__init__(*args, **kwargs)

        group = pygfx.Group()
        self._legend_items_group = pygfx.Group()
        self._set_world_object(group)

        self._mesh = pygfx.Mesh(
            pygfx.box_geometry(50, 10, 1),
            pygfx.MeshBasicMaterial(
                alpha_mode="blend",
                render_queue=RenderQueue.overlay,
                color=pygfx.Color([0.1, 0.1, 0.1, 1]),
                wireframe_thickness=10,
                depth_write=False,
                depth_test=False,
            ),
        )

        # Plane gets rendered before text and line
        self._mesh.render_order = -1

        self.world_object.add(self._mesh)
        self.world_object.add(self._legend_items_group)

        self.highlight_color = pygfx.Color(highlight_color)

        self._plot_area = plot_area
        self._plot_area.add_graphic(self)

        if self._plot_area.__class__.__name__ == "Dock":
            if self._plot_area.size < 1:
                self._plot_area.size = 100

        # TODO: refactor with "moveable graphic" base class once that's done
        self._mesh.add_event_handler(self._pointer_down, "pointer_down")
        self._plot_area.renderer.add_event_handler(self._pointer_move, "pointer_move")
        self._plot_area.renderer.add_event_handler(self._pointer_up, "pointer_up")

        self._last_position = None
        self._initial_controller_state = self._plot_area.controller.enabled

        self._max_rows = max_rows

        self._row_counter = 0
        self._col_counter = 0

    def graphics(self) -> tuple[Graphic, ...]:
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
                f"Graphic already exists in legend with label: '{self._items[graphic._fpl_address].label}'"
            )

        self._check_label_unique(label)

        new_col_ix = self._col_counter
        new_row_ix = self._row_counter

        x_pos = 0
        y_pos = 0

        if self._row_counter == self._max_rows:
            # set counters
            new_col_ix = self._col_counter + 1

            # get x position offset for this new column of LegendItems
            # start by getting the LegendItems in the previous column
            prev_column_items: list[LegendItem] = list(self._items.values())[
                -self._max_rows :
            ]
            # x position of LegendItems in previous column
            x_pos = prev_column_items[-1].world_object.world.x
            max_width = 0
            # get width of widest LegendItem in previous column to add to x_pos offset for this column
            for item in prev_column_items:
                bbox = item.world_object.get_world_bounding_box()
                width, height, depth = np.ptp(bbox, axis=0)
                max_width = max(max_width, width)

            # x position offset for this new column
            x_pos = x_pos + max_width + 15  # add 15 for spacing

            # rest row index for next iteration
            new_row_ix = 1
        else:
            if len(self._items) > 0:
                x_pos = list(self._items.values())[-1].world_object.world.x

            y_pos = new_row_ix * -10
            new_row_ix = self._row_counter + 1

        if isinstance(graphic, LineGraphic):
            legend_item = LineLegendItem(self, graphic, label, position=(x_pos, y_pos))
        else:
            raise ValueError("Legend only supported for LineGraphic for now.")

        self._legend_items_group.add(legend_item.world_object)
        self._reset_mesh_dims()

        self._graphics.append(graphic)
        self._items[graphic._fpl_address] = legend_item

        graphic.add_event_handler(partial(self.remove_graphic, graphic), "deleted")

        self._col_counter = new_col_ix
        self._row_counter = new_row_ix

    def _reset_mesh_dims(self):
        bbox = self._legend_items_group.get_world_bounding_box()

        width, height, _ = np.ptp(bbox, axis=0)

        self._mesh.geometry.positions.data[mesh_masks.x_right] = width + 7
        self._mesh.geometry.positions.data[mesh_masks.x_left] = -5
        self._mesh.geometry.positions.data[mesh_masks.y_bottom] = 0
        self._mesh.geometry.positions.data[mesh_masks.y_bottom] = -height - 3
        self._mesh.geometry.positions.update_range()

    def remove_graphic(self, graphic: Graphic):
        self._graphics.remove(graphic)
        legend_item = self._items.pop(graphic._fpl_address)
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

    def _pointer_down(self, ev):
        self._last_position = self._plot_area.map_screen_to_world(ev)
        self._initial_controller_state = self._plot_area.controller.enabled

    def _pointer_move(self, ev):
        if self._last_position is None:
            return

        self._plot_area.controller.enabled = False

        world_pos = self._plot_area.map_screen_to_world(ev)

        # outside viewport
        if world_pos is None:
            return

        delta = world_pos - self._last_position

        self.world_object.world.x = self.world_object.world.x + delta[0]
        self.world_object.world.y = self.world_object.world.y + delta[1]

        self._last_position = world_pos

        self._plot_area.controller.enabled = self._initial_controller_state

    def _pointer_up(self, ev):
        self._last_position = None
        if self._initial_controller_state is not None:
            self._plot_area.controller.enabled = self._initial_controller_state

    def __getitem__(self, graphic: Graphic) -> LegendItem:
        if not isinstance(graphic, Graphic):
            raise TypeError("Must index Legend with Graphics")

        if graphic._fpl_address not in self._items.keys():
            raise KeyError("Graphic not in legend")

        return self._items[graphic._fpl_address]
