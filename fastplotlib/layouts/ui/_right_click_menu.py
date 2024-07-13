from imgui_bundle import imgui, imgui_ctx

from .._utils import controller_types
from .._plot_area import PlotArea


class RightClickMenu:
    def __init__(self, figure):
        self.figure = figure

        self._last_right_click_pos = None

        self._is_open = False

    def get_subplot(self) -> PlotArea:
        if self._last_right_click_pos is None:
            return False

        for subplot in self.figure:
            if subplot.viewport.is_inside(*self._last_right_click_pos):
                return subplot

    def update(self):
        # TODO: detect mouse click vs. just pointer_down
        #  which is what imgui actually does, issue with
        #  imgui.is_mouse_clicked is that it conflicts with
        #  controller right-click + drag
        if imgui.is_mouse_double_clicked(1):
            # if not imgui.is_mouse_dragging(1):
            self._last_right_click_pos = imgui.get_mouse_pos()

            if self.get_subplot():
                # open only if right click was inside a subplot
                imgui.open_popup(f"right-click-menu")
                self._is_open = True
                self.figure.renderer.disable_events()
                self.get_subplot().controller._actions = {}  # cancel any scheduled events

        if imgui.begin_popup(f"right-click-menu"):
            if imgui.menu_item(f"Autoscale", None, False)[0]:
                self.get_subplot().auto_scale()

            if imgui.menu_item(f"Center", None, False)[0]:
                self.get_subplot().auto_scale()

            _, enabled_controller = imgui.menu_item(
                "Controller Enabled", None, self.get_subplot().controller.enabled
            )
            self.get_subplot().controller.enabled = enabled_controller

            _, maintain_aspect = imgui.menu_item(
                "Maintain Aspect", None, self.get_subplot().camera.maintain_aspect
            )
            self.get_subplot().camera.maintain_aspect = maintain_aspect

            # controller must be disabled for this
            # orig_val = self.get_subplot().controller.enabled
            # self.get_subplot().controller.enabled = False
            changed, fov = imgui.slider_int(
                "FOV",
                v=int(self.get_subplot().camera.fov),
                v_min=0,
                v_max=180,
            )
            if changed:
                self.get_subplot().controller.update_fov(
                    fov - self.get_subplot().camera.fov, animate=False
                )
            # self.get_subplot().controller.enabled = orig_val

            if imgui.begin_menu("Controller Type"):
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

        elif self._is_open:
            # went from open -> closed
            self.figure.renderer.enable_events()
