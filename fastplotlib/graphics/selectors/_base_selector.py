from typing import *
from dataclasses import dataclass
from functools import partial

from pygfx.linalg import Vector3
from pygfx import WorldObject, Line, Mesh, Points


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
            edges: Tuple[Line, ...] = None,
            fill: Tuple[Mesh, ...] = None,
            vertices: Tuple[Points, ...] = None,
            hover_responsive: Tuple[WorldObject, ...] = None,
            arrow_keys_modifier: str = None,
            axis: str = None
    ):
        if edges is None:
            edges = tuple()

        if fill is None:
            fill = tuple()

        if vertices is None:
            vertices = tuple()

        self._edges: Tuple[Line, ...] = edges
        self._fill: Tuple[Mesh, ...] = fill
        self._vertices: Tuple[Points, ...] = vertices

        self._world_objects: Tuple[WorldObject, ...] = self._edges + self._fill + self._vertices

        self._hover_responsive: Tuple[WorldObject, ...] = hover_responsive

        if hover_responsive is not None:
            self._original_colors = dict()
            for wo in self._hover_responsive:
                self._original_colors[wo] = wo.material.color

        self.axis = axis

        # current delta in world coordinates
        self.delta: Vector3 = None

        self.arrow_keys_modifier = arrow_keys_modifier
        # if not False, moves the slider on every render cycle
        self._key_move_value = False
        self.step: float = 1.0  #: step size for moving selector using the arrow keys
        self.arrow_key_events_enabled = False

        self._move_info: MoveInfo = None

    def get_selected_index(self):
        raise NotImplementedError

    def get_selected_indices(self):
        raise NotImplementedError

    def get_selected_data(self):
        raise NotImplementedError

    def _get_source(self, graphic):
        if self.parent is None and graphic is None:
            raise AttributeError(
                "No Graphic to apply selector. "
                "You must either set a ``parent`` Graphic on the selector, or pass a graphic."
            )

        # use passed graphic if provided, else use parent
        if graphic is not None:
            source = graphic
        else:
            source = self.parent

        return source

    def _add_plot_area_hook(self, plot_area):
        self._plot_area = plot_area

        # when the pointer is pressed on a fill, edge or vertex
        for wo in self._world_objects:
            pfunc_down = partial(self._move_start, wo)
            wo.add_event_handler(pfunc_down, "pointer_down")

            # double-click to enable arrow-key moveable mode
            wo.add_event_handler(self._toggle_arrow_key_moveable, "double_click")

        # when the pointer moves
        self._plot_area.renderer.add_event_handler(self._move, "pointer_move")

        # when the pointer is released
        self._plot_area.renderer.add_event_handler(self._move_end, "pointer_up")

        # move directly to location of center mouse button click
        self._plot_area.renderer.add_event_handler(self._move_to_pointer, "click")

        # mouse hover color events
        for wo in self._hover_responsive:
            wo.add_event_handler(self._pointer_enter, "pointer_enter")
            wo.add_event_handler(self._pointer_leave, "pointer_leave")

        # arrow key bindings
        self._plot_area.renderer.add_event_handler(self._key_down, "key_down")
        self._plot_area.renderer.add_event_handler(self._key_up, "key_up")
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

        self._move_graphic(self.delta, ev)

        # update last position
        self._move_info.last_position = world_pos

        self._plot_area.controller.enabled = True

    def _move_graphic(self, delta, ev):
        raise NotImplementedError("Must be implemented in subclass")

    def _move_end(self, ev):
        self._move_info = None
        self._plot_area.controller.enabled = True

    def _move_to_pointer(self, ev):
        """
        Calculates delta just using current world object position and calls self._move_graphic().
        """
        current_position = self.world_object.position.clone()

        # middle mouse button clicks
        if ev.button != 3:
            return

        click_pos = (ev.x, ev.y)
        world_pos = self._plot_area.map_screen_to_world(click_pos)

        # outside this viewport
        if world_pos is None:
            return

        self.delta = world_pos.clone().sub(current_position)
        self._pygfx_event = ev

        # use fill by default as the source
        if len(self._fill) > 0:
            self._move_info = MoveInfo(last_position=current_position, source=self._fill[0])
        # else use an edge
        else:
            self._move_info = MoveInfo(last_position=current_position, source=self._edges[0])

        self._move_graphic(self.delta, ev)
        self._move_info = None

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

    def _toggle_arrow_key_moveable(self, ev):
        self.arrow_key_events_enabled = not self.arrow_key_events_enabled

    def _key_hold(self):
        if self._key_move_value and self.arrow_key_events_enabled:
            # direction vector * step
            delta = key_bind_direction[self._key_move_value].clone().multiply_scalar(self.step)

            # set event source
            # use fill by default as the source
            if len(self._fill) > 0:
                self._move_info = MoveInfo(last_position=None, source=self._fill[0])
            # else use an edge
            else:
                self._move_info = MoveInfo(last_position=None, source=self._edges[0])

            # move the graphic
            self._move_graphic(delta=delta, ev=None)

            self._move_info = None

    def _key_down(self, ev):
        # key bind modifier must be set and must be used for the event
        # for example. if "Shift" is set as a modifier, then "Shift" must be used as a modifier during this event
        if self.arrow_keys_modifier is not None and self.arrow_keys_modifier not in ev.modifiers:
            return

        # ignore if non-arrow key is pressed
        if ev.key not in key_bind_direction.keys():
            return

        # print(ev.key)

        self._key_move_value = ev.key

    def _key_up(self, ev):
        # if arrow key is released, stop moving
        if ev.key in key_bind_direction.keys():
            self._key_move_value = False

        self._move_info = None

    def __del__(self):
        # clear wo event handlers
        for wo in self._world_objects:
            wo._event_handlers.clear()

        # remove renderer event handlers
        self._plot_area.renderer.remove_event_handler(self._move, "pointer_move")
        self._plot_area.renderer.remove_event_handler(self._move_end, "pointer_up")
        self._plot_area.renderer.remove_event_handler(self._move_to_pointer, "click")

        self._plot_area.renderer.remove_event_handler(self._key_down, "key_down")
        self._plot_area.renderer.remove_event_handler(self._key_up, "key_up")

        # remove animation func
        self._plot_area.remove_animation(self._key_hold)