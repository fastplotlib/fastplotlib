from typing import *
import numpy as np
from functools import partial

import pygfx
from pygfx.linalg import Vector3

from .._base import Graphic, Interaction
from ..features._base import GraphicFeature, FeatureEvent


# positions for indexing the BoxGeometry to set the "width" and "height" of the box
# hacky but I don't think we can morph meshes in pygfx yet: https://github.com/pygfx/pygfx/issues/346
x_right = np.array([
    True,  True,  True,  True, False, False, False, False, False,
    True, False,  True,  True, False,  True, False, False,  True,
    False,  True,  True, False,  True, False
])

x_left = np.array([
    False, False, False, False,  True,  True,  True,  True,  True,
    False,  True, False, False,  True, False,  True,  True, False,
    True, False, False,  True, False,  True
])

y_top = np.array([
    False,  True, False,  True, False,  True, False,  True,  True,
    True,  True,  True, False, False, False, False, False, False,
    True,  True, False, False,  True,  True
])

y_bottom = np.array([
    True, False,  True, False,  True, False,  True, False, False,
    False, False, False,  True,  True,  True,  True,  True,  True,
    False, False,  True,  True, False, False
])


class LinearBoundsFeature(GraphicFeature):
    def __init__(self, parent, bounds: Tuple[int, int]):
        super(LinearBoundsFeature, self).__init__(parent, data=bounds)

    def _set(self, value):
        # sets new bounds
        if not isinstance(value, tuple):
            raise TypeError(
                "Bounds must be a tuple in the form of `(min_bound, max_bound)`, "
                "where `min_bound` and `max_bound` are numeric values."
            )

        self._parent.fill.geometry.positions.data[x_left, 0] = value[0]
        self._parent.fill.geometry.positions.data[x_right, 0] = value[1]

        self._parent.edges[0].geometry.positions.data[:, 0] = value[0]
        self._parent.edges[1].geometry.positions.data[:, 0] = value[1]

        self._data = (value[0], value[1])

        self._parent.fill.geometry.positions.update_range()

        self._parent.edges[0].geometry.positions.update_range()
        self._parent.edges[1].geometry.positions.update_range()

        self._feature_changed(key=None, new_data=value)

    def _feature_changed(self, key: Union[int, slice, Tuple[slice]], new_data: Any):
        pick_info = {
            "index": None,
            "collection-index": self._collection_index,
            "world_object": self._parent.world_object,
            "new_data": new_data
        }

        event_data = FeatureEvent(type="bounds", pick_info=pick_info)

        self._call_event_handlers(event_data)


class LinearSelector(Graphic, Interaction):
    """Linear region selector, for lines or line collections."""
    feature_events = (
        "bounds"
    )

    def __init__(
            self,
            bounds: Tuple[int, int],
            limits: Tuple[int, int],
            height: int,
            position: Tuple[int, int],
            resizable: bool = False,
            fill_color=(0, 0, 0.5),
            edge_color=(0.8, 0.8, 0),
            name: str = None
    ):
        """

        Parameters
        ----------
        bounds
        limits
        height
        position
        fill_color
        edge_color
        name
        """
        if limits[0] != position[0] != bounds[0]:
            raise ValueError("limits[0] != position[0] != bounds[0]")

        super(LinearSelector, self).__init__(name=name)

        group = pygfx.Group()
        self._set_world_object(group)

        self.fill = pygfx.Mesh(
            pygfx.box_geometry(1, height, 1),
            pygfx.MeshBasicMaterial(color=fill_color)
        )

        self.fill.position.set(*position, -2)

        self.world_object.add(self.fill)

        self._move_info = None

        self.limits = limits

        left_line_data = np.array(
            [[position[0], (-height / 2) + position[1], 0.5],
             [position[0], (height / 2) + position[1], 0.5]]
        ).astype(np.float32)

        left_line = pygfx.Line(
            pygfx.Geometry(positions=left_line_data, colors=np.repeat([pygfx.Color(edge_color)], 2, axis=0)),
            pygfx.LineMaterial(thickness=2, vertex_colors=True)
        )

        right_line_data = np.array(
            [[bounds[1], (-height / 2) + position[1], 0.5],
             [bounds[1], (height / 2) + position[1], 0.5]]
        ).astype(np.float32)

        right_line = pygfx.Line(
            pygfx.Geometry(positions=right_line_data, colors=np.repeat([pygfx.Color(edge_color)], 2, axis=0)),
            pygfx.LineMaterial(thickness=2, vertex_colors=True)
        )

        self.world_object.add(left_line)
        self.world_object.add(right_line)

        self.edges: Tuple[pygfx.Line, pygfx.Line] = (left_line, right_line)

        self.bounds = LinearBoundsFeature(self, bounds)
        self.bounds = bounds

    def _add_plot_area_hook(self, plot_area):
        # called when this selector is added to a plot area
        self._plot_area = plot_area

        self.fill.add_event_handler(self._move_start, "pointer_down")
        self._plot_area.renderer.add_event_handler(self._move, "pointer_move")
        self._plot_area.renderer.add_event_handler(self._move_end, "pointer_up")

    def _move_start(self, ev):
        self._plot_area.controller.enabled = False
        self._move_info = {"last_pos": (ev.x, ev.y)}

    def _move(self, ev):
        if self._move_info is None:
            return

        self._plot_area.controller.enabled = False

        last = self._move_info["last_pos"]

        delta = (last[0] - ev.x, last[1] - ev.y)

        self._move_info = {"last_pos": (ev.x, ev.y)}

        # clip based on the limits
        left_bound = self.bounds()[0] - delta[0]
        right_bound = self.bounds()[1] - delta[0]

        if left_bound <= self.limits[0] or right_bound >= self.limits[1]:
            self._move_end(None)
            return

        # set the new bounds
        self.bounds = (left_bound, right_bound)

        self._plot_area.controller.enabled = True

    def _move_end(self, ev):
        self._move_info = None
        # sometimes weird stuff happens so we want to make sure the controller is reset
        self._plot_area.controller.enabled = True

    def _set_feature(self, feature: str, new_data: Any, indices: Any):
        pass

    def _reset_feature(self, feature: str):
        pass