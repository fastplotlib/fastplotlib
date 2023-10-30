import traceback
from datetime import datetime
from itertools import product

from ipywidgets import Button, Layout, ToggleButton, Dropdown, HBox

from ...graphics.selectors import PolygonSelector
from ._toolbar import ToolBar


class IpywidgetToolBar(HBox, ToolBar):
    def __init__(self, plot):
        """
        Basic toolbar for a GridPlot instance.

        Parameters
        ----------
        plot:
        """
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
        self._maintain_aspect_button.observe(self.maintain_aspect, "value")
        self._y_direction_button.on_click(self.y_direction_handler)
        self._add_polygon_button.on_click(self.add_polygon)
        self._record_button.observe(self.record_plot, "value")

        # set initial values for some buttons
        self._maintain_aspect_button.value = self.current_subplot.camera.maintain_aspect

        if self.current_subplot.camera.local.scale_y == -1:
            self._y_direction_button.icon = "arrow-down"
        else:
            self._y_direction_button.icon = "arrow-up"

        HBox.__init__(self, widgets)

    def _get_subplot_dropdown_value(self) -> str:
        return self._dropdown.value

    def auto_scale_handler(self, obj):
        self.current_subplot.auto_scale(maintain_aspect=self.current_subplot.camera.maintain_aspect)

    def center_scene_handler(self, obj):
        self.current_subplot.center_scene()

    def panzoom_handler(self, obj):
        self.current_subplot.controller.enabled = self._panzoom_controller_button.value

    def maintain_aspect(self, obj):
        for camera in self.current_subplot.controller.cameras:
            camera.maintain_aspect = self._maintain_aspect_button.value

    def y_direction_handler(self, obj):
        # TODO: What if the user has set different y_scales for cameras under the same controller?
        self.current_subplot.camera.local.scale_y *= -1
        if self.current_subplot.camera.local.scale_y == -1:
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
