from typing import *
import math

import numpy as np

import pygfx
from pygfx.linalg import Vector3

try:
    import ipywidgets
    HAS_IPYWIDGETS = True
except:
    HAS_IPYWIDGETS = False

from .._base import Graphic, GraphicFeature
from ..features._base import FeatureEvent


class SliderValueFeature(GraphicFeature):
    # A bit much to have a class for this but this allows it to integrate with the fastplotlib callback system
    """
    Manages the slider value and callbacks

    **pick info**

     ================== ================================================================
      key                value
     ================== ================================================================
      "new_data"         the new slider position in world coordinates
      "selected_index"   the graphic data index that corresponds to the slider position
      "world_object"     parent world object
     ================== ================================================================

    """
    def __init__(self, parent, axis: str, value: float):
        super(SliderValueFeature, self).__init__(parent, data=value)

        self.axis = axis

    def _set(self, value: float):
        if self.axis == "x":
            self._parent.position.x = value
        else:
            self._parent.position.y = value

        self._data = value
        self._feature_changed(key=None, new_data=value)

    def _feature_changed(self, key: Union[int, slice, Tuple[slice]], new_data: Any):
        if len(self._event_handlers) < 1:
            return

        if self._parent.parent is not None:
            g_ix = self._parent.get_selected_index()
        else:
            g_ix = None

        pick_info = {
            "index": None,
            "collection-index": self._collection_index,
            "world_object": self._parent.world_object,
            "new_data": new_data,
            "selected_index": g_ix,
            "graphic": self._parent
        }

        event_data = FeatureEvent(type="slider", pick_info=pick_info)

        self._call_event_handlers(event_data)


