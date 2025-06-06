from typing import *
from dataclasses import dataclass
from functools import partial

import numpy as np
import pygfx

from pygfx import WorldObject, Line, Mesh, Points

from .._base import Graphic


@dataclass
class MoveInfo:
    """
    stores move info for a WorldObject
    """

    # The initial selection. Differs per type of selector
    start_selection: Any

    # The initial world position of the cursor
    start_position: np.ndarray | None

    # Delta position in world coordinates
    delta: np.ndarray

    # WorldObject or "key" event
    source: WorldObject | str


# key bindings used to move the selector
key_bind_direction = {
    "ArrowRight": np.array([1, 0, 0]),
    "ArrowLeft": np.array([-1, 0, 0]),
    "ArrowUp": np.array([0, 1, 0]),
    "ArrowDown": np.array([0, -1, 0]),
}


# Selector base class
class BaseSelector(Graphic):
    @property
    def axis(self) -> str:
        return self._axis

    @property
    def fill_color(self) -> pygfx.Color:
        """Returns the fill color of the selector, ``None`` if selector has no fill."""
        return self._fill_color

    @fill_color.setter
    def fill_color(self, color: str | Sequence[float]):
        """
        Set the fill color of the selector.

        Parameters
        ----------
        color : str | Sequence[float]
            String or sequence of floats that gets converted into a ``pygfx.Color`` object.
        """
        color = pygfx.Color(color)
        for fill in self._fill:
            fill.material.color = color
            self._original_colors[fill] = color
        self._fill_color = color

    @property
    def vertex_color(self) -> pygfx.Color:
        """Returns the vertex color of the selector, ``None`` if selector has no vertices."""
        return self._vertex_color

    @vertex_color.setter
    def vertex_color(self, color: str | Sequence[float]):
        """
        Set the vertex color of the selector.

        Parameters
        ----------
        color : str | Sequence[float]
            String or sequence of floats that gets converted into a ``pygfx.Color`` object.
        """
        color = pygfx.Color(color)
        for vertex in self._vertices:
            vertex.material.color = color
            vertex.material.edge_color = color
            self._original_colors[vertex] = color
        self._vertex_color = color

    @property
    def edge_color(self) -> pygfx.Color:
        """Returns the edge color of the selector"""
        return self._edge_color

    @edge_color.setter
    def edge_color(self, color: str | Sequence[float]):
        """
        Set the edge color of the selector.

        Parameters
        ----------
        color : str | Sequence[float]
            String or sequence of floats that gets converted into a ``pygfx.Color`` object.
        """
        color = pygfx.Color(color)
        for edge in self._edges:
            edge.material.color = color
            self._original_colors[edge] = color
        self._edge_color = color

    def __init__(
        self,
        edges: Tuple[Line, ...] = None,
        fill: Tuple[Mesh, ...] = None,
        vertices: Tuple[Points, ...] = None,
        hover_responsive: Tuple[WorldObject, ...] = None,
        arrow_keys_modifier: str = None,
        axis: str = None,
        parent: Graphic = None,
        **kwargs,
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

        self._world_objects: Tuple[WorldObject, ...] = (
            self._edges + self._fill + self._vertices
        )

        for wo in self._world_objects:
            wo.material.pick_write = True

        self._hover_responsive: Tuple[WorldObject, ...] = hover_responsive

        # Original color of object that we change the colors of
        self._original_colors = {}

        # Colors as they are changed by the hover events, so they can be restored after a move action
        self._hover_colors = {}

        if hover_responsive is not None:
            for wo in self._hover_responsive:
                self._original_colors[wo] = wo.material.color

        self._axis = axis

        self.arrow_keys_modifier = arrow_keys_modifier
        # if not False, moves the slider on every render cycle
        self._key_move_value = False
        self.step: float = 1.0  #: step size for moving selector using the arrow keys
        self.arrow_key_events_enabled = False

        self._move_info: MoveInfo = None

        # sets to `True` on "pointer_down", sets to `False` on "pointer_up"
        self._moving = False  #: indicates if the selector is currently being moved

        self._initial_controller_state: bool = None

        # used to disable fill area events if the edge is being actively hovered
        # otherwise annoying and requires too much accuracy to move just an edge
        self._edge_hovered: bool = False

        self._pygfx_event = None

        self._parent = parent

        Graphic.__init__(self, **kwargs)

    def get_selected_index(self):
        """Not implemented for this selector"""
        raise NotImplementedError

    def get_selected_indices(self):
        """Not implemented for this selector"""
        raise NotImplementedError

    def get_selected_data(self):
        """Not implemented for this selector"""
        raise NotImplementedError

    def _get_source(self, graphic):
        if self._parent is None and graphic is None:
            raise AttributeError(
                "No Graphic to apply selector. "
                "You must either set a ``parent`` Graphic on the selector, or pass a graphic."
            )

        # use passed graphic if provided, else use parent
        if graphic is not None:
            source = graphic
        else:
            source = self._parent

        return source

    def _fpl_add_plot_area_hook(self, plot_area):
        self._plot_area = plot_area

        # when the pointer is pressed on a fill, edge or vertex
        for wo in self._world_objects:
            pfunc_down = partial(self._move_start, wo)
            wo.add_event_handler(pfunc_down, "pointer_down")

            # double-click to enable arrow-key moveable mode
            wo.add_event_handler(self._toggle_arrow_key_moveable, "double_click")

        for fill in self._fill:
            if fill.material.color_is_transparent:
                self._pfunc_fill = partial(self._check_fill_pointer_event, fill)
                self._plot_area.renderer.add_event_handler(
                    self._pfunc_fill, "pointer_down"
                )

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

    def _check_fill_pointer_event(self, event_source: WorldObject, ev):
        if self._edge_hovered:
            # if edge is hovered, prefer edge events, disable fill moves
            return

        world_pos = self._plot_area.map_screen_to_world(ev)
        # outside viewport, ignore
        # this shouldn't be possible since the event handler is registered to the fill mesh world object
        # but I like sanity checks anyways
        if world_pos is None:
            return

        bbox = event_source.get_world_bounding_box()

        xmin, ymin, zmin = bbox[0]
        xmax, ymax, zmax = bbox[1]

        if not (xmin <= world_pos[0] <= xmax):
            return

        if not (ymin <= world_pos[1] <= ymax):
            return

        self._move_start(event_source, ev)

    def _move_start(self, event_source: WorldObject, ev):
        """
        Called on "pointer_down" events

        Parameters
        ----------
        event_source: WorldObject
            event source, for example selection fill area ``Mesh`` an edge ``Line`` or vertex ``Points``.
            This helps keep the event source within the MoveInfo so that during "pointer_move" events (which are
            from the renderer) we know the original source of the "move action".

        ev: Event
            pygfx ``Event``

        """
        position = self._plot_area.map_screen_to_world(ev)

        self._move_info = MoveInfo(
            start_selection=None,
            start_position=position,
            delta=np.zeros_like(position),
            source=event_source,
        )
        self._moving = True

        self._initial_controller_state = self._plot_area.controller.enabled

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

        # get pointer current world position, in 'mouse capute mode'
        world_pos = self._plot_area.map_screen_to_world(ev, allow_outside=True)

        # update the delta
        self._move_info.delta = world_pos - self._move_info.start_position
        self._pygfx_event = ev

        self._move_graphic(self._move_info)

        # restore the initial controller state
        # if it was disabled, keep it disabled
        self._plot_area.controller.enabled = self._initial_controller_state

    def _move_graphic(self, move_info: MoveInfo):
        raise NotImplementedError("Must be implemented in subclass")

    def _move_end(self, ev):
        self._move_info = None
        self._moving = False

        # Reset hover state
        for wo, color in self._hover_colors.items():
            wo.material.color = color
        self._hover_colors.clear()

        # restore the initial controller state
        # if it was disabled, keep it disabled
        if self._initial_controller_state is not None:
            self._plot_area.controller.enabled = self._initial_controller_state

    def _move_to_pointer(self, ev):
        """
        Calculates delta just using current world object position and calls self._move_graphic().
        """
        # check for middle mouse button click
        if ev.button != 3:
            return

        if self.axis == "x":
            offset = self.offset[0]
        elif self.axis == "y":
            offset = self.offset[1]

        if self.selection.size > 1:
            # linear region selectors
            # TODO: get center for rectangle and polygon selectors
            center = self.selection.mean(axis=0)

        else:
            # linear selectors
            center = self.selection

        current_pos_world: np.ndarray = center + offset

        world_pos = self._plot_area.map_screen_to_world(ev)

        # outside this viewport
        if world_pos is None:
            return

        delta = world_pos - current_pos_world
        self._pygfx_event = ev

        # use fill by default as the source, such as in region selectors
        if len(self._fill) > 0:
            move_info = MoveInfo(
                start_selection=None,
                start_position=None,
                delta=delta,
                source=self._fill[0],
            )
            print(move_info)
        # else use an edge, such as for linear selector
        else:
            move_info = MoveInfo(
                start_position=None,
                start_selection=None,
                delta=delta,
                source=self._edges[0],
            )

        self._move_graphic(move_info)

    def _pointer_enter(self, ev):

        if self._hover_responsive is None:
            return

        wo = ev.pick_info["world_object"]
        if wo not in self._hover_responsive:
            return

        if wo in self._edges:
            self._edge_hovered = True

        if self._moving:
            self._hover_colors[wo] = "magenta"
        else:
            wo.material.color = "magenta"

    def _pointer_leave(self, ev):
        if self._hover_responsive is None:
            return

        self._edge_hovered = False

        # reset colors
        for wo in self._hover_responsive:
            if self._moving:
                self._hover_colors[wo] = self._original_colors[wo]
            else:
                wo.material.color = self._original_colors[wo]

    def _toggle_arrow_key_moveable(self, ev):
        self.arrow_key_events_enabled = not self.arrow_key_events_enabled

    def _key_hold(self):
        if self._key_move_value and self.arrow_key_events_enabled:
            # direction vector * step
            delta = key_bind_direction[self._key_move_value] * self.step

            # set event source
            # use fill by default as the source
            if len(self._fill) > 0:
                move_info = MoveInfo(
                    start_selection=None,
                    start_position=None,
                    delta=delta,
                    source=self._fill[0],
                )
            # else use an edge
            else:
                move_info = MoveInfo(
                    start_selection=None,
                    start_position=None,
                    delta=delta,
                    source=self._edges[0],
                )

            # move the graphic
            self._move_graphic(move_info)

    def _key_down(self, ev):
        # key bind modifier must be set and must be used for the event
        # for example. if "Shift" is set as a modifier, then "Shift" must be used as a modifier during this event
        if (
            self.arrow_keys_modifier is not None
            and self.arrow_keys_modifier not in ev.modifiers
        ):
            return

        # ignore if non-arrow key is pressed
        if ev.key not in key_bind_direction.keys():
            return

        self._key_move_value = ev.key

    def _key_up(self, ev):
        # if arrow key is released, stop moving
        if ev.key in key_bind_direction.keys():
            self._key_move_value = False

    def _fpl_prepare_del(self):
        if hasattr(self, "_pfunc_fill"):
            self._plot_area.renderer.remove_event_handler(
                self._pfunc_fill, "pointer_down"
            )
            del self._pfunc_fill
        super()._fpl_prepare_del()
