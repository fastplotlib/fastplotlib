from typing import *
from numbers import Real

try:
    import ipywidgets

    HAS_IPYWIDGETS = True
except (ImportError, ModuleNotFoundError):
    HAS_IPYWIDGETS = False

import numpy as np

import pygfx

from .._base import Graphic, GraphicCollection
from ._base_selector import BaseSelector
from .._features._selection_features import LinearRegionSelectionFeature


class LinearRegionSelector(BaseSelector):
    @property
    def limits(self) -> Tuple[float, float]:
        return self._limits

    @limits.setter
    def limits(self, values: Tuple[float, float]):
        # check that `values` is an iterable of two real numbers
        # using `Real` here allows it to work with builtin `int` and `float` types, and numpy scaler types
        if len(values) != 2 or not all(map(lambda v: isinstance(v, Real), values)):
            raise TypeError(
                "limits must be an iterable of two numeric values"
            )
        self._limits = tuple(map(round, values))  # if values are close to zero things get weird so round them
        self.selection._limits = self._limits

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
        bounds = tuple(map(round, bounds))
        self._limits = tuple(map(round, limits))
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

        self.parent = parent

        # world object for this will be a group
        # basic mesh for the fill area of the selector
        # line for each edge of the selector
        group = pygfx.Group()
        self._set_world_object(group)

        if axis == "x":
            mesh = pygfx.Mesh(
                pygfx.box_geometry(1, size, 1),
                pygfx.MeshBasicMaterial(color=pygfx.Color(fill_color)),
            )

        elif axis == "y":
            mesh = pygfx.Mesh(
                pygfx.box_geometry(size, 1, 1),
                pygfx.MeshBasicMaterial(color=pygfx.Color(fill_color)),
            )
        else:
            raise ValueError("`axis` must be one of 'x' or 'y'")

        # the fill of the selection
        self.fill = mesh
        self.fill.world.position = (*origin, -2)

        self.world_object.add(self.fill)

        self._resizable = resizable

        if axis == "x":
            # position data for the left edge line
            left_line_data = np.array(
                [
                    [origin[0], (-size / 2) + origin[1], 0.5],
                    [origin[0], (size / 2) + origin[1], 0.5],
                ]
            ).astype(np.float32)

            left_line = pygfx.Line(
                pygfx.Geometry(positions=left_line_data),
                pygfx.LineMaterial(thickness=edge_thickness, color=edge_color),
            )

            # position data for the right edge line
            right_line_data = np.array(
                [
                    [bounds[1], (-size / 2) + origin[1], 0.5],
                    [bounds[1], (size / 2) + origin[1], 0.5],
                ]
            ).astype(np.float32)

            right_line = pygfx.Line(
                pygfx.Geometry(positions=right_line_data),
                pygfx.LineMaterial(thickness=edge_thickness, color=edge_color),
            )

            self.edges: Tuple[pygfx.Line, pygfx.Line] = (left_line, right_line)

        elif axis == "y":
            # position data for the left edge line
            bottom_line_data = np.array(
                [
                    [(-size / 2) + origin[0], origin[1], 0.5],
                    [(size / 2) + origin[0], origin[1], 0.5],
                ]
            ).astype(np.float32)

            bottom_line = pygfx.Line(
                pygfx.Geometry(positions=bottom_line_data),
                pygfx.LineMaterial(thickness=edge_thickness, color=edge_color),
            )

            # position data for the right edge line
            top_line_data = np.array(
                [
                    [(-size / 2) + origin[0], bounds[1], 0.5],
                    [(size / 2) + origin[0], bounds[1], 0.5],
                ]
            ).astype(np.float32)

            top_line = pygfx.Line(
                pygfx.Geometry(positions=top_line_data),
                pygfx.LineMaterial(thickness=edge_thickness, color=edge_color),
            )

            self.edges: Tuple[pygfx.Line, pygfx.Line] = (bottom_line, top_line)

        else:
            raise ValueError("axis argument must be one of 'x' or 'y'")

        # add the edge lines
        for edge in self.edges:
            edge.world.z = -1
            self.world_object.add(edge)

        # set the initial bounds of the selector
        self.selection = LinearRegionSelectionFeature(
            self, bounds, axis=axis, limits=self._limits
        )

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
            name=name
        )

    def get_selected_data(
        self, graphic: Graphic = None
    ) -> Union[np.ndarray, List[np.ndarray], None]:
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
                    if ixs[i].size == 0:
                        data_selections.append(None)
                    else:
                        s = slice(ixs[i][0], ixs[i][-1])
                        data_selections.append(g.data.buffer.data[s])

                return source[:].data[s]
            # just for one Line graphic
            else:
                if ixs.size == 0:
                    return None

                s = slice(ixs[0], ixs[-1])
                return source.data.buffer.data[s]

        if (
            "Heatmap" in source.__class__.__name__
            or "Image" in source.__class__.__name__
        ):
            s = slice(ixs[0], ixs[-1])
            if self.axis == "x":
                return source.data()[:, s]
            elif self.axis == "y":
                return source.data()[s]

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
        source = self._get_source(graphic)

        # if the graphic position is not at (0, 0) then the bounds must be offset
        offset = getattr(source, f"position_{self.selection.axis}")
        offset_bounds = tuple(v - offset for v in self.selection())

        # need them to be int to use as indices
        offset_bounds = tuple(map(int, offset_bounds))

        if self.selection.axis == "x":
            dim = 0
        else:
            dim = 1

        if "Line" in source.__class__.__name__:
            # now we need to map from graphic space to data space
            # we can have more than 1 datapoint between two integer locations in the world space
            if isinstance(source, GraphicCollection):
                ixs = list()
                for g in source.graphics:
                    # map for each graphic in the collection
                    g_ixs = np.where(
                        (g.data()[:, dim] >= offset_bounds[0])
                        & (g.data()[:, dim] <= offset_bounds[1])
                    )[0]
                    ixs.append(g_ixs)
            else:
                # map this only this graphic
                ixs = np.where(
                    (source.data()[:, dim] >= offset_bounds[0])
                    & (source.data()[:, dim] <= offset_bounds[1])
                )[0]

            return ixs

        if (
            "Heatmap" in source.__class__.__name__
            or "Image" in source.__class__.__name__
        ):
            # indices map directly to grid geometry for image data buffer
            ixs = np.arange(*self.selection(), dtype=int)
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

        if not HAS_IPYWIDGETS:
            raise ImportError(
                "Must installed `ipywidgets` to use `make_ipywidget_slider()`"
            )

        if kind not in ["IntRangeSlider", "FloatRangeSlider"]:
            raise TypeError(
                f"`kind` must be one of: 'IntRangeSlider', or 'FloatRangeSlider'\n"
                f"You have passed: '{kind}'"
            )

        cls = getattr(ipywidgets, kind)

        value = self.selection()
        if "Int" in kind:
            value = tuple(map(int, self.selection()))

        slider = cls(
            min=self.limits[0],
            max=self.limits[1],
            value=value,
            **kwargs,
        )
        self.add_ipywidget_handler(slider)

        return slider

    def add_ipywidget_handler(
            self,
            widget,
            step: Union[int, float] = None
    ):
        """
        Bidirectionally connect events with a ipywidget slider

        Parameters
        ----------
        widget: ipywidgets.IntRangeSlider or ipywidgets.FloatRangeSlider
            ipywidget slider to connect to

        step: int or float, default ``None``
            step size, if ``None`` 100 steps are created

        """
        if not isinstance(widget, (ipywidgets.IntRangeSlider, ipywidgets.FloatRangeSlider)):
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
        value = self.selection()

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
        if self.selection.axis == "x":
            # min and max of current bounds, i.e. the edges
            xmin, xmax = self.selection()

            # new left bound position
            bound0_new = xmin + delta[0]

            # new right bound position
            bound1_new = xmax + delta[0]
        else:
            # min and max of current bounds, i.e. the edges
            ymin, ymax = self.selection()

            # new bottom bound position
            bound0_new = ymin + delta[1]

            # new top bound position
            bound1_new = ymax + delta[1]

        # move entire selector if source was fill
        if self._move_info.source == self.fill:
            # set the new bounds
            self.selection = (bound0_new, bound1_new)
            return

        # if selector is not resizable do nothing
        if not self._resizable:
            return

        # if resizable, move edges
        if self._move_info.source == self.edges[0]:
            # change only left or bottom bound
            self.selection = (bound0_new, self.selection()[1])

        elif self._move_info.source == self.edges[1]:
            # change only right or top bound
            self.selection = (self.selection()[0], bound1_new)
        else:
            return
