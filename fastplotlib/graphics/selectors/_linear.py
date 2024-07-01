from typing import *
import math
from numbers import Real

import numpy as np
import pygfx

from ...utils.gui import IS_JUPYTER
from .._base import Graphic
from .._collection_base import GraphicCollection
from .._features._selection_features import LinearSelectionFeature
from ._base_selector import BaseSelector


if IS_JUPYTER:
    # If using the jupyter backend, user has jupyter_rfb, and thus also ipywidgets
    import ipywidgets


class LinearSelector(BaseSelector):
    @property
    def parent(self) -> Graphic:
        return self._parent

    @property
    def selection(self) -> float:
        """
        x or y value of selector's current position
        """
        return self._selection.value

    @selection.setter
    def selection(self, value: int):
        graphic = self._parent

        if isinstance(graphic, GraphicCollection):
            pass

        self._selection.set_value(self, value)

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

    # TODO: make `selection` arg in graphics data space not world space
    def __init__(
        self,
        selection: float,
        limits: Sequence[float],
        size: float,
        center: float,
        axis: str = "x",
        parent: Graphic = None,
        color: str | tuple = "w",
        thickness: float = 2.5,
        arrow_keys_modifier: str = "Shift",
        name: str = None,
    ):
        """
        Create a horizontal or vertical line slider that is synced to an ipywidget IntSlider

        Parameters
        ----------
        selection: int
            initial x or y selected position for the slider, in world space

        limits: (int, int)
            (min, max) limits along the x or y axis for the selector, in world space

        axis: str, default "x"
            "x" | "y", the axis which the slider can move along

        center: float
            center offset of the selector on the orthogonal axis, by default the data mean

        parent: Graphic
            parent graphic for this LineSelector

        arrow_keys_modifier: str
            modifier key that must be pressed to initiate movement using arrow keys, must be one of:
            "Control", "Shift", "Alt" or ``None``. Double click on the selector first to enable the
            arrow key movements, or set the attribute ``arrow_key_events_enabled = True``

        thickness: float, default 2.5
            thickness of the slider

        color: Any, default "w"
            selection to set the color of the slider

        name: str, optional
            name of line slider

        """
        if len(limits) != 2:
            raise ValueError("limits must be a tuple of 2 integers, i.e. (int, int)")

        self._limits = np.asarray(limits)

        end_points = [-size / 2, size / 2]

        if axis == "x":
            xs = np.array([selection, selection])
            ys = np.array(end_points)
            zs = np.zeros(2)

            line_data = np.column_stack([xs, ys, zs])
        elif axis == "y":
            xs = np.array(end_points)
            ys = np.array([selection, selection])
            zs = np.zeros(2)

            line_data = np.column_stack([xs, ys, zs])
        else:
            raise ValueError("`axis` must be one of 'x' or 'y'")

        line_data = line_data.astype(np.float32)

        if thickness < 1.1:
            material = pygfx.LineThinMaterial
        else:
            material = pygfx.LineMaterial

        self.colors_outer = pygfx.Color([0.3, 0.3, 0.3, 1.0])

        line_inner = pygfx.Line(
            # self.data.feature_data because data is a Buffer
            geometry=pygfx.Geometry(positions=line_data),
            material=material(thickness=thickness, color=color, pick_write=True),
        )

        self.line_outer = pygfx.Line(
            geometry=pygfx.Geometry(positions=line_data),
            material=material(
                thickness=thickness + 6, color=self.colors_outer, pick_write=True
            ),
        )

        line_inner.world.z = self.line_outer.world.z + 1

        world_object = pygfx.Group()

        world_object.add(self.line_outer)
        world_object.add(line_inner)

        self._move_info: dict = None

        self._block_ipywidget_call = False

        self._handled_widgets = list()

        if axis == "x":
            offset = (parent.offset[0], center, 0)
        elif axis == "y":
            offset = (center, parent.offset[1], 0)

        # init base selector
        BaseSelector.__init__(
            self,
            edges=(line_inner, self.line_outer),
            hover_responsive=(line_inner, self.line_outer),
            arrow_keys_modifier=arrow_keys_modifier,
            axis=axis,
            parent=parent,
            name=name,
            offset=offset,
        )

        self._set_world_object(world_object)

        self._selection = LinearSelectionFeature(
            axis=axis, value=selection, limits=self._limits
        )

        if self._parent is not None:
            self.selection = selection
        else:
            self._selection.set_value(self, selection)

        # update any ipywidgets
        self.add_event_handler(self._update_ipywidgets, "selection")

    def _setup_ipywidget_slider(self, widget):
        # setup an ipywidget slider with bidirectional callbacks to this LinearSelector
        value = self.selection

        if isinstance(widget, ipywidgets.IntSlider):
            value = int(value)

        widget.value = value

        # user changes widget -> linear selection changes
        widget.observe(self._ipywidget_callback, "value")

        self._handled_widgets.append(widget)

    def _update_ipywidgets(self, ev):
        # update the ipywidget sliders when LinearSelector value changes
        self._block_ipywidget_call = True  # prevent infinite recursion

        value = ev.info["value"]
        # update all the handled slider widgets
        for widget in self._handled_widgets:
            if isinstance(widget, ipywidgets.IntSlider):
                widget.value = int(value)
            else:
                widget.value = value

        self._block_ipywidget_call = False

    def _ipywidget_callback(self, change):
        # update the LinearSelector when the ipywidget value changes
        if self._block_ipywidget_call or self._moving:
            return

        self.selection = change["new"]

    def _fpl_add_plot_area_hook(self, plot_area):
        super()._fpl_add_plot_area_hook(plot_area=plot_area)

        # resize the slider widgets when the canvas is resized
        self._plot_area.renderer.add_event_handler(self._set_slider_layout, "resize")

    def _set_slider_layout(self, *args):
        w, h = self._plot_area.renderer.logical_size

        for widget in self._handled_widgets:
            widget.layout = ipywidgets.Layout(width=f"{w}px")

    def make_ipywidget_slider(self, kind: str = "IntSlider", **kwargs):
        """
        Makes and returns an ipywidget slider that is associated to this LinearSelector

        Parameters
        ----------
        kind: str
            "IntSlider", "FloatSlider" or "FloatLogSlider"

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

        if kind not in ["IntSlider", "FloatSlider", "FloatLogSlider"]:
            raise TypeError(
                f"`kind` must be one of: 'IntSlider', 'FloatSlider' or 'FloatLogSlider'\n"
                f"You have passed: '{kind}'"
            )

        cls = getattr(ipywidgets, kind)

        value = self.selection
        if "Int" in kind:
            value = int(self.selection)

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
        widget: ipywidgets.IntSlider, ipywidgets.FloatSlider, or ipywidgets.FloatLogSlider
            ipywidget slider to connect to

        step: int or float, default ``None``
            step size, if ``None`` 100 steps are created

        """

        if not isinstance(
            widget,
            (ipywidgets.IntSlider, ipywidgets.FloatSlider, ipywidgets.FloatLogSlider),
        ):
            raise TypeError(
                f"`widget` must be one of: ipywidgets.IntSlider, ipywidgets.FloatSlider, or ipywidgets.FloatLogSlider\n"
                f"You have passed a: <{type(widget)}"
            )

        if step is None:
            step = (self.limits[1] - self.limits[0]) / 100

        if isinstance(widget, ipywidgets.IntSlider):
            step = int(step)

        widget.step = step

        self._setup_ipywidget_slider(widget)

    def get_selected_index(self, graphic: Graphic = None) -> Union[int, List[int]]:
        """
        Data index the slider is currently at w.r.t. the Graphic data. With LineGraphic data, the geometry x or y
        position is not always the data position, for example if plotting data using np.linspace. Use this to get
        the data index of the slider.

        Parameters
        ----------
        graphic: Graphic, optional
            Graphic to get the selected data index from. Default is the parent graphic associated to the slider.

        Returns
        -------
        int or List[int]
            data index the slider is currently at, list of ``int`` if a Collection
        """

        source = self._get_source(graphic)

        if isinstance(source, GraphicCollection):
            ixs = list()
            for g in source.graphics:
                ixs.append(self._get_selected_index(g))

            return ixs

        return self._get_selected_index(source)

    def _get_selected_index(self, graphic):
        # the array to search for the closest value along that axis
        if self.axis == "x":
            data = graphic.data[:, 0]
        elif self.axis == "y":
            data = graphic.data[:, 1]

        if (
            "Line" in graphic.__class__.__name__
            or "Scatter" in graphic.__class__.__name__
        ):
            # we want to find the index of the data closest to the slider position
            find_value = self.selection

            # get closest data index to the world space position of the slider
            idx = np.searchsorted(data, find_value, side="left")

            if idx > 0 and (
                idx == len(data)
                or math.fabs(find_value - data[idx - 1])
                < math.fabs(find_value - data[idx])
            ):
                return round(idx - 1)
            else:
                return round(idx)

        if "Image" in graphic.__class__.__name__:
            # indices map directly to grid geometry for image data buffer
            index = self.selection
            return round(index)

    def _move_graphic(self, delta: np.ndarray):
        """
        Moves the graphic

        Parameters
        ----------
        delta: np.ndarray
            delta in world space

        """

        if self.axis == "x":
            self.selection = self.selection + delta[0]
        else:
            self.selection = self.selection + delta[1]

    def _fpl_prepare_del(self):
        for widget in self._handled_widgets:
            widget.unobserve(self._ipywidget_callback, "value")

        super()._fpl_prepare_del()
