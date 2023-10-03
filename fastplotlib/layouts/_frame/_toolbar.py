from datetime import datetime
from itertools import product
import traceback

from ipywidgets import HBox, Layout, Button, ToggleButton, VBox, Dropdown, Widget

from fastplotlib.layouts._subplot import Subplot


class ToolBar:
    def __init__(self, plot):
        """
        Basic toolbar for a GridPlot instance.

        Parameters
        ----------
        plot:
        """
        self.plot = plot

        self.autoscale_button = Button(
            value=False,
            disabled=False,
            icon="expand-arrows-alt",
            layout=Layout(width="auto"),
            tooltip="auto-scale scene",
        )
        self.center_scene_button = Button(
            value=False,
            disabled=False,
            icon="align-center",
            layout=Layout(width="auto"),
            tooltip="auto-center scene",
        )
        self.panzoom_controller_button = ToggleButton(
            value=True,
            disabled=False,
            icon="hand-pointer",
            layout=Layout(width="auto"),
            tooltip="panzoom controller",
        )
        self.maintain_aspect_button = ToggleButton(
            value=True,
            disabled=False,
            description="1:1",
            layout=Layout(width="auto"),
            tooltip="maintain aspect",
        )
        self.maintain_aspect_button.style.font_weight = "bold"
        self.flip_camera_button = Button(
            value=False,
            disabled=False,
            icon="arrow-up",
            layout=Layout(width="auto"),
            tooltip="y-axis direction",
        )

        self.record_button = ToggleButton(
            value=False,
            disabled=False,
            icon="video",
            layout=Layout(width="auto"),
            tooltip="record",
        )

        positions = list(product(range(self.plot.shape[0]), range(self.plot.shape[1])))
        values = list()
        for pos in positions:
            if self.plot[pos].name is not None:
                values.append(self.plot[pos].name)
            else:
                values.append(str(pos))
        self.dropdown = Dropdown(
            options=values,
            disabled=False,
            description="Subplots:",
            layout=Layout(width="200px"),
        )

        self.widget = HBox(
            [
                self.autoscale_button,
                self.center_scene_button,
                self.panzoom_controller_button,
                self.maintain_aspect_button,
                self.flip_camera_button,
                self.record_button,
                self.dropdown,
            ]
        )

        self.panzoom_controller_button.observe(self.panzoom_control, "value")
        self.autoscale_button.on_click(self.auto_scale)
        self.center_scene_button.on_click(self.center_scene)
        self.maintain_aspect_button.observe(self.maintain_aspect, "value")
        self.flip_camera_button.on_click(self.flip_camera)
        self.record_button.observe(self.record_plot, "value")

        self.plot.renderer.add_event_handler(self.update_current_subplot, "click")

    @property
    def current_subplot(self) -> Subplot:
        # parses dropdown value as plot name or position
        current = self.dropdown.value
        if current[0] == "(":
            return self.plot[eval(current)]
        else:
            return self.plot[current]

    def auto_scale(self, obj):
        current = self.current_subplot
        current.auto_scale(maintain_aspect=current.camera.maintain_aspect)

    def center_scene(self, obj):
        current = self.current_subplot
        current.center_scene()

    def panzoom_control(self, obj):
        current = self.current_subplot
        current.controller.enabled = self.panzoom_controller_button.value

    def maintain_aspect(self, obj):
        current = self.current_subplot
        current.camera.maintain_aspect = self.maintain_aspect_button.value

    def flip_camera(self, obj):
        current = self.current_subplot
        current.camera.local.scale_y *= -1
        if current.camera.local.scale_y == -1:
            self.flip_camera_button.icon = "arrow-down"
        else:
            self.flip_camera_button.icon = "arrow-up"

    def update_current_subplot(self, ev):
        for subplot in self.plot:
            pos = subplot.map_screen_to_world((ev.x, ev.y))
            if pos is not None:
                # update self.dropdown
                if subplot.name is None:
                    self.dropdown.value = str(subplot.position)
                else:
                    self.dropdown.value = subplot.name
                self.panzoom_controller_button.value = subplot.controller.enabled
                self.maintain_aspect_button.value = subplot.camera.maintain_aspect

    def record_plot(self, obj):
        if self.record_button.value:
            try:
                self.plot.record_start(
                    f"./{datetime.now().isoformat(timespec='seconds').replace(':', '_')}.mp4"
                )
            except Exception:
                traceback.print_exc()
                self.record_button.value = False
        else:
            self.plot.record_stop()
