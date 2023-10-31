import traceback
from datetime import datetime
from itertools import product
from math import copysign
from functools import partial
from typing import *


from ipywidgets.widgets import (
    IntSlider,
    VBox,
    HBox,
    ToggleButton,
    Dropdown,
    Layout,
    Button,
    BoundedIntText,
    Play,
    jslink,
)

from ...graphics.selectors import PolygonSelector
from ._toolbar import ToolBar


class IpywidgetToolBar(HBox, ToolBar):
    """Basic toolbar using ipywidgets"""
    def __init__(self, plot):
        ToolBar.__init__(self, plot)

        self._auto_scale_button = Button(
            value=False,
            disabled=False,
            icon="expand-arrows-alt",
            layout=Layout(width="auto"),
            tooltip="auto-scale scene",
        )
        self._center_scene_button = Button(
            value=False,
            disabled=False,
            icon="align-center",
            layout=Layout(width="auto"),
            tooltip="auto-center scene",
        )
        self._panzoom_controller_button = ToggleButton(
            value=True,
            disabled=False,
            icon="hand-pointer",
            layout=Layout(width="auto"),
            tooltip="panzoom controller",
        )
        self._maintain_aspect_button = ToggleButton(
            value=True,
            disabled=False,
            description="1:1",
            layout=Layout(width="auto"),
            tooltip="maintain aspect",
        )
        self._maintain_aspect_button.style.font_weight = "bold"

        self._y_direction_button = Button(
            value=False,
            disabled=False,
            icon="arrow-up",
            layout=Layout(width="auto"),
            tooltip="y-axis direction",
        )

        self._record_button = ToggleButton(
            value=False,
            disabled=False,
            icon="video",
            layout=Layout(width="auto"),
            tooltip="record",
        )

        self._add_polygon_button = Button(
            value=False,
            disabled=False,
            icon="draw-polygon",
            layout=Layout(width="auto"),
            tooltip="add PolygonSelector"
        )

        widgets = [
            self._auto_scale_button,
            self._center_scene_button,
            self._panzoom_controller_button,
            self._maintain_aspect_button,
            self._y_direction_button,
            self._add_polygon_button,
            self._record_button,
        ]

        if hasattr(self.plot, "_subplots"):
            positions = list(product(range(self.plot.shape[0]), range(self.plot.shape[1])))
            values = list()
            for pos in positions:
                if self.plot[pos].name is not None:
                    values.append(self.plot[pos].name)
                else:
                    values.append(str(pos))

            self._dropdown = Dropdown(
                options=values,
                disabled=False,
                description="Subplots:",
                layout=Layout(width="200px"),
            )

            self.plot.renderer.add_event_handler(self.update_current_subplot, "click")

            widgets.append(self._dropdown)

        self._panzoom_controller_button.observe(self.panzoom_handler, "value")
        self._auto_scale_button.on_click(self.auto_scale_handler)
        self._center_scene_button.on_click(self.center_scene_handler)
        self._maintain_aspect_button.observe(self.maintain_aspect_handler, "value")
        self._y_direction_button.on_click(self.y_direction_handler)
        self._add_polygon_button.on_click(self.add_polygon)
        self._record_button.observe(self.record_plot, "value")

        # set initial values for some buttons
        self._maintain_aspect_button.value = self.current_subplot.camera.maintain_aspect

        if copysign(1, self.current_subplot.camera.local.scale_y) == -1:
            self._y_direction_button.icon = "arrow-down"
        else:
            self._y_direction_button.icon = "arrow-up"

        super().__init__(widgets)

    def _get_subplot_dropdown_value(self) -> str:
        return self._dropdown.value

    def auto_scale_handler(self, obj):
        self.current_subplot.auto_scale(maintain_aspect=self.current_subplot.camera.maintain_aspect)

    def center_scene_handler(self, obj):
        self.current_subplot.center_scene()

    def panzoom_handler(self, obj):
        self.current_subplot.controller.enabled = self._panzoom_controller_button.value

    def maintain_aspect_handler(self, obj):
        for camera in self.current_subplot.controller.cameras:
            camera.maintain_aspect = self._maintain_aspect_button.value

    def y_direction_handler(self, obj):
        # flip every camera under the same controller
        for camera in self.current_subplot.controller.cameras:
            camera.local.scale_y *= -1

        if copysign(1, self.current_subplot.camera.local.scale_y) == -1:
            self._y_direction_button.icon = "arrow-down"
        else:
            self._y_direction_button.icon = "arrow-up"

    def update_current_subplot(self, ev):
        for subplot in self.plot:
            pos = subplot.map_screen_to_world((ev.x, ev.y))
            if pos is not None:
                # update self.dropdown
                if subplot.name is None:
                    self._dropdown.value = str(subplot.position)
                else:
                    self._dropdown.value = subplot.name
                self._panzoom_controller_button.value = subplot.controller.enabled
                self._maintain_aspect_button.value = subplot.camera.maintain_aspect

                if copysign(1, subplot.camera.local.scale_y) == -1:
                    self._y_direction_button.icon = "arrow-down"
                else:
                    self._y_direction_button.icon = "arrow-up"

    def record_plot(self, obj):
        if self._record_button.value:
            try:
                self.plot.record_start(
                    f"./{datetime.now().isoformat(timespec='seconds').replace(':', '_')}.mp4"
                )
            except Exception:
                traceback.print_exc()
                self._record_button.value = False
        else:
            self.plot.record_stop()

    def add_polygon(self, obj):
        ps = PolygonSelector(edge_width=3, edge_color="magenta")
        self.current_subplot.add_graphic(ps, center=False)


