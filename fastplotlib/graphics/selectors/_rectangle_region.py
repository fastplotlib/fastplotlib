from typing import *
import numpy as np

import pygfx

from .._base import Graphic, GraphicCollection
from ..features._base import GraphicFeature, FeatureEvent
from ._base_selector import BaseSelector

from ._mesh_positions import x_right, x_left, y_top, y_bottom


class RectangleBoundsFeature(GraphicFeature):
    """
    Feature for a linearly bounding region

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
    def __init__(self, parent, bounds: Tuple[int, int], axis: str, limits: Tuple[int, int]):
        super(RectangleBoundsFeature, self).__init__(parent, data=bounds)

        self._axis = axis
        self.limits = limits

        self._set(bounds)

    @property
    def axis(self) -> str:
        """one of "x" | "y" """
        return self._axis

    def _set(self, value: Tuple[float, float, float, float]):
        """

        Parameters
        ----------
        value: Tuple[float]
            new values: (xmin, xmax, ymin, ymax)

        Returns
        -------

        """
        xmin, xmax, ymin, ymax = value

        # TODO: make sure new values do not exceed limits

        # change fill mesh
        # change left x position of the fill mesh
        self._parent.fill.geometry.positions.data[x_left, 0] = xmin

        # change right x position of the fill mesh
        self._parent.fill.geometry.positions.data[x_right, 0] = xmax

        # change bottom y position of the fill mesh
        self._parent.fill.geometry.positions.data[y_bottom, 1] = ymin

        # change top position of the fill mesh
        self._parent.fill.geometry.positions.data[y_top, 1] = ymax

        # change the edge lines

        # each edge line is defined by two end points which are stored in the
        # geometry.positions
        # [x0, y0, z0]
        # [x1, y1, z0]

        # left line
        z = self._parent.edges[0].geometry.positions.data[:, -1][0]
        self._parent.edges[0].geometry.positions.data[:] = np.array(
            [
                [xmin, ymin, z],
                [xmin, ymax, z]
            ]
        )

        # right line
        self._parent.edges[1].geometry.positions.data[:] = np.array(
            [
                [xmax, ymin, z],
                [xmax, ymax, z]
            ]
        )

        # bottom line
        self._parent.edges[2].geometry.positions.data[:] = np.array(
            [
                [xmin, ymin, z],
                [xmax, ymin, z]
            ]
        )

        # top line
        self._parent.edges[3].geometry.positions.data[:] = np.array(
            [
                [xmin, ymax, z],
                [xmax, ymax, z]
            ]
        )

        self._data = value#(value[0], value[1])

        # send changes to GPU
        self._parent.fill.geometry.positions.update_range()

        for edge in self._parent.edges:
            edge.geometry.positions.update_range()

        # calls any events
        self._feature_changed(key=None, new_data=value)

    # TODO: feature_changed
    def _feature_changed(self, key: Union[int, slice, Tuple[slice]], new_data: Any):
        return
        # if len(self._event_handlers) < 1:
        #     return
        #
        # if self._parent.parent is not None:
        #     selected_ixs = self._parent.get_selected_indices()
        #     selected_data = self._parent.get_selected_data()
        # else:
        #     selected_ixs = None
        #     selected_data = None
        #
        # pick_info = {
        #     "index": None,
        #     "collection-index": self._collection_index,
        #     "world_object": self._parent.world_object,
        #     "new_data": new_data,
        #     "selected_indices": selected_ixs,
        #     "selected_data": selected_data
        #     "graphic",
        #     "delta",
        #     "pygfx_event"
        # }
        #
        # event_data = FeatureEvent(type="bounds", pick_info=pick_info)
        #
        # self._call_event_handlers(event_data)


class RectangleRegionSelector(Graphic, BaseSelector):
    feature_events = (
        "bounds"
    )

    def __init__(
            self,
            bounds: Tuple[int, int, int, int],
            limits: Tuple[int, int],
            origin: Tuple[int, int],
            axis: str = "x",
            parent: Graphic = None,
            resizable: bool = True,
            fill_color=(0, 0, 0.35),
            edge_color=(0.8, 0.8, 0),
            arrow_keys_modifier: str = "Shift",
            name: str = None
    ):
        """
        Create a LinearRegionSelector graphic which can be moved only along either the x-axis or y-axis.
        Allows sub-selecting data from a ``Graphic`` or from multiple Graphics.

        bounds[0], limits[0], and position[0] must be identical

        Parameters
        ----------
        bounds: (int, int, int, int)
            the initial bounds of the rectangle, ``(x_min, x_max, y_min, y_max)``

        limits: (int, int, int, int)
            limits of the selector, ``(x_min, x_max, y_min, y_max)``

        origin: (int, int)
            initial position of the selector

        axis: str, default ``None``
            Restrict the selector to the "x" or "y" axis.
            If the selector is restricted to an axis you cannot change the bounds along the other axis. For example,
            if you set ``axis="x"``, then the ``y_min``, ``y_max`` values of the bounds will stay constant.

        parent: Graphic, default ``None``
            associate this selector with a parent Graphic

        resizable: bool
            if ``True``, the edges can be dragged to resize the selection

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

        Graphic.__init__(self, name=name)

        self.parent = parent

        # world object for this will be a group
        # basic mesh for the fill area of the selector
        # line for each edge of the selector
        group = pygfx.Group()
        self._set_world_object(group)

        xmin, xmax, ymin, ymax = bounds

        width = xmax - xmin
        height = ymax - ymin

        self.fill = pygfx.Mesh(
            pygfx.box_geometry(width, height, 1),
            pygfx.MeshBasicMaterial(color=pygfx.Color(fill_color))
        )

        self.fill.position.set(*origin, -2)
        self.world_object.add(self.fill)

        # position data for the left edge line
        left_line_data = np.array(
            [[origin[0], (-height / 2) + origin[1], 0.5],
             [origin[0], (height / 2) + origin[1], 0.5]]
        ).astype(np.float32)

        left_line = pygfx.Line(
            pygfx.Geometry(positions=left_line_data),
            pygfx.LineMaterial(thickness=3, color=edge_color)
        )

        # position data for the right edge line
        right_line_data = np.array(
            [[bounds[1], (-height / 2) + origin[1], 0.5],
             [bounds[1], (height / 2) + origin[1], 0.5]]
        ).astype(np.float32)

        right_line = pygfx.Line(
            pygfx.Geometry(positions=right_line_data),
            pygfx.LineMaterial(thickness=3, color=edge_color)
        )

        # position data for the left edge line
        bottom_line_data = \
            np.array(
                [[(-width / 2) + origin[0], origin[1], 0.5],
                 [(width / 2) + origin[0], origin[1], 0.5]]
            ).astype(np.float32)

        bottom_line = pygfx.Line(
            pygfx.Geometry(positions=bottom_line_data),
            pygfx.LineMaterial(thickness=3, color=edge_color)
        )

        # position data for the right edge line
        top_line_data = np.array(
            [[(-width / 2) + origin[0], bounds[1], 0.5],
             [(width / 2) + origin[0], bounds[1], 0.5]]
        ).astype(np.float32)

        top_line = pygfx.Line(
            pygfx.Geometry(positions=top_line_data),
            pygfx.LineMaterial(thickness=3, color=edge_color)
        )

        self.edges: Tuple[pygfx.Line, ...] = (
            left_line, right_line, bottom_line, top_line
        )  # left line, right line, bottom line, top line

        # add the edge lines
        for edge in self.edges:
            edge.position.set(*origin, -1)
            self.world_object.add(edge)

        self._resizable = resizable
        self._bounds = RectangleBoundsFeature(self, bounds, axis=axis, limits=limits)

        BaseSelector.__init__(
            self,
            edges=self.edges,
            fill=(self.fill,),
            hover_responsive=self.edges,
            arrow_keys_modifier=arrow_keys_modifier,
            axis=axis,
        )

    @property
    def bounds(self) -> RectangleBoundsFeature:
        """
        (xmin, xmax, ymin, ymax) The current bounds of the selection in world space.

        These bounds will NOT necessarily correspond to the indices of the data that are under the selection.
        Use ``get_selected_indices()` which maps from world space to data indices.
        """
        return self._bounds

    def _move_graphic(self, delta):
        # new left bound position
        xmin_new = Vector3(self.bounds()[0]).add(delta).x

        # new right bound position
        xmax_new = Vector3(self.bounds()[1]).add(delta).x

        # new bottom bound position
        ymin_new = Vector3(0, self.bounds()[2]).add(delta).y

        # new top bound position
        ymax_new = Vector3(0, self.bounds()[3]).add(delta).y

        # move entire selector if source was fill
        if self._move_info.source == self.fill:
            # set the new bounds
            self.bounds = (xmin_new, xmax_new, ymin_new, ymax_new)
            return

        # if selector is not resizable do nothing
        if not self._resizable:
            return

        # if resizable, move edges

        xmin, xmax, ymin, ymax = self.bounds()

        # change only left bound
        if self._move_info.source == self.edges[0]:
            xmin = xmin_new

        # change only right bound
        elif self._move_info.source == self.edges[1]:
            xmax = xmax_new

        # change only bottom bound
        elif self._move_info.source == self.edges[2]:
            ymin = ymin_new

        # change only top bound
        elif self._move_info.source == self.edges[3]:
            ymax = ymax_new
        else:
            return

        # set the new bounds
        self.bounds = (xmin, xmax, ymin, ymax)
