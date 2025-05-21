from functools import partial
from collections import OrderedDict
from typing import Iterable

import numpy as np
import pygfx

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

        # # for now only support lines with a single color
        # if np.unique(graphic.colors.value, axis=0).shape[0] > 1:
        #     raise ValueError("Use colorbars for multi-colored lines, not legends")

        # color = pygfx.Color(np.unique(graphic.colors.value, axis=0).ravel())

        # handle both per-vertex and uniform colors
        col = graphic.colors
        if hasattr(col, "value"):
            vals = col.value
        else:
            # uniform_color=True → a single pygfx.Color
            vals = np.array([[col.r, col.g, col.b, col.a]], dtype=float)

        if np.unique(vals, axis=0).shape[0] > 1:
            raise ValueError("Use colorbars for multi-colored lines, not legends")

        # pick the unique RGBA row and wrap in a pygfx.Color
        color = pygfx.Color(np.unique(vals, axis=0).ravel())

        self._parent = parent

        super().__init__(label, color)

        graphic.colors.add_event_handler(self._update_color)

        # construct Line WorldObject
        data = np.array([[0, 0, 0], [5, 0, 0]], dtype=np.float32)

        material = pygfx.LineMaterial

        self._line_world_object = pygfx.Line(
            geometry=pygfx.Geometry(positions=data),
            material=material(thickness=4, color=self._color),
        )

        self._label_world_object = pygfx.Text(
            str(label),
            font_size=6,
            screen_space=False,
            anchor="middle-left",
        )
        mat = self._label_world_object.material
        mat.color             = color
        mat.outline_color     = (0,0,0,1)  # or whatever you like
        mat.outline_thickness = 0

        self.world_object = pygfx.Group()
        self.world_object.add(self._line_world_object, self._label_world_object)

        self.world_object.world.x = position[0]
        # add 10 to x to account for space for the line
        self._label_world_object.world.x = position[0] + 10

        self.world_object.world.y = position[1]
        self.world_object.world.z = 2

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

    # def _highlight_graphic(self, graphic: Graphic, ev):
    #     graphic_color = pygfx.Color(np.unique(graphic.colors.value, axis=0).ravel())

    def _highlight_graphic(self, graphic: Graphic, ev):
        # same fallback for uniform vs. per-vertex colors
        col = graphic.colors
        if hasattr(col, "value"):
            vals = col.value
        else:
            vals = np.array([[col.r, col.g, col.b, col.a]], dtype=float)

        graphic_color = pygfx.Color(np.unique(vals, axis=0).ravel())
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
        background_color: str | tuple | np.ndarray = (0.1, 0.1, 0.1, 1.0),
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

        background_color: Union[str, tuple, np.ndarray], default (0.1, 0.1, 0.1, 1.0)
            highlight color

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

        w, h = (30, 10)
        self._mesh = pygfx.Mesh(
            pygfx.box_geometry(w, h, 1),
            pygfx.MeshBasicMaterial(
                color=pygfx.Color(background_color), 
                wireframe_thickness=10
            ),
        )

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

        self._padding = 3

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

        # Prepare column and row indices and positions
        col_idx = self._col_counter
        row_idx = self._row_counter

        if row_idx >= self._max_rows:
            # Start new column
            col_idx += 1

            # Get last column's items
            prev_items = list(self._items.values())[-self._max_rows:]
            # Compute maximum width of that column
            max_width = 0
            for item in prev_items:
                bbox = item.world_object.get_world_bounding_box()
                w, *_ = np.ptp(bbox, axis=0)
                max_width = max(max_width, w)

            x_pos = max_width + 15  # shift new column by that width + spacing
            y_pos = 0
            row_idx = 1
        else:
            # Same column: flush to left
            x_pos = 0
            y_pos = -row_idx * 10   # each row is 10px down
            row_idx += 1

        if isinstance(graphic, LineGraphic):
            legend_item = LineLegendItem(self, 
                graphic, 
                label, 
                position=(x_pos, y_pos)
            )
        else:
            raise ValueError("Legend only supported for LineGraphic for now.")

        self._legend_items_group.add(legend_item.world_object)
        self._reset_mesh_dims()

        self._graphics.append(graphic)
        self._items[graphic._fpl_address] = legend_item

        graphic.add_event_handler(partial(self.remove_graphic, graphic), "deleted")

        self._col_counter = col_idx
        self._row_counter = row_idx

    def _reset_mesh_dims(self):

        # Bounding box of all legend items
        bbox = self._legend_items_group.get_world_bounding_box()
        (left, bottom, _), (right, top, _) = bbox
        # width, height, _ = np.ptp(bbox, axis=0)

        pos = self._mesh.geometry.positions.data
        pos[mesh_masks.x_left]   = left   - self._padding
        pos[mesh_masks.x_right]  = right  + self._padding
        pos[mesh_masks.y_bottom] = bottom - self._padding
        pos[mesh_masks.y_top]    = top    + self._padding
        self._mesh.geometry.positions.update_range()

    def update_using_camera(self):
        """
        Update the legend position and scale using the camera.
        This only works if legend is in a Dock, not a Plot or Subplot.
        """

        # Update Scaling

        # Legend bounding box
        # (legend_left, legend_bottom, _), (legend_right, legend_top, _) = \
        #     self._legend_items_group.get_world_bounding_box()
        # legend_w = legend_right - legend_left
        # legend_h = legend_top   - legend_bottom

        # Panel bounding box
        (panel_left, panel_bottom, _), (panel_right, panel_top, _) = \
            self.world_object.get_world_bounding_box()

        panel_w = panel_right - panel_left
        panel_h = panel_top   - panel_bottom

        # Camera bounding box
        dock = self._plot_area
        state = dock.camera.get_state()
        cam_w, cam_h = state["width"], state["height"]
        cam_x, cam_y = state["position"][:2]

        # Scale the legend to fit the camera
        # Panel dimensions work better 
        scale_x = cam_w / panel_w
        scale_y = cam_h / panel_h
        scale   = min(scale_x, scale_y)
        tf = self.world_object.local
        tf.scale_x *= scale
        tf.scale_y *= scale

        # Used to figure out scaling and position:
        # print(self._legend_items_group.get_world_bounding_box())
        # print(self._mesh.get_world_bounding_box())
        # print(self.world_object.get_world_bounding_box())
        # print(cam_w, cam_h)
        # print(scale_x, scale_y, scale)

        # Update Position

        #   This was hand tuned as the mix of dock size/borders, mesh padding, and legend size
        #   did not yield a simple formula
        wobj = self.world_object.world
        wobj.x = cam_x + panel_left + 6*scale # hand tuned
        wobj.y = cam_y + panel_top  

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
