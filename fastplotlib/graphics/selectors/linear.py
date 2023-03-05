from typing import *
import numpy as np
from time import time

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
        self._data = (value[0], value[1])

        self._parent.fill.geometry.positions.update_range()

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
            height: int,
            position: Tuple[int, int],
            fill_color=(0.1, 0.1, 0.1),
            edge_color="w",
            name: str = None
    ):
        super(LinearSelector, self).__init__(name=name)

        self._world_object = pygfx.Group()

        self.fill = pygfx.Mesh(
            pygfx.box_geometry(1, height, 1),
            pygfx.MeshBasicMaterial(color=fill_color)
        )

        self.fill.position.set(*position, -2)

        self.fill.add_event_handler(self._move_start, "double_click")
        self.fill.add_event_handler(self._move, "pointer_move")
        self.fill.add_event_handler(self._move_end, "click")

        self.world_object.add(self.fill)

        self._move_info = None
        # self.fill.add_event_handler(

        self.edges = None

        self.bounds = LinearBoundsFeature(self, bounds)
        self.bounds = bounds
        self.timer = 0

        # self._plane =

    def _move_start(self, ev):
        self._move_info = {"last_pos": (ev.x, ev.y)}
        self.timer = time()
        print(self._move_info)

    def _move(self, ev):
        if self._move_info is None:
            return

        if time() - self.timer > 2:
            self._move_end(ev)
            return

        print("moving!")
        print(ev.x, ev.y)

        last = self._move_info["last_pos"]

        delta = (last[0] - ev.x, last[1] - ev.y)

        self._move_info = {"last_pos": (ev.x, ev.y)}

        # adjust x vals
        self.bounds = (self.bounds()[0] - delta[0], self.bounds()[1] - delta[0])

        print(self._move_info)

        self.timer = time()

    def _move_end(self, ev):
        print("move end")
        self._move_info = None

    def _set_feature(self, feature: str, new_data: Any, indices: Any):
        pass

    def _reset_feature(self, feature: str):
        pass