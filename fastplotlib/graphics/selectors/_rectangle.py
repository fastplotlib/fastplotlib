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
            hover_responsive=self.edges,
            arrow_keys_modifier=arrow_keys_modifier,
            axis=axis,
            parent=parent,
            name=name,
            offset=offset,
        )

        self._set_world_object(group)

        self.selection = selection

    def get_selected_data(self):
        pass

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


        pass

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

        # if event source was an edge and selector is resizable, move the edge that caused the event
        if self._move_info.source == self.edges[0]:
            self._selection.set_value(self, (xmin_new, xmax, ymin, ymax))
        if self._move_info.source == self.edges[1]:
            self._selection.set_value(self, (xmin, xmax_new, ymin, ymax))
        if self._move_info.source == self.edges[2]:
            self._selection.set_value(self, (xmin, xmax, ymin_new, ymax))
        if self._move_info.source == self.edges[3]:
            self._selection.set_value(self, (xmin, xmax, ymin, ymax_new))
