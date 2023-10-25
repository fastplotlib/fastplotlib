from typing import *

import numpy as np

import pygfx

from ._base_selector import BaseSelector, MoveInfo
from .._base import Graphic
from ...utils import make_pygfx_colors


class Segment(pygfx.Group):
    def __init__(self, endpoints: Tuple[np.ndarray, np.ndarray], width):
        self._endpoints = np.array(endpoints).astype(np.float32)

        self._width = width

        self.line = pygfx.Line(
            geometry=pygfx.Geometry(positions=self.endpoints),
            material=pygfx.LineMaterial(thickness=self._width, color="magenta")
        )

        colors = make_pygfx_colors("magenta", 2)

        self.vertices = pygfx.Points(
            geometry=pygfx.Geometry(positions=self.endpoints, colors=colors),
            material=pygfx.PointsMaterial(color_mode="vertex", size=self._width * 4)
        )

        super().__init__(visible=True)

        self.add(self.line, self.vertices)

    @property
    def endpoints(self) -> np.ndarray:
        return self._endpoints

    @endpoints.setter
    def endpoints(self, endpoints: np.ndarray):
        self._endpoints = endpoints

        self.line.geometry.positions.data[:] = self._endpoints
        self.vertices.geometry.positions.data[:] = self._endpoints

        self.line.geometry.positions.update_range()
        self.vertices.geometry.positions.update_range()

    def highlight_vertex(self, ev):
        index = ev.pick_info["vertex_index"]
        self.vertices.geometry.colors.data[index] = make_pygfx_colors("cyan", 1)
        self.vertices.geometry.colors.update_range(offset=index, size=1)

    def unhighlight_vertex(self, ev):
        self.vertices.geometry.colors.data[:] = make_pygfx_colors("magenta", 2)
        self.vertices.geometry.colors.update_range()

    def highlight_line(self, ev):
        self.line.material.color = "w"
        self.line.material.thickness = self._width * 1.5

    def unhighlight_line(self, ev):
        self.line.material.color = "magenta"
        self.line.material.thickness = self._width


class PolygonSelector(Graphic, BaseSelector):
    def __init__(
            self,
            edge_color="magenta",
            edge_width: float = 3,
            parent: Graphic = None,
            name: str = None,
    ):
        Graphic.__init__(self, name=name)

        self.parent = parent

        group = pygfx.Group()

        self._set_world_object(group)

        self._segments: List[Segment] = list()

        self.edge_color = edge_color
        self.edge_width = edge_width

        self._move_info: MoveInfo = None

        self._current_mode = None

        # used when vertices are being moved after the polygon has been drawn
        self._current_vertex = None

    def get_vertices(self) -> np.ndarray:
        """Get the vertices for the polygon"""
        vertices = list()
        for segment in self._segments:
            # only add the first point because the second point will be in the next segment
            vertices.append(segment.endpoints[0])

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

    def _start_move_vertex(self, ev):
        self._current_mode = "move_vertex"
        self._current_vertex = ev.pick_info["world_object"]
        self._current_vertex_index = ev.pick_info["vertex_index"]

        self._plot_area.controller.enabled = False

    def _move_vertex(self, ev):
        if not self._current_mode == "move_vertex":
            return

        vertex_index = self._current_vertex_index

        segment = self._current_vertex.parent
        segment_index = self._segments.index(segment)

        # get new position in world coordinates
        world_pos = self._plot_area.map_screen_to_world(ev)

        # set new position
        if vertex_index == 1:
            v0 = segment.endpoints[0]
            v1 = np.array([world_pos]).astype(np.float32)

        elif vertex_index == 0:
            v0 = np.array([world_pos]).astype(np.float32)
            v1 = segment.endpoints[1]

        segment.endpoints = np.vstack((v0, v1))

        # we need to adjust the adjacent segment too based on
        # whether this is the 0th or 1st vertex index of the segment
        if vertex_index == 0:
            # change previous segment
            adjacent_segment = self._segments[segment_index - 1]

            # vertex_0 of this segment is vertex_1 of previous segment
            v1 = v0
            v0 = adjacent_segment.endpoints[0]

        elif vertex_index == 1:
            # change next segment
            if segment == self._segments[-1]:
                # if it's the last segment, loop back to first one which is the "next" segment
                adjacent_segment = self._segments[0]
            else:
                adjacent_segment = self._segments[segment_index + 1]

            # vertex_1 of this segment is vertex_0 of next segment
            v0 = v1
            v1 = adjacent_segment.endpoints[1]

        adjacent_segment.endpoints = np.vstack((v0, v1))

    def _end_move_vertex(self, ev):
        print("pointer up")
        self._plot_area.controller.enabled = True
        self._current_mode = None

    def _move_polygon(self, ev):
        pass

    def _add_segment(self, ev):
        """After click event, adds a new line segment"""
        self._current_mode = "add"

        last_position = self._plot_area.map_screen_to_world(ev)
        self._move_info = MoveInfo(last_position=last_position, source=None)

        # line with same position for start and end until mouse moves
        segment = Segment(endpoints=(last_position, last_position), width=self.edge_width)

        self._setup_segment_events(segment)

        self._segments.append(segment)

        self.world_object.add(segment)

    def _setup_segment_events(self, segment):
        # mouse wheel click to remove segment
        segment.line.add_event_handler(self._remove_segment, "click")

        segment.line.add_event_handler(segment.highlight_line, "pointer_enter")
        segment.line.add_event_handler(segment.unhighlight_line, "pointer_leave")

        segment.vertices.add_event_handler(segment.highlight_vertex, "pointer_enter")
        segment.vertices.add_event_handler(segment.unhighlight_vertex, "pointer_leave")

    def _remove_segment(self, ev):
        # check for middle mouse button click
        if ev.button != 3:
            return

        print(ev)
        print(ev.pick_info)

        if not isinstance(ev.pick_info["world_object"], pygfx.Line):
            return

        if len(self._segments) < 4:
            # this means we currently have only 3 segments, a triangle
            # cannot form a polygon with only 2 segments, so delete the entire polygon
            # TODO: Not sure if this will actually work
            self._plot_area.remove_graphic(self)

    def _move_segment_endpoint(self, ev):
        """After mouse pointer move event, moves endpoint of current line segment"""
        if self._move_info is None:
            return
        self._current_mode = "move"

        world_pos = self._plot_area.map_screen_to_world(ev)

        if world_pos is None:
            return

        # change endpoint of currently-being-drawn segment
        segment: Segment = self._segments[-1]
        v0 = segment.endpoints[0]
        v1 = np.array([world_pos]).astype(np.float32)
        segment.endpoints = np.vstack((v0, v1))

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
            self._segments[0].endpoints[0]
        ])

        final_segment = Segment(data, width=self.edge_width)
        self._setup_segment_events(final_segment)
        self._segments.append(final_segment)

        self.world_object.add(final_segment)

        handlers = {
            self._add_segment: "click",
            self._move_segment_endpoint: "pointer_move",
            self._finish_segment: "click",
            self._finish_polygon: "double_click"
        }

        for handler, event in handlers.items():
            self._plot_area.renderer.remove_event_handler(handler, event)

        for segment in self._segments:
            segment.vertices.add_event_handler(self._start_move_vertex, "pointer_down")
            self._plot_area.renderer.add_event_handler(self._move_vertex, "pointer_move")
            self._plot_area.renderer.add_event_handler(self._end_move_vertex, "pointer_up")
