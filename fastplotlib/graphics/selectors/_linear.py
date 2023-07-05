from typing import *
import math

import numpy as np

import pygfx

try:
    import ipywidgets

    HAS_IPYWIDGETS = True
except (ImportError, ModuleNotFoundError):
    HAS_IPYWIDGETS = False

from .._base import Graphic, GraphicCollection
from .._features._selection_features import LinearSelectionFeature
from ._base_selector import BaseSelector


class LinearSelector(Graphic, BaseSelector):
    # TODO: make `selection` arg in graphics data space not world space
    def __init__(
        self,
        selection: int,
        limits: Tuple[int, int],
        axis: str = "x",
        parent: Graphic = None,
        end_points: Tuple[int, int] = None,
        arrow_keys_modifier: str = "Shift",
        ipywidget_slider=None,
        thickness: float = 2.5,
        color: Any = "w",
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

        parent: Graphic
            parent graphic for this LineSelector

        end_points: (int, int)
            set length of slider by bounding it between two x-pos or two y-pos

        arrow_keys_modifier: str
            modifier key that must be pressed to initiate movement using arrow keys, must be one of:
            "Control", "Shift", "Alt" or ``None``. Double click on the selector first to enable the
            arrow key movements, or set the attribute ``arrow_key_events_enabled = True``

        ipywidget_slider: IntSlider, optional
            ipywidget slider to associate with this graphic

        thickness: float, default 2.5
            thickness of the slider

        color: Any, default "w"
            selection to set the color of the slider

        name: str, optional
            name of line slider

        Features
        --------

        selection: :class:`.LinearSelectionFeature`
            ``selection()`` returns the current selector position in world coordinates.
            Use ``get_selected_index()`` to get the currently selected index in data
            space.
            Use ``selection.add_event_handler()`` to add callback functions that are
            called when the LinearSelector selection changes. See feature class for
            event pick_info table

        """
        if len(limits) != 2:
            raise ValueError("limits must be a tuple of 2 integers, i.e. (int, int)")

        limits = tuple(map(round, limits))
        selection = round(selection)

        if axis == "x":
            xs = np.zeros(2)
            ys = np.array(end_points)
            zs = np.zeros(2)

            line_data = np.column_stack([xs, ys, zs])
        elif axis == "y":
            xs = np.zeros(end_points)
            ys = np.array(2)
            zs = np.zeros(2)

            line_data = np.column_stack([xs, ys, zs])
        else:
            raise ValueError("`axis` must be one of 'x' or 'y'")

        line_data = line_data.astype(np.float32)

        # init Graphic
        Graphic.__init__(self, name=name)

        if thickness < 1.1:
            material = pygfx.LineThinMaterial
        else:
            material = pygfx.LineMaterial

        self.colors_outer = pygfx.Color([0.3, 0.3, 0.3, 1.0])

        line_inner = pygfx.Line(
            # self.data.feature_data because data is a Buffer
            geometry=pygfx.Geometry(positions=line_data),
            material=material(thickness=thickness, color=color),
        )

        self.line_outer = pygfx.Line(
            geometry=pygfx.Geometry(positions=line_data),
            material=material(thickness=thickness + 6, color=self.colors_outer),
        )

        line_inner.world.z = self.line_outer.world.z + 1

        world_object = pygfx.Group()

        world_object.add(self.line_outer)
        world_object.add(line_inner)

        self._set_world_object(world_object)

        # set x or y position
        if axis == "x":
            self.position_x = selection
        else:
            self.position_y = selection

        self.selection = LinearSelectionFeature(
            self, axis=axis, value=selection, limits=limits
        )

        self.ipywidget_slider = ipywidget_slider

        if self.ipywidget_slider is not None:
            self._setup_ipywidget_slider(ipywidget_slider)

        self._move_info: dict = None
        self._pygfx_event = None

        self.parent = parent

        self._block_ipywidget_call = False

        # init base selector
        BaseSelector.__init__(
            self,
            edges=(line_inner, self.line_outer),
            hover_responsive=(line_inner, self.line_outer),
            arrow_keys_modifier=arrow_keys_modifier,
            axis=axis,
        )

    def _setup_ipywidget_slider(self, widget):
        # setup ipywidget slider with callbacks to this LinearSelector
        widget.value = int(self.selection())
        widget.observe(self._ipywidget_callback, "value")
        self.selection.add_event_handler(self._update_ipywidget)
        self._plot_area.renderer.add_event_handler(self._set_slider_layout, "resize")

    def _update_ipywidget(self, ev):
        # update the ipywidget slider value when LinearSelector value changes
        self._block_ipywidget_call = True
        self.ipywidget_slider.value = int(ev.pick_info["new_data"])
        self._block_ipywidget_call = False

    def _ipywidget_callback(self, change):
        # update the LinearSelector if the ipywidget value changes
        if self._block_ipywidget_call:
            return

        self.selection = change["new"]

    def _set_slider_layout(self, *args):
        w, h = self._plot_area.renderer.logical_size

        self.ipywidget_slider.layout = ipywidgets.Layout(width=f"{w}px")

    def make_ipywidget_slider(self, kind: str = "IntSlider", **kwargs):
        """
        Makes and returns an ipywidget slider that is associated to this LinearSelector

        Parameters
        ----------
        kind: str
            "IntSlider" or "FloatSlider"

        kwargs
            passed to the ipywidget slider constructor

        Returns
        -------
        ipywidgets.Intslider or ipywidgets.FloatSlider

        """
        if self.ipywidget_slider is not None:
            raise AttributeError("Already has ipywidget slider")

        if not HAS_IPYWIDGETS:
            raise ImportError(
                "Must installed `ipywidgets` to use `make_ipywidget_slider()`"
            )

        cls = getattr(ipywidgets, kind)

        slider = cls(
            min=self.selection.limits[0],
            max=self.selection.limits[1],
            value=int(self.selection()),
            step=1,
            **kwargs,
        )
        self.ipywidget_slider = slider
        self._setup_ipywidget_slider(slider)

        return slider

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
            geo_positions = graphic.data()[:, 0]
            offset = getattr(graphic, f"position_{self.axis}")
        else:
            geo_positions = graphic.data()[:, 1]
            offset = getattr(graphic, f"position_{self.axis}")

        if "Line" in graphic.__class__.__name__:
            # we want to find the index of the geometry position that is closest to the slider's geometry position
            find_value = self.selection() - offset

            # get closest data index to the world space position of the slider
            idx = np.searchsorted(geo_positions, find_value, side="left")

            if idx > 0 and (
                idx == len(geo_positions)
                or math.fabs(find_value - geo_positions[idx - 1])
                < math.fabs(find_value - geo_positions[idx])
            ):
                return int(idx - 1)
            else:
                return int(idx)

        if (
            "Heatmap" in graphic.__class__.__name__
            or "Image" in graphic.__class__.__name__
        ):
            # indices map directly to grid geometry for image data buffer
            index = self.selection() - offset
            return int(index)

    def _move_graphic(self, delta: np.ndarray):
        """
        Moves the graphic

        Parameters
        ----------
        delta: np.ndarray
            delta in world space

        """

        if self.axis == "x":
            self.selection = self.selection() + delta[0]
        else:
            self.selection = self.selection() + delta[1]
