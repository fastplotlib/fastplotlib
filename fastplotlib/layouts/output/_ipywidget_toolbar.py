import traceback
from datetime import datetime
from itertools import product
from math import copysign
from pathlib import Path

from ipywidgets.widgets import (
    HBox,
    ToggleButton,
    Dropdown,
    Layout,
    Button,
    Image,
)

from ...graphics.selectors import PolygonSelector
from ._toolbar import ToolBar
from ...utils import config


class IpywidgetToolBar(HBox, ToolBar):
    """Basic toolbar using ipywidgets"""

    def __init__(self, figure):
        ToolBar.__init__(self, figure)

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
            tooltip="add PolygonSelector",
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

        if config.party_parrot:
            gif_path = Path(__file__).parent.parent.parent.joinpath("assets", "egg.gif")
            with open(gif_path, "rb") as f:
                gif = f.read()

            image = Image(
                value=gif,
                format="png",
                width=35,
                height=25,
            )
            widgets.append(image)

        positions = list(
            product(range(self.figure.shape[0]), range(self.figure.shape[1]))
        )
        values = list()
        for pos in positions:
            if self.figure[pos].name is not None:
                values.append(self.figure[pos].name)
            else:
                values.append(str(pos))

        self._dropdown = Dropdown(
            options=values,
            disabled=False,
            description="Subplots:",
            layout=Layout(width="200px"),
        )

        self.figure.renderer.add_event_handler(self.update_current_subplot, "click")

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
        self.current_subplot.auto_scale(
            maintain_aspect=self.current_subplot.camera.maintain_aspect
        )

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
        for subplot in self.figure:
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
                self.figure.recorder.start(
                    f"./{datetime.now().isoformat(timespec='seconds').replace(':', '_')}.mp4"
                )
            except Exception:
                traceback.print_exc()
                self._record_button.value = False
        else:
            self.figure.recorder.stop()

    def add_polygon(self, obj):
        ps = PolygonSelector(edge_width=3, edge_color="magenta")
        self.current_subplot.add_graphic(ps, center=False)