class LinearSelector(Graphic):
    def __init__(
            self,
            value: int,
            limits: Tuple[int, int],
            axis: str = "x",
            parent: Graphic = None,
            end_points: Tuple[int, int] = None,
            ipywidget_slider: ipywidgets.IntSlider = None,
            thickness: float = 2.5,
            color: Any = "w",
            name: str = None,
    ):
        """
        Create a horizontal or vertical line slider that is synced to an ipywidget IntSlider

        Parameters
        ----------
        axis: str, default "x"
            "x" | "y", the axis which the slider can move along

        origin: int
            the initial position of the slider, x or y value depending on "axis" argument

        end_points: (int, int)
            set length of slider by bounding it between two x-pos or two y-pos

        ipywidget_slider: IntSlider, optional
            ipywidget slider to associate with this graphic

        thickness: float, default 2.5
            thickness of the slider

        color: Any, default "w"
            value to set the color of the slider

        name: str, optional
            name of line slider

        Features
        --------

        value: :class:`SliderValueFeature`
            ``value()`` returns the current slider position in world coordinates
            use ``value.add_event_handler()`` to add callback functions that are
            called when the LinearSelector value changes. See feaure class for event pick_info table

        """

        self.limits = tuple(map(round, limits))
        value = round(value)

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
            raise ValueError("`axis` must be one of 'v' or 'h'")

        line_data = line_data.astype(np.float32)

        self.axis = axis

        super(LinearSelector, self).__init__(name=name)

        if thickness < 1.1:
            material = pygfx.LineThinMaterial
        else:
            material = pygfx.LineMaterial

        colors_inner = np.repeat([pygfx.Color(color)], 2, axis=0).astype(np.float32)
        self.colors_outer = np.repeat([pygfx.Color([0.3, 0.3, 0.3, 1.0])], 2, axis=0).astype(np.float32)

        line_inner = pygfx.Line(
            # self.data.feature_data because data is a Buffer
            geometry=pygfx.Geometry(positions=line_data, colors=colors_inner),
            material=material(thickness=thickness, vertex_colors=True)
        )

        self.line_outer = pygfx.Line(
            geometry=pygfx.Geometry(positions=line_data, colors=self.colors_outer.copy()),
            material=material(thickness=thickness + 6, vertex_colors=True)
        )

        line_inner.position.z = self.line_outer.position.z + 1

        world_object = pygfx.Group()

        world_object.add(self.line_outer)
        world_object.add(line_inner)

        self._set_world_object(world_object)

        # set x or y position
        pos = getattr(self.position, axis)
        pos = value

        self.value = SliderValueFeature(self, axis=axis, value=value)

        self.ipywidget_slider = ipywidget_slider

        if self.ipywidget_slider is not None:
            self._setup_ipywidget_slider(ipywidget_slider)

        self._move_info: dict = None

        self.parent = parent

        self._block_ipywidget_call = False

    def _setup_ipywidget_slider(self, widget):
        # setup ipywidget slider with callbacks to this LinearSelector
        widget.value = int(self.value())
        widget.observe(self._ipywidget_callback, "value")
        self.value.add_event_handler(self._update_ipywidget)
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

        self.value = change["new"]

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
            raise ImportError("Must installed `ipywidgets` to use `make_ipywidget_slider()`")

        cls = getattr(ipywidgets, kind)

        slider = cls(
            min=self.limits[0],
            max=self.limits[1],
            value=int(self.value()),
            step=1,
            **kwargs
        )
        self.ipywidget_slider = slider
        self._setup_ipywidget_slider(slider)

        return slider

    def get_selected_index(self, graphic: Graphic = None) -> int:
        """
        Data index the slider is currently at w.r.t. the Graphic data.

        Parameters
        ----------
        graphic: Graphic, optional
            Graphic to get the selected data index from. Default is the parent graphic associated to the slider.

        Returns
        -------
        int
            data index the slider is currently at
        """

        graphic = self._get_source(graphic)

        # the array to search for the closest value along that axis
        if self.axis == "x":
            to_search = graphic.data()[:, 0]
            offset = getattr(graphic.position, self.axis)
        else:
            to_search = graphic.data()[:, 1]
            offset = getattr(graphic.position, self.axis)

        find_value = self.value() - offset

        # get closest data index to the world space position of the slider
        idx = np.searchsorted(to_search, find_value, side="left")

        if idx > 0 and (idx == len(to_search) or math.fabs(find_value - to_search[idx - 1]) < math.fabs(find_value - to_search[idx])):
            return int(idx - 1)
        else:
            return int(idx)

    def _get_source(self, graphic):
        if self.parent is None and graphic is None:
            raise AttributeError(
                "No Graphic to apply selector. "
                "You must either set a ``parent`` Graphic on the selector, or pass a graphic."
            )

        # use passed graphic if provided, else use parent
        if graphic is not None:
            source = graphic
        else:
            source = self.parent

        return source

    def _add_plot_area_hook(self, plot_area):
        self._plot_area = plot_area

        # move events
        self.world_object.add_event_handler(self._move_start, "pointer_down")
        self._plot_area.renderer.add_event_handler(self._move, "pointer_move")
        self._plot_area.renderer.add_event_handler(self._move_end, "pointer_up")

        # move directly to location of center mouse button click
        self._plot_area.renderer.add_event_handler(self._move_to_pointer, "click")

        # mouse hover color events
        self.world_object.add_event_handler(self._pointer_enter, "pointer_enter")
        self.world_object.add_event_handler(self._pointer_leave, "pointer_leave")

    def _move_to_pointer(self, ev):
        # middle mouse button clicks
        if ev.button != 3:
            return

        click_pos = (ev.x, ev.y)
        world_pos = self._plot_area.map_screen_to_world(click_pos)

        # outside this viewport
        if world_pos is None:
            return

        if self.axis == "x":
            self.value = world_pos.x
        else:
            self.value = world_pos.y

    def _move_start(self, ev):
        self._move_info = {"last_pos": (ev.x, ev.y)}

    def _move(self, ev):
        if self._move_info is None:
            return

        self._plot_area.controller.enabled = False

        last = self._move_info["last_pos"]

        # new - last
        # pointer move events are in viewport or canvas space
        delta = Vector3(ev.x - last[0], ev.y - last[1])

        self._move_info = {"last_pos": (ev.x, ev.y)}

        viewport_size = self._plot_area.viewport.logical_size

        # convert delta to NDC coordinates using viewport size
        # also since these are just deltas we don't have to calculate positions relative to the viewport
        delta_ndc = delta.multiply(
            Vector3(
                2 / viewport_size[0],
                -2 / viewport_size[1],
                0
            )
        )

        camera = self._plot_area.camera

        # current world position
        vec = self.position.clone()

        # compute and add delta in projected NDC space and then unproject back to world space
        vec.project(camera).add(delta_ndc).unproject(camera)

        new_value = getattr(vec, self.axis)

        if new_value < self.limits[0] or new_value > self.limits[1]:
            return

        self.value = new_value
        self._plot_area.controller.enabled = True

    def _move_end(self, ev):
        self._move_info = None
        self._plot_area.controller.enabled = True

    def _pointer_enter(self, ev):
        self.line_outer.geometry.colors.data[:] = np.repeat([pygfx.Color("magenta")], 2, axis=0)
        self.line_outer.geometry.colors.update_range()

    def _pointer_leave(self, ev):
        if self._move_info is not None:
            return

        self._reset_color()

    def _reset_color(self):
        self.line_outer.geometry.colors.data[:] = self.colors_outer
        self.line_outer.geometry.colors.update_range()
