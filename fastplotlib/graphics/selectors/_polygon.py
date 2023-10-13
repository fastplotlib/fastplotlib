from typing import *

import numpy as np

import pygfx

from ._base_selector import BaseSelector, MoveInfo
from .._base import Graphic


class PolygonSelector(BaseSelector):
    def __init__(
        self,
        edge_color="magenta",
        edge_width: float = 3,
        parent: Graphic = None,
        name: str = None,
    ):

        self.parent = parent

        group = pygfx.Group()

        self._set_world_object(group)

        self.edge_color = edge_color
        self.edge_width = edge_width

        self._move_info: MoveInfo = None

        self._current_mode = None

        BaseSelector.__init__(self, name=name)

    def get_vertices(self) -> np.ndarray:
        """Get the vertices for the polygon"""
        vertices = list()
        for child in self.world_object.children:
            vertices.append(child.geometry.positions.data[:, :2])

        return np.vstack(vertices)

    def _add_plot_area_hook(self, plot_area):
        self._plot_area = plot_area

        # click to add new segment
        self._plot_area.renderer.add_event_handler(self._add_segment, "click")

        # pointer move to change endpoint of segment
        self._plot_area.renderer.add_event_handler(self._move_segment_endpoint, "pointer_move")

        # click to finish existing segment
        self._plot_area.renderer.add_event_handler(self._finish_segment, "click")

        # double click to finish polygon
        self._plot_area.renderer.add_event_handler(self._finish_polygon, "double_click")

        self.position_z = len(self._plot_area) + 10

    def _add_segment(self, ev):
        """After click event, adds a new line segment"""
        self._current_mode = "add"

        last_position = self._plot_area.map_screen_to_world(ev)
        self._move_info = MoveInfo(last_position=last_position, source=None)

        # line with same position for start and end until mouse moves
        data = np.array([last_position, last_position])

        new_line = pygfx.Line(
            geometry=pygfx.Geometry(positions=data.astype(np.float32)),
            material=pygfx.LineMaterial(thickness=self.edge_width, color=pygfx.Color(self.edge_color))
        )

        self.world_object.add(new_line)

    def _move_segment_endpoint(self, ev):
        """After mouse pointer move event, moves endpoint of current line segment"""
        if self._move_info is None:
            return
        self._current_mode = "move"

        world_pos = self._plot_area.map_screen_to_world(ev)

        if world_pos is None:
            return

        # change endpoint
        self.world_object.children[-1].geometry.positions.data[1] = np.array([world_pos]).astype(np.float32)
        self.world_object.children[-1].geometry.positions.update_range()

    def _finish_segment(self, ev):
        """After click event, ends a line segment"""
        # should start a new segment
        if self._move_info is None:
            return

        # since both _add_segment and _finish_segment use the "click" callback
        # this is to block _finish_segment right after a _add_segment call
        if self._current_mode == "add":
            return

        # just make move info None so that _move_segment_endpoint is not called
        # and _add_segment gets triggered for "click"
        self._move_info = None

        self._current_mode = "finish-segment"

    def _finish_polygon(self, ev):
        """finishes the polygon, disconnects events"""
        world_pos = self._plot_area.map_screen_to_world(ev)

        if world_pos is None:
            return

        # make new line to connect first and last vertices
        data = np.vstack([
            world_pos,
            self.world_object.children[0].geometry.positions.data[0]
        ])

        new_line = pygfx.Line(
            geometry=pygfx.Geometry(positions=data.astype(np.float32)),
            material=pygfx.LineMaterial(thickness=self.edge_width, color=pygfx.Color(self.edge_color))
        )

        self.world_object.add(new_line)

        handlers = {
            self._add_segment: "click",
            self._move_segment_endpoint: "pointer_move",
            self._finish_segment: "click",
            self._finish_polygon: "double_click"
        }

        for handler, event in handlers.items():
            self._plot_area.renderer.remove_event_handler(handler, event)
