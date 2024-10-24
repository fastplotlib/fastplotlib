from numbers import Real
from typing import Sequence

import numpy as np
import pygfx

from .._base import Graphic
from .._collection_base import GraphicCollection
from .._features._selection_features import LinearRegionSelectionFeature
from ._base_selector import BaseSelector


class LinearRegionSelector(BaseSelector):
    @property
    def parent(self) -> Graphic | None:
        """graphic that the selector is associated with"""
        return self._parent

    @property
    def selection(self) -> np.ndarray[float]:
        """
        (min, max) of selector along selector's axis
        """
        # TODO: This probably does not account for rotation since world.position
        #  does not account for rotation, we can do this later

        return self._selection.value.copy()

        # TODO: if no parent graphic is set, this just returns values in world space
        #  but should we change it?

    @selection.setter
    def selection(self, selection: Sequence[float]):
        # set (min, max) of the selector in data space
        graphic = self._parent

        self._selection.set_value(self, selection)

    @property
    def limits(self) -> tuple[float, float]:
        return self._limits

    @limits.setter
    def limits(self, values: tuple[float, float]):
        # check that `values` is an iterable of two real numbers
        # using `Real` here allows it to work with builtin `int` and `float` types, and numpy scaler types
        if len(values) != 2 or not all(map(lambda v: isinstance(v, Real), values)):
            raise TypeError("limits must be an iterable of two numeric values")
        self._limits = tuple(
            map(round, values)
        )  # if values are close to zero things get weird so round them
        self._selection._limits = self._limits

    def __init__(
        self,
        selection: Sequence[float],
        limits: Sequence[float],
        size: float,
        center: float,
        axis: str = "x",
        parent: Graphic = None,
        resizable: bool = True,
        fill_color: str | Sequence[float] = (0, 0, 0.35),
        edge_color: str | Sequence[float] = (0.8, 0.6, 0),
        edge_thickness: float = 8,
        arrow_keys_modifier: str = "Shift",
        name: str = None,
    ):
        """
        Create a LinearRegionSelector graphic which can be moved only along either the x-axis or y-axis.
        Allows sub-selecting data from a parent ``Graphic`` or from multiple Graphics.

        Assumes that the data under the selector is a function of the axis on which the selector moves
        along. Example: if the selector is along the x-axis, then there must be only one y-value for each
        x-value, otherwise methods such as ``get_selected_data()`` do not make sense.

        Parameters
        ----------
        selection: (float, float)
            initial (min, max) x or y values

        limits: (float, float)
            (min limit, max limit) within which the selector can move

        size: int
            usually the data range, height or width of the selector

        center: float
            usually the data mean, center offset of the selector on the orthogonal axis

        axis: str, default "x"
            "x" | "y", axis along which the selector can move

        parent: ``Graphic`` instance, default ``None``
            associate this selector with a parent ``Graphic`` from which to fetch data or indices

        resizable: bool
            if ``True``, the edges can be dragged to change the range of the selection

        fill_color: str, array, or tuple
            fill color for the selector, passed to pygfx.Color

        edge_color: str, array, or tuple
            edge color for the selector, passed to pygfx.Color

        edge_thickness: float, default 8
            edge thickness

        arrow_keys_modifier: str
            modifier key that must be pressed to initiate movement using arrow keys, must be one of:
            "Control", "Shift", "Alt" or ``None``

        name: str, optional
            name of this selector graphic

        """
        self._edge_color = pygfx.Color(edge_color)
        self._fill_color = pygfx.Color(fill_color)
        self._vertex_color = None

        # lots of very close to zero values etc. so round them, otherwise things get weird
        if not len(selection) == 2:
            raise ValueError

        selection = np.asarray(selection)

        if not len(limits) == 2:
            raise ValueError

        self._limits = np.asarray(limits)

        # TODO: sanity checks, we recommend users to add LinearSelection using the add_linear_selector() methods
        # TODO: so we can worry about the sanity checks later

        group = pygfx.Group()

        if axis == "x":
            mesh = pygfx.Mesh(
                pygfx.box_geometry(1, size, 1),
                pygfx.MeshBasicMaterial(
                    color=pygfx.Color(self.fill_color), pick_write=True
                ),
            )

        elif axis == "y":
            mesh = pygfx.Mesh(
                pygfx.box_geometry(size, 1, 1),
                pygfx.MeshBasicMaterial(
                    color=pygfx.Color(self.fill_color), pick_write=True
                ),
            )
        else:
            raise ValueError("`axis` must be one of 'x' or 'y'")

        # the fill of the selection
        self.fill = mesh
        # no x, y offsets for linear region selector
        # everything is done by setting the mesh data
        # and line positions
        self.fill.world.position = (0, 0, -2)

        group.add(self.fill)

        self._resizable = resizable

        if axis == "x":
            # just some data to initialize the edge lines
            init_line_data = np.array([[0, -size / 2, 0], [0, size / 2, 0]]).astype(
                np.float32
            )

        elif axis == "y":
            # just some line data to initialize y axis edge lines
            init_line_data = np.array(
                [
                    [-size / 2, 0, 0],
                    [size / 2, 0, 0],
                ]
            ).astype(np.float32)

        else:
            raise ValueError("axis argument must be one of 'x' or 'y'")

        line0 = pygfx.Line(
            pygfx.Geometry(
                positions=init_line_data.copy()
            ),  # copy so the line buffer is isolated
            pygfx.LineMaterial(
                thickness=edge_thickness, color=self.edge_color, pick_write=True
            ),
        )
        line1 = pygfx.Line(
            pygfx.Geometry(
                positions=init_line_data.copy()
            ),  # copy so the line buffer is isolated
            pygfx.LineMaterial(
                thickness=edge_thickness, color=self.edge_color, pick_write=True
            ),
        )

        self.edges: tuple[pygfx.Line, pygfx.Line] = (line0, line1)

        # add the edge lines
        for edge in self.edges:
            edge.world.z = -0.5
            group.add(edge)

        # TODO: if parent offset changes, we should set the selector offset too, use offset evented property
        # TODO: add check if parent is `None`, will throw error otherwise
        if axis == "x":
            offset = (parent.offset[0], center + parent.offset[1], 0)
        elif axis == "y":
            offset = (center + parent.offset[1], parent.offset[1], 0)

        # set the initial bounds of the selector
        # compensate for any offset from the parent graphic
        # selection feature only works in world space, not data space
        self._selection = LinearRegionSelectionFeature(
            selection, axis=axis, limits=self._limits
        )

        self._pygfx_event = None

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

    def get_selected_data(
        self, graphic: Graphic = None
    ) -> np.ndarray | list[np.ndarray]:
        """
        Get the ``Graphic`` data bounded by the current selection.
        Returns a view of the data array.

        If the ``Graphic`` is a collection, such as a ``LineStack``, it returns a list of views of the full array.
        Can be performed on the ``parent`` Graphic or on another graphic by passing to the ``graphic`` arg.

        **NOTE:** You must be aware of the axis for the selector. The sub-selected data that is returned will be of
        shape ``[n_points_selected, 3]``. If you have selected along the x-axis then you can access y-values of the
        subselection like this: sub[:, 1]. Conversely, if you have selected along the y-axis then you can access the
        x-values of the subselection like this: sub[:, 0].

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

        if "Line" in source.__class__.__name__:
            if isinstance(source, GraphicCollection):
                # this will return a list of views of the arrays, therefore no copy operations occur
                # it's fine and fast even as a list of views because there is no re-allocating of memory
                # this is fast even for slicing a 10,000 x 5,000 LineStack
                data_selections: list[np.ndarray] = list()

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

                return source.data[s]
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

        if "Image" in source.__class__.__name__:
            s = slice(ixs[0], ixs[-1] + 1)

            if self.axis == "x":
                # slice columns
                return source.data[:, s]

            elif self.axis == "y":
                # slice rows
                return source.data[s]

    def get_selected_indices(
        self, graphic: Graphic = None
    ) -> np.ndarray | list[np.ndarray]:
        """
        Returns the indices of the ``Graphic`` data bounded by the current selection.

        These are the data indices along the selector's "axis" which correspond to the data under the selector.

        Parameters
        ----------
        graphic: Graphic, optional
            if provided, returns the selection indices from this graphic instead of the graphic set as ``parent``

        Returns
        -------
        Union[np.ndarray, List[np.ndarray]]
            data indices of the selection, list of np.ndarray if graphic is a collection

        """
        # we get the indices from the source graphic
        source = self._get_source(graphic)

        # get the offset of the source graphic
        if self.axis == "x":
            dim = 0
        elif self.axis == "y":
            dim = 1

        # selector (min, max) data values along axis
        bounds = self.selection

        if (
            "Line" in source.__class__.__name__
            or "Scatter" in source.__class__.__name__
        ):
            # gets indices corresponding to n_datapoints dim
            # data is [n_datapoints, xyz], so we return
            # indices that can be used to slice `n_datapoints`
            if isinstance(source, GraphicCollection):
                ixs = list()
                for g in source.graphics:
                    # indices for each graphic in the collection
                    data = g.data[:, dim]
                    g_ixs = np.where((data >= bounds[0]) & (data <= bounds[1]))[0]
                    ixs.append(g_ixs)
            else:
                # map this only this graphic
                data = source.data[:, dim]
                ixs = np.where((data >= bounds[0]) & (data <= bounds[1]))[0]

            return ixs

        if "Image" in source.__class__.__name__:
            # indices map directly to grid geometry for image data buffer
            return np.arange(*bounds, dtype=int)

    def _move_graphic(self, delta: np.ndarray):
        # add delta to current min, max to get new positions
        if self.axis == "x":
            # add x value
            new_min, new_max = self.selection + delta[0]

        elif self.axis == "y":
            # add y value
            new_min, new_max = self.selection + delta[1]

        # move entire selector if event source was fill
        if self._move_info.source == self.fill:
            # prevent weird shrinkage of selector if one edge is already at the limit
            if self.selection[0] == self.limits[0] and new_min < self.limits[0]:
                # self._move_end(None)  # TODO: cancel further movement to prevent weird asynchronization with pointer
                return
            if self.selection[1] == self.limits[1] and new_max > self.limits[1]:
                # self._move_end(None)
                return

            # move entire selector
            self._selection.set_value(self, (new_min, new_max))
            return

        # if selector is not resizable return
        if not self._resizable:
            return

        # if event source was an edge and selector is resizable,
        # move the edge that caused the event
        if self._move_info.source == self.edges[0]:
            # change only left or bottom bound
            self._selection.set_value(self, (new_min, self._selection.value[1]))

        elif self._move_info.source == self.edges[1]:
            # change only right or top bound
            self._selection.set_value(self, (self.selection[0], new_max))
