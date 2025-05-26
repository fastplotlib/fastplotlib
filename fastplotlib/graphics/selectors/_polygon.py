from typing import *

from numbers import Real

import numpy as np
import pygfx

from .._base import Graphic
from .._collection_base import GraphicCollection
from ..features._selection_features import PolygonSelectionFeature
from ._base_selector import BaseSelector, MoveInfo


class PolygonSelector(BaseSelector):
    _features = {"selection": PolygonSelectionFeature}

    @property
    def parent(self) -> Graphic | None:
        """Graphic that selector is associated with."""
        return self._parent

    @property
    def selection(self) -> np.ndarray[float]:
        """
        The polygon as an array of 3D points.
        """
        return self._selection.value.copy()

    @selection.setter
    def selection(self, selection: np.ndarray[float]):
        # set (xmin, xmax, ymin, ymax) of the selector in data space
        graphic = self._parent

        if isinstance(graphic, GraphicCollection):
            pass

        self._selection.set_value(self, selection)

    @property
    def limits(self) -> Tuple[float, float, float, float]:
        """Return the limits of the selector."""
        return self._limits

    @limits.setter
    def limits(self, values: Tuple[float, float, float, float]):
        if len(values) != 4 or not all(map(lambda v: isinstance(v, Real), values)):
            raise TypeError("limits must be an iterable of two numeric values")
        self._limits = tuple(
            map(round, values)
        )  # if values are close to zero things get weird so round them
        self._selection._limits = self._limits

    def __init__(
        self,
        edge_color="magenta",
        edge_thickness: float = 4,
        parent: Graphic = None,
        name: str = None,
    ):
        self._parent = parent
        self._move_info: MoveInfo = None
        self._current_mode = None

        BaseSelector.__init__(self, name=name, parent=parent)

        self.geometry = pygfx.Geometry(
            positions=np.zeros((8, 3), np.float32),
            indices=np.zeros((8, 3), np.int32),
        )
        self.geometry.positions.draw_range = 0, 0
        self.geometry.indices.draw_range = 0, 0

        edge = pygfx.Line(
            self.geometry,
            pygfx.LineMaterial(thickness=edge_thickness, color=edge_color),
        )
        points = pygfx.Points(
            self.geometry,
            pygfx.PointsMaterial(size=edge_thickness * 2, color=edge_color),
        )
        mesh = pygfx.Mesh(
            self.geometry, pygfx.MeshBasicMaterial(color=edge_color, opacity=0.2)
        )
        group = pygfx.Group().add(edge, points, mesh)
        self._set_world_object(group)

        self._selection = PolygonSelectionFeature([], [0, 0, 0, 0])

        self.edge_color = edge_color
        self.edge_width = edge_thickness

    def get_selected_indices(self):
        return []

    def _fpl_add_plot_area_hook(self, plot_area):
        self._plot_area = plot_area

        self._plot_area.controller.enabled = False

        # click to add new segment
        self._plot_area.renderer.add_event_handler(self._finish_segment, "click")

        # pointer move to change endpoint of segment
        self._plot_area.renderer.add_event_handler(
            self._move_segment_endpoint, "pointer_move"
        )
        # double click to finish polygon
        self._plot_area.renderer.add_event_handler(self._finish_polygon, "double_click")

        self.position_z = len(self._plot_area) + 10

    def _finish_segment(self, ev):
        """After click event, adds a new line segment"""

        # Don't add two points at the same spot
        if self._current_mode == "add":
            return
        self._current_mode = "add"

        position = self._plot_area.map_screen_to_world(ev)
        self._move_info = MoveInfo(
            start_selection=None,
            start_position=position,
            delta=np.zeros_like(position),
            source=None,
        )

        # line with same position for start and end until mouse moves
        data = np.vstack([self.selection, position])

        self._selection.set_value(self, data)

    def _move_segment_endpoint(self, ev):
        """After mouse pointer move event, moves endpoint of current line segment"""
        if self._move_info is None:
            return
        self._current_mode = "move"

        world_pos = self._plot_area.map_screen_to_world(ev)

        if world_pos is None:
            return

        # change endpoint
        data = self.selection
        data[-1] = world_pos
        self._selection.set_value(self, data)

    def _finish_polygon(self, ev):
        """finishes the polygon, disconnects events"""
        world_pos = self._plot_area.map_screen_to_world(ev)

        if world_pos is None:
            return

        # close the loop
        self.world_object.children[0].material.loop = True

        self._plot_area.controller.enabled = True

        handlers = {
            self._finish_segment: "click",
            self._move_segment_endpoint: "pointer_move",
            self._finish_polygon: "double_click",
        }

        for handler, event in handlers.items():
            self._plot_area.renderer.remove_event_handler(handler, event)
