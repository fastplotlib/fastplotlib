from typing import *
from dataclasses import dataclass
from functools import partial

import numpy as np

import pygfx
from pygfx.linalg import Vector3
from pygfx import WorldObject, Line, Mesh, Points

from .._base import Graphic


@dataclass
class MoveInfo:
    """
    stores move info for a WorldObject
    """

    # last position for an edge, fill, or vertex in world coordinates
    # can be None, such as key events
    last_position: Vector3 | None

    # WorldObject or "key" event
    source: WorldObject | str


# key bindings used to move the selector
key_bind_direction = {
    "ArrowRight": Vector3(1, 0, 0),
    "ArrowLeft": Vector3(-1, 0, 0),
    "ArrowUp": Vector3(0, 1, 0),
    "ArrowDown": Vector3(0, -1, 0),
}


# Selector base class
class BaseSelector:
    def __init__(
            self,
            edges: List[Line] = None,
            vertices: List[Line] = None,
            fill: List[Points] = None,
            hover_responsive: List[WorldObject] = None,
            axis_constraint: str = None
    ):
        if edges is None:
            edges = list()

        if fill is None:
            fill = list()

        if vertices is None:
            vertices = list()

        self._edges: List[Line] = edges
        self._fill: List[Mesh] = fill
        self._vertices: List[Points] = vertices

        self._world_objects: List[WorldObject] = self._edges + self._fill + self._vertices

        self._hover_responsive: List[WorldObject] = hover_responsive

        if hover_responsive is not None:
            self._original_colors = dict()
            for wo in self._hover_responsive:
                self._original_colors[wo] = wo.material.color

        self.axis_constraint = axis_constraint

        # current delta in world coordinates
        self.delta: Vector3 = None

        self._key_move_value = False

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

        # when the pointer is pressed on a fill, edge or vertex
        for wo in self._world_objects:
            pfunc_down = partial(self._move_start, wo)
            wo.add_event_handler(pfunc_down, "pointer_down")

        # when the pointer moves
        self._plot_area.renderer.add_event_handler(self._move, "pointer_move")

        # when the pointer is released
        self._plot_area.renderer.add_event_handler(self._move_end, "pointer_up")

        # move directly to location of center mouse button click
        # check if _move_to_pointer is implemented or not
        kh = getattr(self, "_move_to_pointer")
        if not kh.__qualname__.partition(".")[0] == "BaseSelector":
            self._plot_area.renderer.add_event_handler(self._move_to_pointer, "click")

        # mouse hover color events
        for wo in self._hover_responsive:
            wo.add_event_handler(self._pointer_enter, "pointer_enter")
            wo.add_event_handler(self._pointer_leave, "pointer_leave")

        # arrow key bindings
        self._plot_area.renderer.add_event_handler(self._key_down, "key_down")
        self._plot_area.renderer.add_event_handler(self._key_up, "key_up")

        # check if _key_hold is implemented or not
        kh = getattr(self, "_key_hold")
        if not kh.__qualname__.partition(".")[0] == "BaseSelector":
            self._plot_area.add_animations(self._key_hold)

    def _move_start(self, event_source: WorldObject, ev):
        """
        Called on "pointer_down" events

        Parameters
        ----------
        event_source: WorldObject
            event source, for example selection fill area ``Mesh`` an edge ``Line`` or vertex ``Points``

        ev: Event
            pygfx ``Event``

        """
        last_position = self._plot_area.map_screen_to_world((ev.x, ev.y))

        self._move_info = MoveInfo(
            last_position=last_position,
            source=event_source
        )

    def _move(self, ev):
        """
        Called on pointer move events

        Parameters
        ----------
        ev

        Returns
        -------

        """
        if self._move_info is None:
            return

        # disable controller during moves
        self._plot_area.controller.enabled = False

        # get pointer current world position
        pointer_pos_screen = (ev.x, ev.y)
        world_pos = self._plot_area.map_screen_to_world(pointer_pos_screen)

        # outside this viewport
        if world_pos is None:
            return

        # compute the delta
        self.delta = world_pos.clone().sub(self._move_info.last_position)
        self._pygfx_event = ev

        self._move_graphic(self.delta)

        # update last position
        self._move_info.last_position = world_pos

        self._plot_area.controller.enabled = True

    def _move_graphic(self, delta):
        raise NotImplementedError("Must be implemented in subclass")

    def _move_end(self, ev):
        self._move_info = None
        self._plot_area.controller.enabled = True

    def _move_to_pointer(self):
        raise NotImplementedError("Must be implemented in subclass")

    def _pointer_enter(self, ev):
        if self._hover_responsive is None:
            return

        wo = ev.pick_info["world_object"]
        if wo not in self._hover_responsive:
            return

        wo.material.color = "magenta"

    def _pointer_leave(self, ev):
        if self._hover_responsive is None:
            return

        # reset colors
        for wo in self._hover_responsive:
            wo.material.color = self._original_colors[wo]

    def _key_hold(self):
        if self._key_move_value:
            # direction vector * step
            delta = key_bind_direction[self._key_move_value].multiply(self.step)

            # set event source
            self._move_info = MoveInfo(
                last_position=None,
                source="key"
            )
            # move the graphic
            self._move_graphic(delta=delta)

    def _key_down(self, ev):
        # key bind modifier must be set and must be used for the event
        # for example. if "Shift" is set as a modifier, then "Shift" must be used as a modifier during this event
        if self.key_bind_modifier is not None and self.key_bind_modifier not in ev.modifiers:
            return

        # ignore if non-arrow key is pressed
        if ev.key not in key_bind_direction.keys():
            return

        self._key_move_value = ev.key

    def _key_up(self, ev):
        # if arrow key is released, stop moving
        if ev.key in key_bind_direction.keys():
            self._key_move_value = False