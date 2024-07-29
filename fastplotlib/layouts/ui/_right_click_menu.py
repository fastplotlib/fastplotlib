import numpy as np

from imgui_bundle import imgui, imgui_ctx

from .._utils import controller_types
from .._plot_area import PlotArea


class RightClickMenu:
    def __init__(self, figure):
        self.figure = figure

        self._last_right_click_pos = None

        self._is_open = False

        self._mouse_down: bool = False

        self.figure.renderer.event_filters["right-click-menu"] = np.array([
            [-1, -1],
            [-1, -1]
        ])

        self.figure.renderer.event_filters["controller-menu"] = np.array([
            [-1, -1],
            [-1, -1]
        ])

    def reset_event_filters(self):
        for k in ["right-click-menu", "controller-menu"]:
            self.figure.renderer.event_filters[k][:] = [-1, -1], [-1, -1]

    def set_event_filter(self, name: str):
        x1, y1 = imgui.get_window_pos()
        width, height = imgui.get_window_size()
        x2, y2 = x1 + width, y1 + height

        self.figure.renderer.event_filters[name][:] = [x1 - 1, y1 - 1], [x2 + 4, y2 + 4]

    def get_subplot(self) -> PlotArea:
        if self._last_right_click_pos is None:
            return False

        for subplot in self.figure:
            if subplot.viewport.is_inside(*self._last_right_click_pos):
                return subplot

    def update(self):
        if imgui.is_mouse_down(1) and not self._mouse_down:
            self._mouse_down = True
            self._last_right_click_pos = imgui.get_mouse_pos()

        if imgui.is_mouse_released(1) and self._mouse_down:
            self._mouse_down = False

            if self._last_right_click_pos == imgui.get_mouse_pos():
                if self.get_subplot():
                    # open only if right click was inside a subplot
                    imgui.open_popup(f"right-click-menu")
                    self._is_open = True
                    self.get_subplot().controller._actions = {}  # cancel any scheduled events

        if not imgui.is_popup_open("right-click-menu"):
            self.reset_event_filters()

        if imgui.begin_popup(f"right-click-menu"):
            self.set_event_filter("right-click-menu")

            if imgui.menu_item(f"Autoscale", None, False)[0]:
                self.get_subplot().auto_scale()

            if imgui.menu_item(f"Center", None, False)[0]:
                self.get_subplot().center_scene()

            _, maintain_aspect = imgui.menu_item(
                "Maintain Aspect", None, self.get_subplot().camera.maintain_aspect
            )
            self.get_subplot().camera.maintain_aspect = maintain_aspect

            if imgui.begin_menu("Controller"):
                self.set_event_filter("controller-menu")
                _, enabled = imgui.menu_item(
                    "Enabled", None, self.get_subplot().controller.enabled
                )

                self.get_subplot().controller.enabled = enabled

                changed, damping = imgui.slider_float(
                    "Damping",
                    v=self.get_subplot().controller.damping,
                    v_min=0.0,
                    v_max=10.0,
                )

                if changed:
                    self.get_subplot().controller.damping = damping

                imgui.separator()
                imgui.text("Controller type:")

                for name, controller_type_iter in controller_types.items():
                    current_type = type(self.get_subplot().controller)

                    clicked, _ = imgui.menu_item(
                        label=name,
                        shortcut=None,
                        p_selected=current_type is controller_type_iter,
                    )

                    if clicked and (current_type is not controller_type_iter):
                        # menu item was clicked and the desired controller isn't the current one
                        self.get_subplot().controller = name

                imgui.end_menu()

            imgui.end_popup()