class IpywidgetImageWidgetToolbar(VBox):
    def __init__(self, iw):
        """
        Basic toolbar for a ImageWidget instance.

        Parameters
        ----------
        plot:
        """
        self.iw = iw

        self.reset_vminvmax_button = Button(
            value=False,
            disabled=False,
            icon="adjust",
            layout=Layout(width="auto"),
            tooltip="reset vmin/vmax",
        )

        self.reset_vminvmax_hlut_button = Button(
            value=False,
            icon="adjust",
            description="reset",
            layout=Layout(width="auto"),
            tooltip="reset vmin/vmax and reset histogram using current frame"
        )

        self.sliders: Dict[str, IntSlider] = dict()

        # only for xy data, no time point slider needed
        if self.iw.ndim == 2:
            widgets = [self.reset_vminvmax_button]
        # for txy, tzxy, etc. data
        else:
            for dim in self.iw.slider_dims:
                slider = IntSlider(
                    min=0,
                    max=self.iw._dims_max_bounds[dim] - 1,
                    step=1,
                    value=0,
                    description=f"dimension: {dim}",
                    orientation="horizontal",
                )

                slider.observe(partial(self.iw._slider_value_changed, dim), names="value")

                self.sliders[dim] = slider

            self.step_size_setter = BoundedIntText(
                value=1,
                min=1,
                max=self.sliders["t"].max,
                step=1,
                description="Step Size:",
                disabled=False,
                description_tooltip="set slider step",
                layout=Layout(width="150px"),
            )
            self.speed_text = BoundedIntText(
                value=100,
                min=1,
                max=1_000,
                step=50,
                description="Speed",
                disabled=False,
                description_tooltip="Playback speed, this is NOT framerate.\nArbitrary units between 1 - 1,000",
                layout=Layout(width="150px"),
            )
            self.play_button = Play(
                value=0,
                min=self.sliders["t"].min,
                max=self.sliders["t"].max,
                step=self.sliders["t"].step,
                description="play/pause",
                disabled=False,
            )
            widgets = [
                self.reset_vminvmax_button,
                self.reset_vminvmax_hlut_button,
                self.play_button,
                self.step_size_setter,
                self.speed_text
            ]

            self.play_button.interval = 10

            self.step_size_setter.observe(self._change_stepsize, "value")
            self.speed_text.observe(self._change_framerate, "value")
            jslink((self.play_button, "value"), (self.sliders["t"], "value"))
            jslink((self.play_button, "max"), (self.sliders["t"], "max"))

        self.reset_vminvmax_button.on_click(self._reset_vminvmax)
        self.reset_vminvmax_hlut_button.on_click(self._reset_vminvmax_frame)

        self.iw.gridplot.renderer.add_event_handler(self._set_slider_layout, "resize")

        # the buttons
        self.hbox = HBox(widgets)

        super().__init__((self.hbox, *list(self.sliders.values())))

    def _reset_vminvmax(self, obj):
        self.iw.reset_vmin_vmax()

    def _reset_vminvmax_frame(self, obj):
        self.iw.reset_vmin_vmax_frame()

    def _change_stepsize(self, obj):
        self.sliders["t"].step = self.step_size_setter.value

    def _change_framerate(self, change):
        interval = int(1000 / change["new"])
        self.play_button.interval = interval

    def _set_slider_layout(self, *args):
        w, h = self.iw.gridplot.renderer.logical_size
        for k, v in self.sliders.items():
            v.layout = Layout(width=f"{w}px")
