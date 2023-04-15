from typing import *
import numpy as np
from functools import partial

import pygfx
from pygfx.linalg import Vector3

from .._base import Graphic, Interaction, GraphicCollection
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


class _LinearBoundsFeature(GraphicFeature):
    """Feature for a linear bounding region"""
    def __init__(self, parent, bounds: Tuple[int, int]):
        # int so we can use these as slice indices for other purposes
        bounds = tuple(map(int, bounds))
        super(_LinearBoundsFeature, self).__init__(parent, data=bounds)

    def _set(self, value):
        # sets new bounds
        if not isinstance(value, tuple):
            raise TypeError(
                "Bounds must be a tuple in the form of `(min_bound, max_bound)`, "
                "where `min_bound` and `max_bound` are numeric values."
            )

        # int so we can use these as slice indices for other purposes
        value = tuple(map(int, value))

        # change left x position of the fill mesh
        self._parent.fill.geometry.positions.data[x_left, 0] = value[0]

        # change right x position of the fill mesh
        self._parent.fill.geometry.positions.data[x_right, 0] = value[1]

        # change  position of the left edge line
        self._parent.edges[0].geometry.positions.data[:, 0] = value[0]

        # change  position of the right edge line
        self._parent.edges[1].geometry.positions.data[:, 0] = value[1]

        self._data = (value[0], value[1])

        # send changes to GPU
        self._parent.fill.geometry.positions.update_range()

        self._parent.edges[0].geometry.positions.update_range()
        self._parent.edges[1].geometry.positions.update_range()

        # calls any events
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
    feature_events = (
        "bounds"
    )

    def __init__(
            self,
            bounds: Tuple[int, int],
            limits: Tuple[int, int],
            height: int,
            position: Tuple[int, int],
            parent: Graphic = None,
            resizable: bool = False,
            fill_color=(0, 0, 0.35),
            edge_color=(0.8, 0.8, 0),
            name: str = None
    ):
        """
        Create a LinearSelector graphic which can be moved only along the x-axis. Useful for sub-selecting
        data on Line graphics.

        bounds[0], limits[0], and position[0] must be identical

        Parameters
        ----------
        bounds: (int, int)
            the initial bounds of the linear selector

        limits: (int, int)
            (min limit, max limit) for the selector

        height: int
            height of the selector

        position: (int, int)
            initial position of the selector

        resizable: bool
            if ``True``, the edges can be dragged to resize the width of the linear selection

        fill_color: str, array, or tuple
            fill color for the selector, passed to pygfx.Color

        edge_color: str, array, or tuple
            edge color for the selector, passed to pygfx.Color

        name: str
            name for this selector graphic
        """

        if limits[0] != position[0] != bounds[0]:
            raise ValueError("limits[0] != position[0] != bounds[0]")

        super(LinearSelector, self).__init__(name=name)

        self.parent = parent

        # world object for this will be a group
        # basic mesh for the fill area of the selector
        # line for each edge of the selector
        group = pygfx.Group()
        self._set_world_object(group)

        # the fill of the selection
        self.fill = pygfx.Mesh(
            pygfx.box_geometry(1, height, 1),
            pygfx.MeshBasicMaterial(color=pygfx.Color(fill_color))
        )

        self.fill.position.set(*position, -2)

        self.world_object.add(self.fill)

        # will be used to store the mouse pointer x y movements
        # so deltas can be calculated for interacting with the selection
        self._move_info = None

        # mouse events can come from either the fill mesh world object, or one of the lines on the edge of the selector
        self._event_source: str = None

        self.limits = limits
        self._resizable = resizable

        self._edge_color = np.repeat([pygfx.Color(edge_color)], 2, axis=0)

        # position data for the left edge line
        left_line_data = np.array(
            [[position[0], (-height / 2) + position[1], 0.5],
             [position[0], (height / 2) + position[1], 0.5]]
        ).astype(np.float32)

        left_line = pygfx.Line(
            pygfx.Geometry(positions=left_line_data, colors=self._edge_color.copy()),
            pygfx.LineMaterial(thickness=3, vertex_colors=True)
        )

        # position data for the right edge line
        right_line_data = np.array(
            [[bounds[1], (-height / 2) + position[1], 0.5],
             [bounds[1], (height / 2) + position[1], 0.5]]
        ).astype(np.float32)

        right_line = pygfx.Line(
            pygfx.Geometry(positions=right_line_data, colors=self._edge_color.copy()),
            pygfx.LineMaterial(thickness=3, vertex_colors=True)
        )

        # add the edge lines
        self.world_object.add(left_line)
        self.world_object.add(right_line)

        self.edges: Tuple[pygfx.Line, pygfx.Line] = (left_line, right_line)

        # highlight the edges when mouse is hovered
        for edge_line in self.edges:
            edge_line.add_event_handler(
                partial(self._pointer_enter_edge, edge_line),
                "pointer_enter"
            )
            edge_line.add_event_handler(self._pointer_leave_edge, "pointer_leave")

        # set the initial bounds of the selector
        self.bounds = _LinearBoundsFeature(self, bounds)
        self.bounds = bounds

    def get_selected_data(self, graphic: Graphic = None) -> Union[np.ndarray, List[np.ndarray]]:
        """
        Get the ``Graphic`` data bounded by the current selection.
        Returns a view of the full data array.
        If the ``Graphic`` is a collection, such as a ``LineStack``, it returns a list of views of the full array.
        Can be performed on the ``parent`` Graphic or on another graphic by passing to the ``graphic`` arg.

        Returns
        -------
        graphic: Graphic, optional
            if provided, returns the data selection from this graphic instead of the graphic set as ``parent``

        Union[np.ndarray, List[np.ndarray]]
            view or list of views of the full array

        """
        if self.parent is None and graphic is None:
            raise AttributeError(
                "No Graphic to apply selector. "
                "You must either set a ``parent`` Graphic on the selector, or pass a graphic."
            )

        if graphic is not None:
            source = graphic
        else:
            source = self.parent

        # slice along x-axis
        x_slice = slice(*self.bounds())

        if isinstance(source, GraphicCollection):
            # this will return a list of views of the arrays, therefore no copy operations occur
            # it's fine and fast even as a list of views because there is no re-allocating of memory
            # this is fast even for slicing a 10,000 x 5,000 LineStack
            return source[:].data[x_slice]

        return source.data.buffer.data[x_slice]

    def _add_plot_area_hook(self, plot_area):
        # called when this selector is added to a plot area
        self._plot_area = plot_area

        # need partials so that the source of the event is passed to the `_move_start` handler
        move_start_fill = partial(self._move_start, "fill")
        move_start_edge_left = partial(self._move_start, "edge-left")
        move_start_edge_right = partial(self._move_start, "edge-right")

        self.fill.add_event_handler(move_start_fill, "pointer_down")

        if self._resizable:
            self.edges[0].add_event_handler(move_start_edge_left, "pointer_down")
            self.edges[1].add_event_handler(move_start_edge_right, "pointer_down")

        self._plot_area.renderer.add_event_handler(self._move, "pointer_move")
        self._plot_area.renderer.add_event_handler(self._move_end, "pointer_up")

    def _move_start(self, event_source: str, ev):
        """
        Parameters
        ----------
        event_source: str
            "fill" | "edge-left" | "edge-right"

        """
        # self._plot_area.controller.enabled = False
        # last pointer position
        self._move_info = {"last_pos": (ev.x, ev.y)}
        self._event_source = event_source

    def _move(self, ev):
        if self._move_info is None:
            return

        # disable the controller, otherwise the panzoom or other controllers will move the camera and will not
        # allow the selector to process the mouse events
        self._plot_area.controller.enabled = False

        last = self._move_info["last_pos"]

        delta = (last[0] - ev.x, last[1] - ev.y)

        self._move_info = {"last_pos": (ev.x, ev.y)}

        if self._event_source == "edge-left":
            # change only the left bound
            # move the left edge only, expand the fill in the leftward direction
            left_bound = self.bounds()[0] - delta[0]
            right_bound = self.bounds()[1]

        elif self._event_source == "edge-right":
            # change only the right bound
            # move the right edge only, expand the fill in the rightward direction
            left_bound = self.bounds()[0]
            right_bound = self.bounds()[1] - delta[0]

        elif self._event_source == "fill":
            # move the entire selector
            left_bound = self.bounds()[0] - delta[0]
            right_bound = self.bounds()[1] - delta[0]

        # if the limits are met do nothing
        if left_bound < self.limits[0] or right_bound > self.limits[1]:
            return

        # make sure `selector width > 2`, left edge must not move past right edge!
        # has to be at least 2 otherwise can't join datapoints for lines
        if (right_bound - left_bound) < 2:
            return

        # set the new bounds
        self.bounds = (left_bound, right_bound)

        # re-enable the controller
        self._plot_area.controller.enabled = True

    def _move_end(self, ev):
        self._move_info = None
        # sometimes weird stuff happens so we want to make sure the controller is reset
        self._plot_area.controller.enabled = True

        self._reset_edge_color()

    def _pointer_enter_edge(self, edge: pygfx.Line, ev):
        edge.material.thickness = 6
        edge.geometry.colors.data[:] = np.repeat([pygfx.Color("magenta")], 2, axis=0)
        edge.geometry.colors.update_range()

    def _pointer_leave_edge(self,  ev):
        if self._move_info is not None and self._event_source.startswith("edge"):
            return

        self._reset_edge_color()

    def _reset_edge_color(self):
        for edge in self.edges:
            edge.material.thickness = 3
            edge.geometry.colors.data[:] = self._edge_color
            edge.geometry.colors.update_range()

    def _set_feature(self, feature: str, new_data: Any, indices: Any):
        pass

    def _reset_feature(self, feature: str):
        pass