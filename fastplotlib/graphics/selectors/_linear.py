from typing import *
import numpy as np
from functools import partial

import pygfx
from pygfx.linalg import Vector3

from .._base import Graphic, Interaction, GraphicCollection
from ..features._base import GraphicFeature, FeatureEvent


# positions for indexing the BoxGeometry to set the "width" and "size" of the box
# hacky, but I don't think we can morph meshes in pygfx yet: https://github.com/pygfx/pygfx/issues/346
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
    """
    Feature for a linear bounding region

    Pick Info
    ---------

    +--------------------+-------------------------------+--------------------------------------------------------------------------------------+
    | key                | type                          | description                                                                          |
    +====================+===============================+======================================================================================+
    | "selected_indices" | ``numpy.ndarray`` or ``None`` | selected graphic data indices                                                        |
    | "selected_data"    | ``numpy.ndarray`` or ``None`` | selected graphic data                                                                |
    | "new_data"         | ``(float, float)``            | current bounds in world coordinates, NOT necessarily the same as "selected_indices". |
    +--------------------+-------------------------------+--------------------------------------------------------------------------------------+

    """
    def __init__(self, parent, bounds: Tuple[int, int], axis: str):
        super(LinearBoundsFeature, self).__init__(parent, data=bounds)

        self._axis = axis

    @property
    def axis(self) -> str:
        """one of "x" | "y" """
        return self._axis

    def _set(self, value):
        # sets new bounds
        if not isinstance(value, tuple):
            raise TypeError(
                "Bounds must be a tuple in the form of `(min_bound, max_bound)`, "
                "where `min_bound` and `max_bound` are numeric values."
            )

        if self.axis == "x":
            # change left x position of the fill mesh
            self._parent.fill.geometry.positions.data[x_left, 0] = value[0]

            # change right x position of the fill mesh
            self._parent.fill.geometry.positions.data[x_right, 0] = value[1]

            # change x position of the left edge line
            self._parent.edges[0].geometry.positions.data[:, 0] = value[0]

            # change x position of the right edge line
            self._parent.edges[1].geometry.positions.data[:, 0] = value[1]

        elif self.axis == "y":
            # change bottom y position of the fill mesh
            self._parent.fill.geometry.positions.data[y_bottom, 1] = value[0]

            # change top position of the fill mesh
            self._parent.fill.geometry.positions.data[y_top, 1] = value[1]

            # change y position of the bottom edge line
            self._parent.edges[0].geometry.positions.data[:, 1] = value[0]

            # change y position of the top edge line
            self._parent.edges[1].geometry.positions.data[:, 1] = value[1]

        self._data = value#(value[0], value[1])

        # send changes to GPU
        self._parent.fill.geometry.positions.update_range()

        self._parent.edges[0].geometry.positions.update_range()
        self._parent.edges[1].geometry.positions.update_range()

        # calls any events
        self._feature_changed(key=None, new_data=value)

    def _feature_changed(self, key: Union[int, slice, Tuple[slice]], new_data: Any):
        if len(self._event_handlers) < 1:
            return

        if self._parent.parent is not None:
            selected_ixs = self._parent.get_selected_indices()
            selected_data = self._parent.get_selected_data()
        else:
            selected_ixs = None
            selected_data = None

        pick_info = {
            "index": None,
            "collection-index": self._collection_index,
            "world_object": self._parent.world_object,
            "new_data": new_data,
            "selected_indices": selected_ixs,
            "selected_data": selected_data
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
            size: int,
            origin: Tuple[int, int],
            axis: str = "x",
            parent: Graphic = None,
            resizable: bool = True,
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

        size: int
            height or width of the selector

        origin: (int, int)
            initial position of the selector

        axis: str, default "x"
            "x" | "y", axis for the selector

        parent: Graphic, default ``None``
            associated this selector with a parent Graphic

        resizable: bool
            if ``True``, the edges can be dragged to resize the width of the linear selection

        fill_color: str, array, or tuple
            fill color for the selector, passed to pygfx.Color

        edge_color: str, array, or tuple
            edge color for the selector, passed to pygfx.Color

        name: str
            name for this selector graphic
        """

        # lots of very close to zero values etc. so round them
        bounds = tuple(map(round, bounds))
        limits = tuple(map(round, limits))
        origin = tuple(map(round, origin))

        # TODO: sanity checks, we recommend users to add LinearSelection using the add_linear_selector() methods
        # TODO: so we can worry about the sanity checks later
        # if axis == "x":
        #     if limits[0] != origin[0] != bounds[0]:
        #         raise ValueError(
        #             f"limits[0] != position[0] != bounds[0]\n"
        #             f"{limits[0]} != {origin[0]} != {bounds[0]}"
        #         )
        #
        # elif axis == "y":
        #     # initial y-position is position[1]
        #     if limits[0] != origin[1] != bounds[0]:
        #         raise ValueError(
        #             f"limits[0] != position[1] != bounds[0]\n"
        #             f"{limits[0]} != {origin[1]} != {bounds[0]}"
        #         )

        super(LinearSelector, self).__init__(name=name)

        self.parent = parent

        # world object for this will be a group
        # basic mesh for the fill area of the selector
        # line for each edge of the selector
        group = pygfx.Group()
        self._set_world_object(group)

        if axis == "x":
            mesh = pygfx.Mesh(
            pygfx.box_geometry(1, size, 1),
            pygfx.MeshBasicMaterial(color=pygfx.Color(fill_color))
            )

        elif axis == "y":
            mesh = pygfx.Mesh(
                pygfx.box_geometry(size, 1, 1),
                pygfx.MeshBasicMaterial(color=pygfx.Color(fill_color))
            )

        # the fill of the selection
        self.fill = mesh

        self.fill.position.set(*origin, -2)

        self.world_object.add(self.fill)

        # will be used to store the mouse pointer x y movements
        # so deltas can be calculated for interacting with the selection
        self._move_info = None

        # mouse events can come from either the fill mesh world object, or one of the lines on the edge of the selector
        self._event_source: str = None

        self.limits = limits
        self._resizable = resizable

        self._edge_color = np.repeat([pygfx.Color(edge_color)], 2, axis=0)

        if axis == "x":
            # position data for the left edge line
            left_line_data = np.array(
                [[origin[0], (-size / 2) + origin[1], 0.5],
                 [origin[0], (size / 2) + origin[1], 0.5]]
            ).astype(np.float32)

            left_line = pygfx.Line(
                pygfx.Geometry(positions=left_line_data, colors=self._edge_color.copy()),
                pygfx.LineMaterial(thickness=3, vertex_colors=True)
            )

            # position data for the right edge line
            right_line_data = np.array(
                [[bounds[1], (-size / 2) + origin[1], 0.5],
                 [bounds[1], (size / 2) + origin[1], 0.5]]
            ).astype(np.float32)

            right_line = pygfx.Line(
                pygfx.Geometry(positions=right_line_data, colors=self._edge_color.copy()),
                pygfx.LineMaterial(thickness=3, vertex_colors=True)
            )

            self.edges: Tuple[pygfx.Line, pygfx.Line] = (left_line, right_line)

        elif axis == "y":
            # position data for the left edge line
            bottom_line_data = \
                np.array(
                    [[(-size / 2) + origin[0], origin[1], 0.5],
                     [(size / 2) + origin[0], origin[1], 0.5]]
                ).astype(np.float32)

            bottom_line = pygfx.Line(
                pygfx.Geometry(positions=bottom_line_data, colors=self._edge_color.copy()),
                pygfx.LineMaterial(thickness=3, vertex_colors=True)
            )

            # position data for the right edge line
            top_line_data = np.array(
                [[(-size / 2) + origin[0], bounds[1], 0.5],
                 [(size / 2) + origin[0], bounds[1], 0.5]]
            ).astype(np.float32)

            top_line = pygfx.Line(
                pygfx.Geometry(positions=top_line_data, colors=self._edge_color.copy()),
                pygfx.LineMaterial(thickness=3, vertex_colors=True)
            )

            self.edges: Tuple[pygfx.Line, pygfx.Line] = (bottom_line, top_line)

        # add the edge lines
        for edge in self.edges:
            edge.position.set_z(-1)
            self.world_object.add(edge)

        # highlight the edges when mouse is hovered
        for edge_line in self.edges:
            edge_line.add_event_handler(
                partial(self._pointer_enter_edge, edge_line),
                "pointer_enter"
            )
            edge_line.add_event_handler(self._pointer_leave_edge, "pointer_leave")

        # set the initial bounds of the selector
        self._bounds = LinearBoundsFeature(self, bounds, axis=axis)
        self._bounds: LinearBoundsFeature = bounds

    @property
    def bounds(self) -> LinearBoundsFeature:
        """
        The current bounds of the selection in world space. These bounds will NOT necessarily correspond to the
        indices of the data that are under the selection. Use ``get_selected_indices()` which maps from
        world space to data indices.
        """
        return self._bounds

    def get_selected_data(self, graphic: Graphic = None) -> Union[np.ndarray, List[np.ndarray], None]:
        """
        Get the ``Graphic`` data bounded by the current selection.
        Returns a view of the full data array.
        If the ``Graphic`` is a collection, such as a ``LineStack``, it returns a list of views of the full array.
        Can be performed on the ``parent`` Graphic or on another graphic by passing to the ``graphic`` arg.

        **NOTE:** You must be aware of the axis for the selector. The sub-selected data that is returned will be of
        shape ``[n_points_selected, 3]``. If you have selected along the x-axis then you can access y-values of the
        subselection like this: sub[:, 1]. Conversely, if you have selected along the y-axis then you can access the
        x-values of the subselection like this: sub[:, 0].

        Parameters
        ----------
        graphic: Graphic, optional
            if provided, returns the data selection from this graphic instead of the graphic set as ``parent``

        Returns
        -------
        np.ndarray, List[np.ndarray], or None
            view or list of views of the full array, returns ``None`` if selection is empty

        """
        source = self._get_source(graphic)
        ixs = self.get_selected_indices(source)

        if isinstance(source, GraphicCollection):
            # this will return a list of views of the arrays, therefore no copy operations occur
            # it's fine and fast even as a list of views because there is no re-allocating of memory
            # this is fast even for slicing a 10,000 x 5,000 LineStack
            data_selections: List[np.ndarray] = list()

            for i, g in enumerate(source.graphics):
                if ixs[i].size == 0:
                    data_selections.append(None)
                else:
                    s = slice(ixs[i][0], ixs[i][-1])
                    data_selections.append(g.data.buffer.data[s])

            return source[:].data[s]
        # just for one graphic
        else:
            if ixs.size == 0:
                return None

            s = slice(ixs[0], ixs[-1])
            return source.data.buffer.data[s]

    def get_selected_indices(self, graphic: Graphic = None) -> Union[np.ndarray, List[np.ndarray]]:
        """
        Returns the indices of the ``Graphic`` data bounded by the current selection.
        This is useful because the ``bounds`` min and max are not necessarily the same
        as the Line Geometry positions x-vals or y-vals. For example, if if you used a
        np.linspace(0, 100, 1000) for xvals in your line, then you will have 1,000
        x-positions. If the selection ``bounds`` are set to ``(0, 10)``, the returned
        indices would be ``(0, 100``.

        Parameters
        ----------
        graphic: Graphic, optional
            if provided, returns the selection indices from this graphic instead of the graphic set as ``parent``

        Returns
        -------
        Union[np.ndarray, List[np.ndarray]]
            data indices of the selection

        """
        source = self._get_source(graphic)

        # if the graphic position is not at (0, 0) then the bounds must be offset
        offset = getattr(source.position, self.bounds.axis)
        offset_bounds = tuple(v - offset for v in self.bounds())
        # need them to be int to use as indices
        offset_bounds = tuple(map(int, offset_bounds))

        if self.bounds.axis == "x":
            dim = 0
        else:
            dim = 1
        # now we need to map from graphic space to data space
        # we can have more than 1 datapoint between two integer locations in the world space
        if isinstance(source, GraphicCollection):
            ixs = list()
            for g in source.graphics:
                # map for each graphic in the collection
                g_ixs = np.where(
                    (g.data()[:, dim] >= offset_bounds[0]) & (g.data()[:, dim] <= offset_bounds[1])
                )[0]
                ixs.append(g_ixs)
        else:
            # map this only this graphic
            ixs = np.where(
                (source.data()[:, dim] >= offset_bounds[0]) & (source.data()[:, dim] <= offset_bounds[1])
            )[0]

        return ixs

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
        # called when this selector is added to a plot area
        self._plot_area = plot_area

        # need partials so that the source of the event is passed to the `_move_start` handler
        self._move_start_fill = partial(self._move_start, "fill")
        self._move_start_edge_0 = partial(self._move_start, "edge-0")
        self._move_start_edge_1 = partial(self._move_start, "edge-1")

        self.fill.add_event_handler(self._move_start_fill, "pointer_down")

        if self._resizable:
            self.edges[0].add_event_handler(self._move_start_edge_0, "pointer_down")
            self.edges[1].add_event_handler(self._move_start_edge_1, "pointer_down")

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

        # new - last
        # pointer move events are in viewport or canvas space
        delta = Vector3(ev.x - last[0], ev.y - last[1])

        self._move_info = {"last_pos": (ev.x, ev.y)}

        viewport_size = self._plot_area.viewport.logical_size

        # convert delta to NDC coordinates using viewport size
        # also since these are just deltas we don't have to calculate positions relative to the viewport
        delta_ndc = delta.multiply(
            Vector3(
                2 / viewport_size[0],
                -2 / viewport_size[1],
                0
            )
        )

        camera = self._plot_area.camera

        # edge-0 bound current world position
        if self.bounds.axis == "x":
            # left bound position
            vec0 = Vector3(self.bounds()[0])
        else:
            # bottom bound position
            vec0 = Vector3(0, self.bounds()[0])
        # compute and add delta in projected NDC space and then unproject back to world space
        vec0.project(camera).add(delta_ndc).unproject(camera)

        # edge-1 bound current world position
        if self.bounds.axis == "x":
            vec1 = Vector3(self.bounds()[1])
        else:
            vec1 = Vector3(0, self.bounds()[1])
        # compute and add delta in projected NDC space and then unproject back to world space
        vec1.project(camera).add(delta_ndc).unproject(camera)

        if self._event_source == "edge-0":
            # change only the left bound or bottom bound
            bound0 = getattr(vec0, self.bounds.axis)  # gets either vec.x or vec.y
            bound1 = self.bounds()[1]

        elif self._event_source == "edge-1":
            # change only the right bound or top bound
            bound0 = self.bounds()[0]
            bound1 = getattr(vec1, self.bounds.axis)   # gets either vec.x or vec.y

        elif self._event_source == "fill":
            # move the entire selector
            bound0 = getattr(vec0, self.bounds.axis)
            bound1 = getattr(vec1, self.bounds.axis)

        # if the limits are met do nothing
        if bound0 < self.limits[0] or bound1 > self.limits[1]:
            return

        # make sure `selector width >= 2`, left edge must not move past right edge!
        # or bottom edge must not move past top edge!
        # has to be at least 2 otherwise can't join datapoints for lines
        if not (bound1 - bound0) >= 2:
            return

        # set the new bounds
        self.bounds = (bound0, bound1)

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

    def __del__(self):
        self.fill.remove_event_handler(self._move_start_fill, "pointer_down")

        if self._resizable:
            self.edges[0].remove_event_handler(self._move_start_edge_0, "pointer_down")
            self.edges[1].remove_event_handler(self._move_start_edge_1, "pointer_down")

        self._plot_area.renderer.remove_event_handler(self._move, "pointer_move")
        self._plot_area.renderer.remove_event_handler(self._move_end, "pointer_up")
