from typing import *
from numbers import Real

import numpy as np
import pygfx

from ...utils.gui import IS_JUPYTER
from .._base import Graphic, GraphicCollection
from .._features._selection_features import LinearRegionSelectionFeature
from ._base_selector import BaseSelector


if IS_JUPYTER:
    # If using the jupyter backend, user has jupyter_rfb, and thus also ipywidgets
    import ipywidgets


class LinearRegionSelector(BaseSelector):
    @property
    def selection(self) -> tuple[int, int] | List[tuple[int, int]]:
        """
        (min, max) of data value along selector's axis, in data space
        """
        # TODO: This probably does not account for rotation since world.position
        #  does not account for rotation, we can do this later
        if self._parent is not None:
            # just subtract parent offset to map from world to data space
            if self.axis == "x":
                offset = self._parent.offset[0]
            elif self.axis == "y":
                offset = self._parent.offset[1]

            return self._selection.value.copy() - offset

            #
            # indices = self.get_selected_indices()
            # if isinstance(indices, np.ndarray):
            #     # this can be used directly to create a range object
            #     return indices[0], indices[-1] + 1
            # # if a collection is under the selector
            # elif isinstance(indices, list):
            #     ranges = list()
            #     for ixs in indices:
            #         ranges.append((ixs[0], ixs[-1] + 1))
            #
            #     return ranges

        # TODO: if no parent graphic is set, this just returns world positions
        #  but should we change it?
        return self._selection.value

    @selection.setter
    def selection(self, selection: tuple[int, int]):
        # set (xmin, xmax), or (ymin, ymax) of the selector in data space
        graphic = self._parent

        start, stop = selection

        if isinstance(graphic, GraphicCollection):
            pass

        if self.axis == "x":
            offset = graphic.offset[0]
        elif self.axis == "y":
            offset = graphic.offset[1]

        # add the offset
        start += offset
        stop += offset

        self._selection.set_value(self, (start, stop))

    @property
    def limits(self) -> Tuple[float, float]:
        return self._limits

    @limits.setter
    def limits(self, values: Tuple[float, float]):
        # check that `values` is an iterable of two real numbers
        # using `Real` here allows it to work with builtin `int` and `float` types, and numpy scaler types
        if len(values) != 2 or not all(map(lambda v: isinstance(v, Real), values)):
            raise TypeError("limits must be an iterable of two numeric values")
        self._limits = tuple(
            map(round, values)
        )  # if values are close to zero things get weird so round them
        self.selection._limits = self._limits

    def __init__(
            self,
            selection: Tuple[int, int],
            limits: Tuple[int, int],
            size: tuple[float, float],
            center: float,
            axis: str = "x",
            parent: Graphic = None,
            resizable: bool = True,
            fill_color=(0, 0, 0.35),
            edge_color=(0.8, 0.8, 0),
            edge_thickness: int = 3,
            arrow_keys_modifier: str = "Shift",
            name: str = None,
    ):
        """
        Create a LinearRegionSelector graphic which can be moved only along either the x-axis or y-axis.
        Allows sub-selecting data from a ``Graphic`` or from multiple Graphics.

        bounds[0], limits[0], and position[0] must be identical.

        Holding the right mouse button while dragging an edge will force the entire region selector to move. This is
        a when using transparent fill areas due to ``pygfx`` picking limitations.

        **Note:** Events get very weird if the values of bounds, limits and origin are close to zero. If you need
        a linear selector with small data, we recommend scaling the data and then using the selector.

        Parameters
        ----------
        selection: (int, int)
            (min, max) values of the "axis" under the selector

        limits: (int, int)
            (min limit, max limit) of values on the axis

        size: int
            height or width of the selector

        axis: str, default "x"
            "x" | "y", axis for the selector

        parent: Graphic, default ``None``
            associate this selector with a parent Graphic

        resizable: bool
            if ``True``, the edges can be dragged to resize the width of the linear selection

        fill_color: str, array, or tuple
            fill color for the selector, passed to pygfx.Color

        edge_color: str, array, or tuple
            edge color for the selector, passed to pygfx.Color

        arrow_keys_modifier: str
            modifier key that must be pressed to initiate movement using arrow keys, must be one of:
            "Control", "Shift", "Alt" or ``None``

        name: str
            name for this selector graphic

        Features
        --------

        selection: :class:`.LinearRegionSelectionFeature`
            ``selection()`` returns the current selector bounds in world coordinates.
            Use ``get_selected_indices()`` to return the selected indices in data
            space, and ``get_selected_data()`` to return the selected data.
            Use ``selection.add_event_handler()`` to add callback functions that are
            called when the LinearSelector selection changes. See feature class for
            event pick_info table.

        """

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

        mesh_size = np.ptp(size)

        if axis == "x":
            mesh = pygfx.Mesh(
                pygfx.box_geometry(1, mesh_size, 1),
                pygfx.MeshBasicMaterial(color=pygfx.Color(fill_color), pick_write=True),
            )

        elif axis == "y":
            mesh = pygfx.Mesh(
                pygfx.box_geometry(mesh_size, 1, 1),
                pygfx.MeshBasicMaterial(color=pygfx.Color(fill_color), pick_write=True),
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
            init_line_data = np.array(
                [
                    [0, size[0], 0],
                    [0, size[1], 0]
                ]
            ).astype(np.float32)

            if parent is not None:
                parent_offset = parent.offset[0]
            else:
                parent_offset = 0

        elif axis == "y":
            # just some line data to initialize y axis edge lines
            init_line_data = np.array(
                [
                    [size[0], 0, 0],
                    [size[1], 0, 0],
                ]
            ).astype(np.float32)

            if parent is not None:
                parent_offset = parent.offset[1]
            else:
                parent_offset = 0

        else:
            raise ValueError("axis argument must be one of 'x' or 'y'")

        line0 = pygfx.Line(
            pygfx.Geometry(positions=init_line_data.copy()),  # copy so the line buffer is isolated
            pygfx.LineMaterial(
                thickness=edge_thickness, color=edge_color, pick_write=True
            ),
        )
        line1 = pygfx.Line(
            pygfx.Geometry(positions=init_line_data.copy()),  # copy so the line buffer is isolated
            pygfx.LineMaterial(
                thickness=edge_thickness, color=edge_color, pick_write=True
            ),
        )

        self.edges: Tuple[pygfx.Line, pygfx.Line] = (line0, line1)

        # add the edge lines
        for edge in self.edges:
            edge.world.z = -0.5
            group.add(edge)

        # set the initial bounds of the selector
        # compensate for any offset from the parent graphic
        # selection feature only works in world space, not data space
        self._selection = LinearRegionSelectionFeature(
            selection + parent_offset,
            axis=axis,
            limits=self._limits + parent_offset
        )

        print(f"sel value after construct: {selection}")

        self._handled_widgets = list()
        self._block_ipywidget_call = False
        self._pygfx_event = None

        BaseSelector.__init__(
            self,
            edges=self.edges,
            fill=(self.fill,),
            hover_responsive=self.edges,
            arrow_keys_modifier=arrow_keys_modifier,
            axis=axis,
            name=name,
            parent=parent
        )

        self._set_world_object(group)

        self.selection = selection

        print(f"sel value after set: {selection}")

        if self.axis == "x":
            offset = (0, center, 0)
        elif self.axis == "y":
            offset = (center, 0, 0)

        self.offset = self.offset + offset

    def get_selected_data(
            self, graphic: Graphic = None
    ) -> Union[np.ndarray, List[np.ndarray]]:
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

        if "Line" in source.__class__.__name__:
            if isinstance(source, GraphicCollection):
                # this will return a list of views of the arrays, therefore no copy operations occur
                # it's fine and fast even as a list of views because there is no re-allocating of memory
                # this is fast even for slicing a 10,000 x 5,000 LineStack
                data_selections: List[np.ndarray] = list()

                for i, g in enumerate(source.graphics):
                    # if ixs[i].size == 0:
                    #     data_selections.append(np.array([], dtype=np.float32))
                    # else:
                    s = slice(ixs[i][0], ixs[i][-1])
                    # slices n_datapoints dim
                    data_selections.append(g.data.buffer.data[s])

                return source[:].data[s]
            else:
                # just for one graphic
                # if ixs.size == 0:
                #     return np.array([], dtype=np.float32)

                s = slice(ixs[0], ixs[-1])
                # slices n_datapoints dim
                return source.data.buffer.data[s]

        if "Image" in source.__class__.__name__:
            s = slice(ixs[0], ixs[-1])

            if self.axis == "x":
                return source.data.value[:, s]

            elif self.axis == "y":
                return source.data.value[s]

    def get_selected_indices(
            self, graphic: Graphic = None
    ) -> Union[np.ndarray, List[np.ndarray]]:
        """
        Returns the indices of the ``Graphic`` data bounded by the current selection.
        This is useful because the ``bounds`` min and max are not necessarily the same
        as the Line Geometry positions x-vals or y-vals. For example, if if you used a
        np.linspace(0, 100, 1000) for xvals in your line, then you will have 1,000
        x-positions. If the selection ``bounds`` are set to ``(0, 10)``, the returned
        indices would be ``(0, 100)``.

        Parameters
        ----------
        graphic: Graphic, optional
            if provided, returns the selection indices from this graphic instead of the graphic set as ``parent``

        Returns
        -------
        Union[np.ndarray, List[np.ndarray]]
            data indices of the selection, list of np.ndarray if graphic is LineCollection

        """
        # we get the indices from the source graphic
        source = self._get_source(graphic)

        # get the offset of the source graphic
        if self.axis == "x":
            source_offset = source.offset[0]
            dim = 0
        elif self.axis == "y":
            source_offset = source.offset[1]
            dim = 1

        # selector (min, max) in world space
        bounds = self._selection.value
        # subtract offset to get the (min, max) bounded region
        # of the source graphic in world space
        bounds = tuple(v - source_offset for v in bounds)

        # # need them to be int to use as indices
        # offset_bounds = tuple(map(int, offset_bounds))

        if "Line" in source.__class__.__name__:
            # now we need to map from world space to data space
            # gets indices corresponding to n_datapoints dim
            # data space is [n_datapoints, xyz], so we return
            # indices that can be used to slice `n_datapoints`
            if isinstance(source, GraphicCollection):
                ixs = list()
                for g in source.graphics:
                    # map for each graphic in the collection
                    g_ixs = np.where(
                        (g.data.value[:, dim] >= bounds[0])
                        & (g.data.value[:, dim] <= bounds[1])
                    )[0]
                    ixs.append(g_ixs)
            else:
                # map this only this graphic
                ixs = np.where(
                    (source.data.value[:, dim] >= bounds[0])
                    & (source.data.value[:, dim] <= bounds[1])
                )[0]

            return ixs

        if "Image" in source.__class__.__name__:
            # indices map directly to grid geometry for image data buffer
            ixs = np.arange(*bounds, dtype=int)
            return ixs

    def make_ipywidget_slider(self, kind: str = "IntRangeSlider", **kwargs):
        """
        Makes and returns an ipywidget slider that is associated to this LinearSelector

        Parameters
        ----------
        kind: str
            "IntRangeSlider" or "FloatRangeSlider"

        kwargs
            passed to the ipywidget slider constructor

        Returns
        -------
        ipywidgets.Intslider or ipywidgets.FloatSlider

        """

        if not IS_JUPYTER:
            raise ImportError(
                "Must installed `ipywidgets` to use `make_ipywidget_slider()`"
            )

        if kind not in ["IntRangeSlider", "FloatRangeSlider"]:
            raise TypeError(
                f"`kind` must be one of: 'IntRangeSlider', or 'FloatRangeSlider'\n"
                f"You have passed: '{kind}'"
            )

        cls = getattr(ipywidgets, kind)

        value = self.selection
        if "Int" in kind:
            value = tuple(map(int, self.selection))

        slider = cls(
            min=self.limits[0],
            max=self.limits[1],
            value=value,
            **kwargs,
        )
        self.add_ipywidget_handler(slider)

        return slider

    def add_ipywidget_handler(self, widget, step: Union[int, float] = None):
        """
        Bidirectionally connect events with a ipywidget slider

        Parameters
        ----------
        widget: ipywidgets.IntRangeSlider or ipywidgets.FloatRangeSlider
            ipywidget slider to connect to

        step: int or float, default ``None``
            step size, if ``None`` 100 steps are created

        """
        if not isinstance(
                widget, (ipywidgets.IntRangeSlider, ipywidgets.FloatRangeSlider)
        ):
            raise TypeError(
                f"`widget` must be one of: ipywidgets.IntRangeSlider or ipywidgets.FloatRangeSlider\n"
                f"You have passed a: <{type(widget)}"
            )

        if step is None:
            step = (self.limits[1] - self.limits[0]) / 100

        if isinstance(widget, ipywidgets.IntSlider):
            step = int(step)

        widget.step = step

        self._setup_ipywidget_slider(widget)

    def _setup_ipywidget_slider(self, widget):
        # setup an ipywidget slider with bidirectional callbacks to this LinearSelector
        value = self.selection

        if isinstance(widget, ipywidgets.IntSlider):
            value = tuple(map(int, value))

        widget.value = value

        # user changes widget -> linear selection changes
        widget.observe(self._ipywidget_callback, "value")

        # user changes linear selection -> widget changes
        self.selection.add_event_handler(self._update_ipywidgets)

        self._plot_area.renderer.add_event_handler(self._set_slider_layout, "resize")

        self._handled_widgets.append(widget)

    def _update_ipywidgets(self, ev):
        # update the ipywidget sliders when LinearSelector value changes
        self._block_ipywidget_call = True  # prevent infinite recursion

        value = ev.pick_info["new_data"]
        # update all the handled slider widgets
        for widget in self._handled_widgets:
            if isinstance(widget, ipywidgets.IntSlider):
                widget.value = tuple(map(int, value))
            else:
                widget.value = value

        self._block_ipywidget_call = False

    def _ipywidget_callback(self, change):
        # update the LinearSelector if the ipywidget value changes
        if self._block_ipywidget_call or self._moving:
            return

        self.selection = change["new"]

    def _set_slider_layout(self, *args):
        w, h = self._plot_area.renderer.logical_size

        for widget in self._handled_widgets:
            widget.layout = ipywidgets.Layout(width=f"{w}px")

    def _move_graphic(self, delta: np.ndarray):
        # add delta to current bounds to get new positions
        # print(delta)
        if self.axis == "x":
            # min and max of current bounds, i.e. the edges
            xmin, xmax = self._selection.value

            # new left bound position
            bound0_new = xmin + delta[0]

            # new right bound position
            bound1_new = xmax + delta[0]
        elif self.axis == "y":
            # min and max of current bounds, i.e. the edges
            ymin, ymax = self._selection.value

            # new bottom bound position
            bound0_new = ymin + delta[1]

            # new top bound position
            bound1_new = ymax + delta[1]

        # move entire selector if source was fill
        if self._move_info.source == self.fill:
            # set the new bounds, in WORLD space
            # don't set property because that is in data space!
            self._selection.set_value(self, (bound0_new, bound1_new))
            return

        # if selector is not resizable do nothing
        if not self._resizable:
            return

        # if resizable, move edges
        if self._move_info.source == self.edges[0]:
            # change only left or bottom bound
            self._selection.set_value(self, (bound0_new, self._selection.value[1]))

        elif self._move_info.source == self.edges[1]:
            # change only right or top bound
            self._selection.set_value(self, (self._selection.value[0], bound1_new))
        else:
            return
