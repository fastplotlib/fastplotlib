import warnings
from typing import *

from dataclasses import dataclass
from numbers import Real

import numpy as np
import pygfx

from .._base import Graphic
from .._collection_base import GraphicCollection
from ..features._selection_features import PolygonSelectionFeature
from ._base_selector import BaseSelector, render_queue


@dataclass
class MoveInfo:
    """Movement info specific to the polygon selector."""

    # The interaction mode: None, 'create', or 'drag'
    mode: str

    # The index of the point in the polygon that is currently being manipulated
    index: int

    # The index of the point in the polygon to snap to. This is used to merge (i.e. delete) points, and to finish se the polygon.
    snap_index: int

    # The position of the cursor at the start of a drag
    start_pos: np.ndarray | None

    # The position of the vertices at the start of a drag
    start_positions: np.ndarray | None


class PolygonSelector(BaseSelector):
    _features = {"selection": PolygonSelectionFeature}

    @property
    def parent(self) -> Graphic | None:
        """Graphic that selector is associated with."""
        return self._parent

    @property
    def selection(self) -> np.ndarray[float]:
        """
        The polygon as an array of 3D points. The shape is [n_points, 3].
        """
        return self._selection.value.copy()

    @selection.setter
    def selection(self, selection: np.ndarray[float]):
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
        selection: Optional[Sequence[Tuple[float]]],
        limits: Sequence[float],
        parent: Graphic = None,
        resizable: bool = True,
        fill_color=(0, 0, 0.35),
        edge_color=(0.8, 0.6, 0),
        edge_thickness: float = 4,
        vertex_color=(0.7, 0.4, 0),
        vertex_size: float = 12,
        name: str = None,
    ):
        self._parent = parent
        self._resizable = bool(resizable)

        BaseSelector.__init__(self, name=name, parent=parent)
        self._move_info = MoveInfo("none", -1, -1, None, None)

        # Initialize geometry with space for 8 points. The buffers are oversized, so we only need to create new buffers when the allocated space is full.
        # The points are 3D, even though the z-component is always 0. Indices represent the faces (i.e. the triangles).
        self.geometry = pygfx.Geometry(
            positions=np.zeros((8, 3), np.float32),
            indices=np.zeros((8, 3), np.int32),
        )

        # The draw range allows us to draw only part of the buffer, i.e. it allows us to oversize our buffers to avoid creating a new one for every added point.
        self.geometry.positions.draw_range = 0, 0
        self.geometry.indices.draw_range = 0, 0

        self._line = pygfx.Line(
            self.geometry,
            pygfx.LineMaterial(
                thickness=edge_thickness,
                color=edge_color,
                alpha_mode="blend",
                aa=True,
                render_queue=render_queue,
                depth_test=False,
                depth_write=False,
                pick_write=True,
            ),
        )
        self._points = pygfx.Points(
            self.geometry,
            pygfx.PointsMaterial(
                size=vertex_size,
                color=vertex_color,
                alpha_mode="blend",
                aa=True,
                render_queue=render_queue,
                depth_test=False,
                depth_write=False,
                pick_write=True,
            ),
        )
        self._indicator = pygfx.Points(
            pygfx.Geometry(positions=[[0, 0, 0]]),
            pygfx.PointsMaterial(
                size=15,
                color=vertex_color,
                alpha_mode="blend",
                opacity=0.3,
                aa=True,
                render_queue=render_queue,
                depth_test=False,
                depth_write=False,
            ),
        )
        self._indicator.visible = False
        self._mesh = pygfx.Mesh(
            self.geometry,
            pygfx.MeshBasicMaterial(
                color=fill_color,
                alpha_mode="blend",
                opacity=0.4,
                render_queue=render_queue,
                depth_test=False,
                depth_write=False,
                pick_write=True,
            ),
        )
        group = pygfx.Group().add(self._line, self._points, self._mesh, self._indicator)
        self._set_world_object(group)

        # Order in z, so stuff stays pickable
        self._line.local.z = 0.1
        self._points.local.z = 0.2

        if selection is None:
            selection = []
        self._selection = PolygonSelectionFeature(selection, (0, 0, 0, 0))

        self.edge_color = edge_color
        self.edge_width = edge_thickness
        self.limits = limits
        self.selection = self.selection  # trigger positions to be created

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
            return source.data[ixs[:, 1], ixs[:, 0]]

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
            | array of (x, y) indices if the graphic is an image
            | list of indices along the x-dimension for each line if graphic is a line collection
            | array of indices along the x-dimension if graphic is a line
        """
        # get indices from source
        source = self._get_source(graphic)

        # selector (xmin, xmax, ymin, ymax) values
        polygon = self.selection[:, :2]

        # Empty ...
        if len(polygon) == 0:
            if "Image" in source.__class__.__name__:
                return np.zeros((0, 2), np.int32)
            if "Line" in source.__class__.__name__:
                if isinstance(source, GraphicCollection):
                    return [np.zeros((0, 1), np.int32) for _ in source.graphics]
                else:
                    return np.zeros((0, 1), np.int32)

        # Get bounding box to be able to do first selection
        xmin, xmax = polygon[:, 0].min(), polygon[:, 0].max()
        ymin, ymax = polygon[:, 1].min(), polygon[:, 1].max()

        # image data does not need to check for mode because the selector is always bounded
        # to the image
        if "Image" in source.__class__.__name__:
            shape = source.data.value.shape
            col_ixs = np.arange(max(0, xmin), min(xmax, shape[1] - 1), dtype=int)
            row_ixs = np.arange(max(0, ymin), min(ymax, shape[0] - 1), dtype=int)
            indices = []
            for y in row_ixs:
                for x in col_ixs:
                    p = np.array([x, y], np.float32)
                    if point_in_polygon((x, y), polygon):
                        indices.append(p)
            return np.array(indices, np.int32).reshape(-1, 2)

        if "Line" in source.__class__.__name__:
            if isinstance(source, GraphicCollection):
                ixs = list()
                for g in source.graphics:
                    points = g.data.value[:, :2] + g.offset[:2]
                    g_ixs = np.where(
                        (points[:, 0] >= xmin)
                        & (points[:, 0] <= xmax)
                        & (points[:, 1] >= ymin)
                        & (points[:, 1] <= ymax)
                    )[0]
                    g_ixs = np.array(
                        [i for i in g_ixs if point_in_polygon(points[i], polygon)],
                        g_ixs.dtype,
                    )
                    ixs.append(g_ixs)
            else:
                # map only this graphic
                points = source.data.value[:2]
                ixs = np.where(
                    (points[:, 0] >= xmin)
                    & (points[:, 0] <= xmax)
                    & (points[:, 1] >= ymin)
                    & (points[:, 1] <= ymax)
                )[0]
                ixs = np.array(
                    [i for i in ixs if point_in_polygon(points[i], polygon)],
                    ixs.dtype,
                )

            return ixs

    def _fpl_add_plot_area_hook(self, plot_area):
        self._plot_area = plot_area

        # pointer move to change endpoint of segment
        self._plot_area.renderer.add_event_handler(
            self._on_pointer_down, "pointer_down"
        )
        self._plot_area.renderer.add_event_handler(
            self._on_pointer_move, "pointer_move"
        )
        self._plot_area.renderer.add_event_handler(self._on_pointer_up, "pointer_up")

        self.position_z = len(self._plot_area) + 10

        if len(self.selection) == 0:
            self._start_move_mode("create", -1)

    def start_new_polygon(self):
        """Remove the current polygon and start drawing a new one."""
        self.selection = np.zeros((0, 3), np.float32)
        self._start_move_mode("create", -1)

    def _start_move_mode(self, what, index, start_pos=None):
        self._plot_area.controller.enabled = False
        self._move_info.mode = what
        self._move_info.index = index
        self._move_info.snap_index = None
        self._indicator.material.size = 15
        self._indicator.visible = True
        if start_pos is not None:
            self._move_info.start_pos = start_pos
            self._move_info.start_positions = self.selection.copy()
            self._indicator.visible = False

    def _end_move_mode(self):
        if self._move_info.mode == "create":
            self.world_object.children[0].material.loop = True
        self._plot_area.controller.enabled = True
        self._move_info.mode = None
        self._move_info.start_pos = None
        self._move_info.start_positions = None
        self._indicator.visible = False

    def _on_pointer_down(self, ev):
        world_pos = self._plot_area.map_screen_to_world(ev)
        if world_pos is None:
            return

        if self._move_info.mode == "create":
            # Add a polygon or finish it
            if self._move_info.snap_index is not None:
                pass  # on release we finish the polygon
            else:
                self._insert_polygon_vertex(999999, world_pos)

        elif self._move_info.mode is None:
            # Maybe initiate a drag
            if ev.target is self._points:
                index = ev.pick_info["vertex_index"]
                self._start_move_mode("drag", index)
            elif ev.target is self._line:
                index = ev.pick_info["vertex_index"]
                if ev.pick_info["segment_coord"] > 0:
                    index += 1
                self._insert_polygon_vertex(index, world_pos)
                self._start_move_mode("drag", index)
            elif ev.target is self._mesh:
                index = None  # move whole polygon
                self._start_move_mode("drag", index, world_pos)

    def _on_pointer_move(self, ev):
        """After mouse pointer move event, moves endpoint of current line segment"""
        if self._move_info.mode is None:
            return
        world_pos = self._plot_area.map_screen_to_world((ev.x, ev.y))
        if world_pos is None:
            return

        # Are we close to a point that we can snap to?
        # The concept of snapping does multiple things:
        # - preventing the user from creating points that are very close to each-other,
        # - allowing the user to finish the polygon by connecting to the start-point when in 'create' mode.
        # - allowing the user to merge points by dragging one onto its neighbour.
        index = self._move_info.index
        snap_index = None

        # Use numpy to select the nearest point.
        # This is because we cannot use picking on the actual points because
        # then we'd always pick the point being moved. We don't use a depth buffer
        # so we cannot move the point backwards to avoid it being picked.
        # An advantage is that we can make the snap-radius larger than the size of the points.
        world_pos2 = self._plot_area.map_screen_to_world((ev.x + 1, ev.y))
        world_pos_scale = float(np.linalg.norm(world_pos - world_pos2))
        snap_radius = 20  # logical screen pixels
        if len(self.selection) > 0:
            distances = np.linalg.norm(self.selection[:, :2] - world_pos[:2], axis=1)
            distances /= world_pos_scale
            distances[index] = np.inf
            snap_index = int(np.argmin(distances))
            if distances[snap_index] > snap_radius:
                snap_index = None

        if snap_index == index:  # just in case, dont snap to moving point
            snap_index = None
        if len(self.selection) < 4:
            snap_index = None
        if self._move_info.mode == "create" and snap_index != 0:
            snap_index = None
        if self._move_info.mode == "drag" and index is not None:
            last_index = len(self.selection) - 1
            if not (
                (index == 0 and snap_index == last_index)
                or (index == last_index and snap_index == 0)
                or (snap_index in (index - 1, index + 1))
            ):
                snap_index = None
        self._move_info.snap_index = snap_index

        # Show state of snap index to user
        if snap_index is not None:
            world_pos = self.geometry.positions.data[snap_index]
            self._indicator.material.size = 30
        else:
            self._indicator.material.size = 15

        # Move the positions being moved a bit down in depth, so its de-preferred in picking
        world_pos = (world_pos[0], world_pos[1], -0.05)

        self._indicator.local.position = world_pos

        # Update data
        if self._move_info.mode in ("create", "drag"):
            data = self.selection
            if len(data) > 0:
                if self._move_info.index is None:
                    delta = world_pos - self._move_info.start_pos
                    data[:] = self._move_info.start_positions + delta
                else:
                    data[self._move_info.index] = world_pos
                self._selection.set_value(self, data)

    def _on_pointer_up(self, ev):
        if self._move_info.mode in ("create", "drag"):
            # Update data to set depth (z) to zero again
            data = self.selection
            data[:, 2] = 0
            self._selection.set_value(self, data)
            # If we snapped, we dissolve (i.e. delete the vertex being moved)
            if self._move_info.snap_index is not None:
                assert self._move_info.index is not None
                self._delete_polygon_vertex(self._move_info.index)

        # Moving the mouse up may end the move action
        if self._move_info.mode == "create":
            if self._move_info.snap_index is not None:
                self._end_move_mode()
        elif self._move_info.mode == "drag":
            self._end_move_mode()

    def _insert_polygon_vertex(self, i, world_pos):
        selection = self.selection
        if len(selection) == 0:
            data = np.vstack([selection, world_pos, world_pos])
        else:
            data = np.vstack([selection[:i], world_pos, selection[i:]])
        self._selection.set_value(self, data)

    def _delete_polygon_vertex(self, i):
        selection = self.selection
        if i < 0:
            data = selection[:i]
        else:
            data = np.vstack([selection[:i], selection[i + 1 :]])
        self._selection.set_value(self, data)


def is_left(p0, p1, p2):
    """Test if point p2 is left of the line formed by p0 → p1"""
    return (p1[0] - p0[0]) * (p2[1] - p0[1]) - (p2[0] - p0[0]) * (p1[1] - p0[1])


def point_in_polygon(point, polygon):
    """Determines if the point is inside the polygon using the winding number algorithm."""
    wn = 0  # winding number counter
    n = len(polygon)

    for i in range(n):
        p0 = polygon[i]
        p1 = polygon[(i + 1) % n]

        if p0[1] <= point[1]:  # start y <= point.y
            if p1[1] > point[1]:  # upward crossing
                if is_left(p0, p1, point) > 0:
                    wn += 1  # point is left of edge
        else:  # start y > point.y
            if p1[1] <= point[1]:  # downward crossing
                if is_left(p0, p1, point) < 0:
                    wn -= 1  # point is right of edge

    return wn != 0
