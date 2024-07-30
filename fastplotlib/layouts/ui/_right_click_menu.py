import numpy as np

from imgui_bundle import imgui

from .._utils import controller_types
from .._plot_area import PlotArea
from ._base import BaseGUI


def flip_axis(subplot: PlotArea, axis: str, flip: bool):
    camera = subplot.camera
    axis_attr = f"scale_{axis}"
    scale = getattr(camera.local, axis_attr)

    if flip and scale > 0:
        # flip is checked and axis is not already flipped
        setattr(camera.local, axis_attr, scale * -1)

    elif not flip and scale < 0:
        # flip not checked and axis is flipped
        setattr(camera.local, axis_attr, scale * -1)


class RightClickMenu(BaseGUI):
    def __init__(self, owner, fa_icons, size=None):
        super().__init__(owner=owner, fa_icons=fa_icons, size=None)
        self._last_right_click_pos = None

        self._mouse_down: bool = False

        self.owner.renderer.event_filters["right-click-menu"] = np.array(
            [[-1, -1], [-1, -1]]
        )

        self.owner.renderer.event_filters["controller-menu"] = np.array(
            [[-1, -1], [-1, -1]]
        )

    def reset_event_filters(self):
        for k in ["right-click-menu", "controller-menu"]:
            self.owner.renderer.event_filters[k][:] = [-1, -1], [-1, -1]

    def set_event_filter(self, name: str):
        x1, y1 = imgui.get_window_pos()
        width, height = imgui.get_window_size()
        x2, y2 = x1 + width, y1 + height

        self.owner.renderer.event_filters[name][:] = [x1 - 1, y1 - 1], [x2 + 4, y2 + 4]

    def get_subplot(self) -> PlotArea | bool:
        if self._last_right_click_pos is None:
            return False

        for subplot in self.owner:
            if subplot.viewport.is_inside(*self._last_right_click_pos):
                return subplot

    def update(self):
        if imgui.is_mouse_down(1) and not self._mouse_down:
            self._mouse_down = True
            self._last_right_click_pos = imgui.get_mouse_pos()

        if imgui.is_mouse_released(1) and self._mouse_down:
            self._mouse_down = False

            # mouse was not moved between down and up events
            if self._last_right_click_pos == imgui.get_mouse_pos():
                if self.get_subplot():
                    # open only if right click was inside a subplot
                    imgui.open_popup(f"right-click-menu")

        if not imgui.is_popup_open("right-click-menu"):
            self.reset_event_filters()

        if imgui.begin_popup(f"right-click-menu"):
            self.set_event_filter("right-click-menu")

            if not self.get_subplot():
                # for some reason it will still trigger at certain locations
                # despite open_popup() only being called when an actual
                # subplot is returned
                imgui.end_popup()
                imgui.close_current_popup()
                return

            name = self.get_subplot().name
            if name is None:
                name = self.get_subplot().position

            imgui.text(f"subplot: {name}")
            imgui.separator()

            if imgui.menu_item(f"Autoscale", None, False)[0]:
                self.get_subplot().auto_scale()

            if imgui.menu_item(f"Center", None, False)[0]:
                self.get_subplot().center_scene()

            _, maintain_aspect = imgui.menu_item(
                "Maintain Aspect", None, self.get_subplot().camera.maintain_aspect
            )
            self.get_subplot().camera.maintain_aspect = maintain_aspect

            imgui.separator()

            for axis in ["x", "y", "z"]:
                scale = getattr(self.get_subplot().camera.local, f"scale_{axis}")
                changed, flip = imgui.menu_item(f"Flip {axis} axis", None, scale < 0)

                if changed:
                    flip_axis(self.get_subplot(), axis, flip)

            imgui.separator()

            for plane in ["xy", "xz", "yz"]:
                grid = getattr(self.get_subplot().axes.grids, plane)
                visible = grid.visible
                changed, new_visible = imgui.menu_item(f"Grid {plane}", None, visible)

                if changed:
                    grid.visible = new_visible

            imgui.separator()

            changed, fov = imgui.slider_float(
                "FOV", v=self.get_subplot().camera.fov, v_min=0.0, v_max=180.0
            )

            imgui.separator()

            if changed:
                # FOV between 0 and 1 is numerically unstable
                if 0 < fov < 1:
                    fov = 1
                self.get_subplot().controller.update_fov(
                    fov - self.get_subplot().camera.fov,
                    animate=False,
                )

            imgui.separator()

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
