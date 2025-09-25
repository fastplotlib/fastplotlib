import warnings
from numbers import Real
from typing import *
import numpy as np

import pygfx
from .._collection_base import GraphicCollection

from ...utils.enums import RenderQueue
from .._base import Graphic
from ..features import RectangleSelectionFeature


class RectangleSelector(BaseSelector):
    _features = {"selection": RectangleSelectionFeature}

    @property
    def parent(self) -> Graphic | None:
        """Graphic that selector is associated with."""
        return self._parent

    @property
    def selection(self) -> np.ndarray[float]:
        """
        (xmin, xmax, ymin, ymax) of the rectangle selection
        """
        return self._selection.value.copy()

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
        parent: Graphic = None,
        resizable: bool = True,
        fill_color=(0, 0, 0.35),
        edge_color=(0.8, 0.6, 0),
        edge_thickness: float = 8,
        vertex_color=(0.7, 0.4, 0),
        vertex_size: float = 8,
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

        parent: Graphic, default ``None``
            associate this selector with a parent Graphic

        resizable: bool, default ``True``
            if ``True``, the edges can be dragged to resize the selection

        fill_color: str, array, or tuple
            fill color for the selector as a str or RGBA array

        edge_color: str, array, or tuple
            edge color for the selector as a str or RGBA array

        edge_thickness: float, default 8
            edge thickness

        vertex_color: str, array, or tuple
            vertex color for the selector as a str or RGBA array

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

        self._fill_color = pygfx.Color(fill_color)
        self._edge_color = pygfx.Color(edge_color)
        self._vertex_color = pygfx.Color(vertex_color)

        width = xmax - xmin
        height = ymax - ymin

        if width < 0 or height < 0:
            raise ValueError()

        self.fill = pygfx.Mesh(
            pygfx.box_geometry(width, height, 1),
            pygfx.MeshBasicMaterial(
                color=pygfx.Color(self.fill_color),
                alpha_mode="blend",
                opacity=0.4,
                render_queue=RenderQueue.selector,
                depth_test=False,
                depth_write=False,
                pick_write=True,
            ),
        )

        self.fill.world.position = (0, 0, -2)

        group.add(self.fill)

        # position data for the left edge line
        left_line_data = np.array(
            [
                [xmin, ymin, 0],
                [xmin, ymax, 0],
            ]
        ).astype(np.float32)

        left_line = pygfx.Line(
            pygfx.Geometry(positions=left_line_data.copy()),
            pygfx.LineMaterial(
                thickness=edge_thickness,
                color=self.edge_color,
                alpha_mode="blend",
                aa=True,
                render_queue=RenderQueue.selector,
                depth_test=False,
                depth_write=False,
            ),
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
            pygfx.LineMaterial(
                thickness=edge_thickness,
                color=self.edge_color,
                alpha_mode="blend",
                aa=True,
                render_queue=RenderQueue.selector,
                depth_test=False,
                depth_write=False,
            ),
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
            pygfx.LineMaterial(
                thickness=edge_thickness,
                color=self.edge_color,
                alpha_mode="blend",
                aa=True,
                render_queue=RenderQueue.selector,
                depth_test=False,
                depth_write=False,
            ),
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
            pygfx.LineMaterial(
                thickness=edge_thickness,
                color=self.edge_color,
                alpha_mode="blend",
                aa=True,
                render_queue=RenderQueue.selector,
                depth_test=False,
                depth_write=False,
            ),
        )

        self.edges: Tuple[pygfx.Line, pygfx.Line, pygfx.Line, pygfx.Line] = (
            left_line,
            right_line,
            bottom_line,
            top_line,
        )  # left line, right line, bottom line, top line

        # add the edge lines

        for edge in self.edges:
            edge.render_order = 1
            group.add(*self.edges)

        # vertices
        top_left_vertex_data = (xmin, ymax, 1)
        top_right_vertex_data = (xmax, ymax, 1)
        bottom_left_vertex_data = (xmin, ymin, 1)
        bottom_right_vertex_data = (xmax, ymin, 1)

        top_left_vertex = pygfx.Points(
            pygfx.Geometry(positions=[top_left_vertex_data], sizes=[vertex_size]),
            pygfx.PointsMarkerMaterial(
                marker="square",
                size=vertex_size,
                color=self.vertex_color,
                size_mode="vertex",
                edge_color=self.vertex_color,
                alpha_mode="blend",
                aa=True,
                render_queue=RenderQueue.selector,
                depth_test=False,
                depth_write=False,
            ),
        )

        top_right_vertex = pygfx.Points(
            pygfx.Geometry(positions=[top_right_vertex_data], sizes=[vertex_size]),
            pygfx.PointsMarkerMaterial(
                marker="square",
                size=vertex_size,
                color=self.vertex_color,
                size_mode="vertex",
                edge_color=self.vertex_color,
                alpha_mode="blend",
                aa=True,
                render_queue=RenderQueue.selector,
                depth_test=False,
                depth_write=False,
            ),
        )

        bottom_left_vertex = pygfx.Points(
            pygfx.Geometry(positions=[bottom_left_vertex_data], sizes=[vertex_size]),
            pygfx.PointsMarkerMaterial(
                marker="square",
                size=vertex_size,
                color=self.vertex_color,
                size_mode="vertex",
                edge_color=self.vertex_color,
                alpha_mode="blend",
                aa=True,
                render_queue=RenderQueue.selector,
                depth_test=False,
                depth_write=False,
            ),
        )

        bottom_right_vertex = pygfx.Points(
            pygfx.Geometry(positions=[bottom_right_vertex_data], sizes=[vertex_size]),
            pygfx.PointsMarkerMaterial(
                marker="square",
                size=vertex_size,
                color=self.vertex_color,
                size_mode="vertex",
                edge_color=self.vertex_color,
                alpha_mode="blend",
                aa=True,
                render_queue=RenderQueue.selector,
                depth_test=False,
                depth_write=False,
            ),
        )

        self.vertices: Tuple[pygfx.Points, pygfx.Points, pygfx.Points, pygfx.Points] = (
            bottom_left_vertex,
            bottom_right_vertex,
            top_left_vertex,
            top_right_vertex,
        )

        for vertex in self.vertices:
            vertex.render_order = 2
            group.add(vertex)

        self._selection = RectangleSelectionFeature(selection, limits=self._limits)

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
            parent=parent,
            name=name,
            offset=offset,
        )

        self._set_world_object(group)

        self.selection = selection

    def get_selected_data(
        self, graphic: Graphic = None, mode: str = "full"
    ) -> Union[np.ndarray, List[np.ndarray]]:
        """
        Get the ``Graphic`` data bounded by the current selection.
        Returns a view of the data array.

        If the ``Graphic`` is a collection, such as a ``LineStack``, it returns a list of views of the full array.
        Can be performed on the ``parent`` Graphic or on another graphic by passing to the ``graphic`` arg.

        Parameters
        ----------
        graphic: Graphic, optional, default ``None``
            if provided, returns the data selection from this graphic instead of the graphic set as ``parent``
        mode: str, default 'full'
            One of 'full', 'partial', or 'ignore'. Indicates how selected data should be returned based on the
            selectors position over the graphic. Only used for ``LineGraphic``, ``LineCollection``, and ``LineStack``
            | If 'full', will return all data bounded by the x and y limits of the selector even if partial indices
            along one axis are not fully covered by the selector.
            | If 'partial' will return only the data that is bounded by the selector, missing indices not bounded by the
            selector will be set to NaNs
            | If 'ignore', will only return data for graphics that have indices completely bounded by the selector

        Returns
        -------
        np.ndarray or List[np.ndarray]
            view or list of views of the full array, returns empty array if selection is empty
        """
        source = self._get_source(graphic)
        ixs = self.get_selected_indices(source)

        # do not need to check for mode for images, because the selector is bounded by the image shape
        # will always be `full`
        if "Image" in source.__class__.__name__:
            row_ixs, col_ixs = ixs
            row_slice = slice(row_ixs[0], row_ixs[-1] + 1)
            col_slice = slice(col_ixs[0], col_ixs[-1] + 1)

            return source.data[row_slice, col_slice]

        if mode not in ["full", "partial", "ignore"]:
            raise ValueError(
                f"`mode` must be one of 'full', 'partial', or 'ignore', you have passed {mode}"
            )
        if "Line" in source.__class__.__name__:
            if isinstance(source, GraphicCollection):
                data_selections: List[np.ndarray] = list()

                for i, g in enumerate(source.graphics):
                    # want to keep same length as the original line collection
                    if ixs[i].size == 0:
                        data_selections.append(
                            np.array([], dtype=np.float32).reshape(0, 3)
                        )
                    else:
                        # s gives entire slice of data along the x
                        s = slice(
                            ixs[i][0], ixs[i][-1] + 1
                        )  # add 1 because these are direct indices
                        # slices n_datapoints dim

                        # calculate missing ixs using set difference
                        # then calculate shift
                        missing_ixs = (
                            np.setdiff1d(np.arange(ixs[i][0], ixs[i][-1] + 1), ixs[i])
                            - ixs[i][0]
                        )

                        match mode:
                            # take all ixs, ignore missing
                            case "full":
                                data_selections.append(g.data[s])
                            # set missing ixs data to NaNs
                            case "partial":
                                if len(missing_ixs) > 0:
                                    data = g.data[s].copy()
                                    data[missing_ixs] = np.nan
                                    data_selections.append(data)
                                else:
                                    data_selections.append(g.data[s])
                            # ignore lines that do not have full ixs to start
                            case "ignore":
                                if len(missing_ixs) > 0:
                                    data_selections.append(
                                        np.array([], dtype=np.float32).reshape(0, 3)
                                    )
                                else:
                                    data_selections.append(g.data[s])
                return data_selections
            else:  # for lines
                if ixs.size == 0:
                    # empty selection
                    return np.array([], dtype=np.float32).reshape(0, 3)

                s = slice(
                    ixs[0], ixs[-1] + 1
                )  # add 1 to end because these are direct indices
                # slices n_datapoints dim
                # slice with min, max is faster than using all the indices

                # get missing ixs
                missing_ixs = np.setdiff1d(np.arange(ixs[0], ixs[-1] + 1), ixs) - ixs[0]

                match mode:
                    # return all, do not care about missing
                    case "full":
                        return source.data[s]
                    # set missing to NaNs
                    case "partial":
                        if len(missing_ixs) > 0:
                            data = source.data[s].copy()
                            data[missing_ixs] = np.nan
                            return data
                        else:
                            return source.data[s]
                    # missing means nothing will be returned even if selector is partially over data
                    # warn the user and return empty
                    case "ignore":
                        if len(missing_ixs) > 0:
                            warnings.warn(
                                "You have selected 'ignore' mode. Selected graphic has incomplete indices. "
                                "Move the selector or change the mode to one of `partial` or `full`."
                            )
                            return np.array([], dtype=np.float32)
                        else:
                            return source.data[s]

    def get_selected_indices(
        self, graphic: Graphic = None
    ) -> np.ndarray | tuple[np.ndarray]:
        """
        Returns the indices of the ``Graphic`` data bounded by the current selection.

        These are the data indices which correspond to the data under the selector.

        Parameters
        ----------
        graphic: Graphic, default ``None``
            If provided, returns the selection indices from this graphic instead of the graphic set as ``parent``

        Returns
        -------
        Union[np.ndarray, List[np.ndarray]]
            data indicies of the selection
            | tuple of [row_indices, col_indices] if the graphic is an image
            | list of indices along the x-dimension for each line if graphic is a line collection
            | array of indices along the x-dimension if graphic is a line
        """
        # get indices from source
        source = self._get_source(graphic)

        # selector (xmin, xmax, ymin, ymax) values
        xmin, xmax, ymin, ymax = self.selection

        # image data does not need to check for mode because the selector is always bounded
        # to the image
        if "Image" in source.__class__.__name__:
            col_ixs = np.arange(xmin, xmax, dtype=int)
            row_ixs = np.arange(ymin, ymax, dtype=int)
            return row_ixs, col_ixs

        if "Line" in source.__class__.__name__:
            if isinstance(source, GraphicCollection):
                ixs = list()
                for g in source.graphics:
                    data = g.data.value
                    g_ixs = np.where(
                        (data[:, 0] >= xmin - g.offset[0])
                        & (data[:, 0] <= xmax - g.offset[0])
                        & (data[:, 1] >= ymin - g.offset[1])
                        & (data[:, 1] <= ymax - g.offset[1])
                    )[0]
                    ixs.append(g_ixs)
            else:
                # map only this graphic
                data = source.data.value
                ixs = np.where(
                    (data[:, 0] >= xmin)
                    & (data[:, 0] <= xmax)
                    & (data[:, 1] >= ymin)
                    & (data[:, 1] <= ymax)
                )[0]

            return ixs

    def _move_graphic(self, move_info: MoveInfo):
        # If this the first move in this drag, store initial selection
        if move_info.start_selection is None:
            move_info.start_selection = self.selection

        # add delta to current min, max to get new positions
        deltax, deltay = move_info.delta[0], move_info.delta[1]

        # Get original selection
        xmin, xmax, ymin, ymax = move_info.start_selection

        # move entire selector if source is fill
        if move_info.source == self.fill:
            # Limit the delta to avoid weird resizine behavior
            min_deltax = self.limits[0] - xmin
            max_deltax = self.limits[1] - xmax
            min_deltay = self.limits[2] - ymin
            max_deltay = self.limits[3] - ymax
            deltax = np.clip(deltax, min_deltax, max_deltax)
            deltay = np.clip(deltay, min_deltay, max_deltay)
            # Update all bounds with equal amount
            self._selection.set_value(
                self, (xmin + deltax, xmax + deltax, ymin + deltay, ymax + deltay)
            )
            return

        # if selector not resizable return
        if not self._resizable:
            return

        xmin_new = min(xmin + deltax, xmax)
        xmax_new = max(xmax + deltax, xmin)
        ymin_new = min(ymin + deltay, ymax)
        ymax_new = max(ymax + deltay, ymin)

        if move_info.source == self.vertices[0]:  # bottom left
            self._selection.set_value(self, (xmin_new, xmax, ymin_new, ymax))
        if move_info.source == self.vertices[1]:  # bottom right
            self._selection.set_value(self, (xmin, xmax_new, ymin_new, ymax))
        if move_info.source == self.vertices[2]:  # top left
            self._selection.set_value(self, (xmin_new, xmax, ymin, ymax_new))
        if move_info.source == self.vertices[3]:  # top right
            self._selection.set_value(self, (xmin, xmax_new, ymin, ymax_new))
        # if event source was an edge and selector is resizable, move the edge that caused the event
        if move_info.source == self.edges[0]:
            self._selection.set_value(self, (xmin_new, xmax, ymin, ymax))
        if move_info.source == self.edges[1]:
            self._selection.set_value(self, (xmin, xmax_new, ymin, ymax))
        if move_info.source == self.edges[2]:
            self._selection.set_value(self, (xmin, xmax, ymin_new, ymax))
        if move_info.source == self.edges[3]:
            self._selection.set_value(self, (xmin, xmax, ymin, ymax_new))

    def _move_to_pointer(self, ev):
        pass
