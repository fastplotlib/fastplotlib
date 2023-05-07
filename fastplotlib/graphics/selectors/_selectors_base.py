from typing import *
from .._base import Graphic

from pygfx.linalg import Vector3


# Selector base class
class BaseSelector(Graphic):
    def get_selected_index(self):
        pass

    def get_selected_indices(self):
        pass

    def get_selected_data(self):
        pass

    def _get_source(self):
        pass

    def _add_plot_area_hook(self, plot_area):
        self._plot_area = plot_area

        # move events
        self.world_object.add_event_handler(self._move_start, "pointer_down")
        self._plot_area.renderer.add_event_handler(self._move, "pointer_move")
        self._plot_area.renderer.add_event_handler(self._move_end, "pointer_up")

        # move directly to location of center mouse button click
        # check if _move_to_pointer is implemented or not
        kh = getattr(self, "_key_hold")
        if not kh.__qualname__.partition(".")[0] == "BaseSelector":
            self._plot_area.renderer.add_event_handler(self._move_to_pointer, "click")

        # mouse hover color events
        self.world_object.add_event_handler(self._pointer_enter, "pointer_enter")
        self.world_object.add_event_handler(self._pointer_leave, "pointer_leave")

        # arrow key bindings
        self._plot_area.renderer.add_event_handler(self._key_down, "key_down")
        self._plot_area.renderer.add_event_handler(self._key_up, "key_up")

        # check if _key_hold is implemented or not
        kh = getattr(self, "_key_hold")
        if not kh.__qualname__.partition(".")[0] == "BaseSelector":
            self._plot_area.add_animations(self._key_hold)

    def _move_start(self):
        pass

    def get_move_vector(self, ev):
        if self._move_info is None:
            return

        last = self._move_info["last_pos"]

        # new - last
        # pointer move events are in viewport or canvas space
        delta = Vector3(ev.x - last[0], ev.y - last[1])

        self._pygfx_event = ev

        self._move_graphic(delta)

        self._move_info = {"last_pos": (ev.x, ev.y)}
        self._plot_area.controller.enabled = True

    def _move(self):
        pass

    def _move_graphic(self, delta):
        self.delta = delta.clone()

        viewport_size = self._plot_area.viewport.logical_size

        # convert delta to NDC coordinates using viewport size
        # also since these are just deltas we don't have to calculate positions relative to the viewport
        delta_ndc = delta.clone().multiply(
            Vector3(
                2 / viewport_size[0],
                -2 / viewport_size[1],
                0
            )
        )

        camera = self._plot_area.camera

        # current world position
        vec = self.position.clone()

        # compute and add delta in projected NDC space and then unproject back to world space
        vec.project(camera).add(delta_ndc).unproject(camera)

        # TODO: think about this a bi tmore
        new_value = getattr(vec, self.axis)

        if new_value < self.limits[0] or new_value > self.limits[1]:
            return

    def _move_end(self):
        pass

    def _move_to_pointer(self):
        pass

    def _pointer_enter(self):
        pass

    def _pointer_leave(self):
        pass

    def _key_down(self):
        pass

    def _key_hold(self):
        pass

    def _key_up(self):
        pass
