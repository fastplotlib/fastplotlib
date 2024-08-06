from numbers import Real
from typing import *
import numpy as np

import pygfx
from .._collection_base import GraphicCollection

from .._base import Graphic
from .._features import RectangleSelectionFeature
from ._base_selector import BaseSelector


class RectangleSelector(BaseSelector):
    @property
    def parent(self) -> Graphic | None:
        """Graphic that selector is associated with."""
        return self._parent

    @property
    def selection(self) -> Sequence[float] | List[Sequence[float]]:
        """
        (xmin, xmax, ymin, ymax) of the rectangle selection
        """
        return self._selection.value

    @selection.setter
    def selection(self, selection: Sequence[float]):
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
            selection: Sequence[float],
            limits: Sequence[float],
            axis: str = None,
            parent: Graphic = None,
            resizable: bool = True,
            fill_color=(0, 0, 0.35),
            edge_color=(0.8, 0.6, 0),
            edge_thickness: float = 8,
            arrow_keys_modifier: str = "Shift",
            name: str = None,
    ):
        """
        Create a RectangleSelector graphic which can be used to select a rectangular region of data.
        Allows sub-selecting data from a ``Graphic`` or from multiple Graphics.

        Parameters
        ----------
        selection: (float, float, float, float)
            the initial selection of the rectangle, ``(x_min, x_max, y_min, y_max)``

        limits: (float, float, float, float)
            limits of the selector, ``(x_min, x_max, y_min, y_max)``

        axis: str, default ``None``
            Restrict the selector to the "x" or "y" axis.
            If the selector is restricted to an axis you cannot change the selection along the other axis. For example,
            if you set ``axis="x"``, then the ``y_min``, ``y_max`` values of the selection will stay constant.

        parent: Graphic, default ``None``
            associate this selector with a parent Graphic

        resizable: bool, default ``True``
            if ``True``, the edges can be dragged to resize the selection

        fill_color: str, array, or tuple
            fill color for the selector, passed to pygfx.Color

        edge_color: str, array, or tuple
            edge color for the selector, passed to pygfx.Color

        edge_thickness: float, default 8
            edge thickness

        arrow_keys_modifier: str
            modifier key that must be pressed to initiate movement using arrow keys, must be one of:
            "Control", "Shift", "Alt" or ``None``

        name: str
            name for this selector graphic
        """

        if not len(selection) == 4 or not len(limits) == 4:
            raise ValueError()

        # lots of very close to zero values etc. so round them
        selection = tuple(map(round, selection))
        limits = tuple(map(round, limits))

        self._parent = parent
        self._limits = np.asarray(limits)
        self._resizable = resizable

        selection = np.asarray(selection)

        # world object for this will be a group
        # basic mesh for the fill area of the selector
        # line for each edge of the selector
        group = pygfx.Group()

        xmin, xmax, ymin, ymax = selection

        width = xmax - xmin
        height = ymax - ymin

        if width < 0 or height < 0:
            raise ValueError()

        self.fill = pygfx.Mesh(
            pygfx.box_geometry(width, height, 1),
            pygfx.MeshBasicMaterial(color=pygfx.Color(fill_color), pick_write=True),
        )

        self.fill.world.position = (0, 0, -2)

        group.add(self.fill)

        #position data for the left edge line
        left_line_data = np.array(
            [
                [xmin, ymin, 0],
                [xmin, ymax, 0],
            ]
        ).astype(np.float32)

        left_line = pygfx.Line(
            pygfx.Geometry(positions=left_line_data.copy()),
            pygfx.LineMaterial(thickness=edge_thickness, color=edge_color),
        )

        # position data for the right edge line
        right_line_data = np.array(
            [
                [xmax, ymin, 0],
                [xmax, ymax, 0],
            ]
        ).astype(np.float32)

        right_line = pygfx.Line(
            pygfx.Geometry(positions=right_line_data.copy()),
            pygfx.LineMaterial(thickness=edge_thickness, color=edge_color),
        )

        # position data for the left edge line
        bottom_line_data = np.array(
            [
                [xmin, ymax, 0],
                [xmax, ymax, 0],
            ]
        ).astype(np.float32)

        bottom_line = pygfx.Line(
            pygfx.Geometry(positions=bottom_line_data.copy()),
            pygfx.LineMaterial(thickness=edge_thickness, color=edge_color),
        )

        # position data for the right edge line
        top_line_data = np.array(
            [
                [xmin, ymin, 0],
                [xmax, ymin, 0],
            ]
        ).astype(np.float32)

        top_line = pygfx.Line(
            pygfx.Geometry(positions=top_line_data.copy()),
            pygfx.LineMaterial(thickness=edge_thickness, color=edge_color),
        )

        self.edges: Tuple[pygfx.Line, pygfx.Line, pygfx.Line, pygfx.Line] = (
            left_line,
            right_line,
            bottom_line,
            top_line,
        )  # left line, right line, bottom line, top line

        # add the edge lines
        for edge in self.edges:
            edge.world.z = -0.5
            group.add(edge)

        # vertices
        top_left_vertex_data = (xmin, ymax, 1)
        top_right_vertex_data = (xmax, ymax, 1)
        bottom_left_vertex_data = (xmin, ymin, 1)
        bottom_right_vertex_data = (xmax, ymin, 1)

        top_left_vertex = pygfx.Points(
            pygfx.Geometry(positions=[top_left_vertex_data], sizes=[edge_thickness]),
            pygfx.PointsMaterial(size=edge_thickness, color=edge_color, size_space="world", size_mode="vertex"),
        )

        top_right_vertex = pygfx.Points(
            pygfx.Geometry(positions=[top_right_vertex_data], sizes=[edge_thickness]),
            pygfx.PointsMaterial(size=edge_thickness, color=edge_color, size_space="world", size_mode="vertex"),
        )

        bottom_left_vertex = pygfx.Points(
            pygfx.Geometry(positions=[bottom_left_vertex_data], sizes=[edge_thickness]),
            pygfx.PointsMaterial(size=edge_thickness, color=edge_color, size_space="world", size_mode="vertex"),
        )

        bottom_right_vertex = pygfx.Points(
            pygfx.Geometry(positions=[bottom_right_vertex_data], sizes=[edge_thickness]),
            pygfx.PointsMaterial(size=edge_thickness, color=edge_color, size_space="world", size_mode="vertex"),
        )

        self.vertices: Tuple[pygfx.Points, pygfx.Points, pygfx.Points, pygfx.Points] = (
            bottom_left_vertex,
            bottom_right_vertex,
            top_left_vertex,
            top_right_vertex,
        )

        for vertex in self.vertices:
            vertex.world.z = -0.25
            group.add(vertex)

        self._selection = RectangleSelectionFeature(selection, axis=axis, limits=self._limits)

        # include parent offset
        if parent is not None:
            offset = (parent.offset[0], parent.offset[1], 0)
        else:
            offset = (0, 0, 0)

        BaseSelector.__init__(
            self,
            edges=self.edges,
            fill=(self.fill,),
            vertices=self.vertices,
            hover_responsive=(*self.edges, *self.vertices),
            arrow_keys_modifier=arrow_keys_modifier,
            axis=axis,
            parent=parent,
            name=name,
            offset=offset,
        )

        self._set_world_object(group)

        self.selection = selection

    def get_selected_data(self, graphic: Graphic = None) -> Union[np.ndarray, List[np.ndarray]]:
        """
        Get the ``Graphic`` data bounded by the current selection.
        Returns a view of the data array.

        If the ``Graphic`` is a collection, such as a ``LineStack``, it returns a list of views of the full array.
        Can be performed on the ``parent`` Graphic or on another graphic by passing to the ``graphic`` arg.

        Parameters
        ----------
        graphic: Graphic, optional, default ``None``
            if provided, returns the data selection from this graphic instead of the graphic set as ``parent``

        Returns
        -------
        np.ndarray or List[np.ndarray]
            view or list of views of the full array, returns ``None`` if selection is empty
        """
        source = self._get_source(graphic)
        ixs = self.get_selected_indices(source)

        if "Image" in source.__class__.__name__:
            s_x = slice(ixs[0][0], ixs[0][-1] + 1)
            s_y = slice(ixs[1][0], ixs[1][-1] + 1)

            return source.data[s_x, s_y]

        if "Line" in source.__class__.__name__:
            if isinstance(source, GraphicCollection):
                data_selections: List[np.ndarray] = list()

                for i, g in enumerate(source.graphics):
                    if ixs[i].size == 0:
                        data_selections.append(
                            np.array([], dtype=np.float32).reshape(0, 3)
                        )
                    else:
                        s = slice(
                            ixs[i][0], ixs[i][-1] + 1
                        )  # add 1 because these are direct indices
                        # slices n_datapoints dim
                        data_selections.append(g.data[s])
            else:
                if ixs.size == 0:
                    # empty selection
                    return np.array([], dtype=np.float32).reshape(0, 3)

                s = slice(
                    ixs[0], ixs[-1] + 1
                )  # add 1 to end because these are direct indices
                # slices n_datapoints dim
                # slice with min, max is faster than using all the indices
            return source.data[s]

    def get_selected_indices(self, graphic: Graphic = None) -> Union[np.ndarray, List[np.ndarray]]:
        """
        Returns the indices of the ``Graphic`` data bounded by the current selection.

        These are the data indices which correspond to the data under the selector.

        Parameters
        ----------
        graphic: Graphic, default ``None``
            If provided, returns the selection indices from this graphic instrad of the graphic set as ``parent``

        Returns
        -------
        Union[np.ndarray, List[np.ndarray]]
            data indicies of the selection, list of np.ndarray if the graphic is a collection
        """
        # get indices from source
        source = self._get_source(graphic)

        # selector (xmin, xmax, ymin, ymax) values
        bounds = self.selection

        if "Image" in source.__class__.__name__:
            ys = np.arange(bounds[0], bounds[1], dtype=int)
            xs = np.arange(bounds[2], bounds[3], dtype=int)
            return [xs, ys]

        if "Line" in source.__class__.__name__:
            if isinstance(source, GraphicCollection):
                ixs = list()
                for g in source.graphics:
                    data = g.data.value
                    g_ixs = np.where((data[:, 0] >= bounds[0]) &
                                     (data[:, 0] <= bounds[1]) &
                                     (data[:, 1] >= bounds[2]) &
                                     (data[:, 1] <= bounds[3]))[0]
                    ixs.append(g_ixs)
            else:
                # map only this graphic
                data = source.data.value
                ixs = np.where((data[:, 0] >= bounds[0]) &
                               (data[:, 0] <= bounds[1]) &
                               (data[:, 1] >= bounds[2]) &
                               (data[:, 1] <= bounds[3]))[0]
            return ixs

    def _move_graphic(self, delta: np.ndarray):

        # new selection positions
        xmin_new = self.selection[0] + delta[0]
        xmax_new = self.selection[1] + delta[0]
        ymin_new = self.selection[2] + delta[1]
        ymax_new = self.selection[3] + delta[1]

        # move entire selector if source is fill
        if self._move_info.source == self.fill:
            if self.selection[0] == self.limits[0] and xmin_new < self.limits[0]:
                return
            if self.selection[1] == self.limits[1] and xmax_new > self.limits[1]:
                return
            if self.selection[2] == self.limits[2] and ymin_new < self.limits[2]:
                return
            if self.selection[3] == self.limits[3] and ymax_new > self.limits[3]:
                return
            # set thew new bounds
            self._selection.set_value(self, (xmin_new, xmax_new, ymin_new, ymax_new))
            return

        # if selector not resizable return
        if not self._resizable:
            return

        xmin, xmax, ymin, ymax = self.selection

        if self._move_info.source == self.vertices[0]: # bottom left
            self._selection.set_value(self, (xmin_new, xmax, ymin_new, ymax))
        if self._move_info.source == self.vertices[1]: # bottom right
            self._selection.set_value(self, (xmin, xmax_new, ymin_new, ymax))
        if self._move_info.source == self.vertices[2]: # top left
            self._selection.set_value(self, (xmin_new, xmax, ymin, ymax_new))
        if self._move_info.source == self.vertices[3]: # top right
            self._selection.set_value(self, (xmin, xmax_new, ymin, ymax_new))
        # if event source was an edge and selector is resizable, move the edge that caused the event
        if self._move_info.source == self.edges[0]:
            self._selection.set_value(self, (xmin_new, xmax, ymin, ymax))
        if self._move_info.source == self.edges[1]:
            self._selection.set_value(self, (xmin, xmax_new, ymin, ymax))
        if self._move_info.source == self.edges[2]:
            self._selection.set_value(self, (xmin, xmax, ymin_new, ymax))
        if self._move_info.source == self.edges[3]:
            self._selection.set_value(self, (xmin, xmax, ymin, ymax_new))
