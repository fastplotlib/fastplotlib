from imgui_bundle import imgui

from ...layouts._utils import controller_types
from ...layouts._plot_area import PlotArea
from ...ui import Popup


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


class StandardRightClickMenu(Popup):
    """Right click menu that is shown on subplots"""

    def __init__(self, figure, fa_icons):
        super().__init__(figure=figure, fa_icons=fa_icons)

        self._last_right_click_pos = None
        self._mouse_down: bool = False

        # whether the right click menu is currently open or not
        self.is_open: bool = False

    def get_subplot(self) -> PlotArea | bool:
        """get the subplot that a click occurred in"""
        if self._last_right_click_pos is None:
            return False

        for subplot in self._figure:
            if subplot.viewport.is_inside(*self._last_right_click_pos):
                return subplot

    def cleanup(self):
        """called when the popup disappears"""
        self.is_open = False

    def update(self):
        if imgui.is_mouse_down(1) and not self._mouse_down:
            # mouse button was pressed down, store this position
            self._mouse_down = True
            self._last_right_click_pos = imgui.get_mouse_pos()

        if imgui.is_mouse_released(1) and self._mouse_down:
            self._mouse_down = False

            # open popup only if mouse was not moved between mouse_down and mouse_up events
            if self._last_right_click_pos == imgui.get_mouse_pos():
                if self.get_subplot() is not False:  # must explicitly check for False
                    # open only if right click was inside a subplot
                    imgui.open_popup(f"right-click-menu")

        # TODO: call this just once when going from open -> closed state
        if not imgui.is_popup_open("right-click-menu"):
            self.cleanup()

        if imgui.begin_popup(f"right-click-menu"):
            if self.get_subplot() is False:  # must explicitly check for False
                # for some reason it will still trigger at certain locations
                # despite open_popup() only being called when an actual
                # subplot is returned
                imgui.end_popup()
                imgui.close_current_popup()
                self.cleanup()
                return

            name = self.get_subplot().name

            if name is not None:
                # text label at the top of the menu
                imgui.text(f"subplot: {name}")
                imgui.separator()

            # autoscale, center, maintain aspect
            if imgui.menu_item(f"Autoscale", "", False)[0]:
                self.get_subplot().auto_scale()

            if imgui.menu_item(f"Center", "", False)[0]:
                self.get_subplot().center_scene()

            _, maintain_aspect = imgui.menu_item(
                "Maintain Aspect", "", self.get_subplot().camera.maintain_aspect
            )
            self.get_subplot().camera.maintain_aspect = maintain_aspect

            imgui.separator()

            # toggles to flip axes cameras
            for axis in ["x", "y", "z"]:
                scale = getattr(self.get_subplot().camera.local, f"scale_{axis}")
                changed, flip = imgui.menu_item(
                    f"Flip {axis} axis", "", bool(scale < 0)
                )

                if changed:
                    flip_axis(self.get_subplot(), axis, flip)

            imgui.separator()

            # toggles to show/hide the grid
            for plane in ["xy", "xz", "yz"]:
                grid = getattr(self.get_subplot().axes.grids, plane)
                visible = grid.visible
                changed, new_visible = imgui.menu_item(f"Grid {plane}", "", visible)

                if changed:
                    grid.visible = new_visible

            imgui.separator()

            # camera FOV
            changed, fov = imgui.slider_float(
                "FOV", v=self.get_subplot().camera.fov, v_min=0.0, v_max=180.0
            )

            imgui.separator()

            if changed:
                # FOV between 0 and 1 is numerically unstable
                if 0 < fov < 1:
                    fov = 1

                # need to update FOV via controller, if FOV is directly set
                # on the camera the controller will immediately set it back
                self.get_subplot().controller.update_fov(
                    fov - self.get_subplot().camera.fov,
                    animate=False,
                )

            imgui.separator()

            # controller options
            if imgui.begin_menu("Controller"):
                _, enabled = imgui.menu_item(
                    "Enabled", "", self.get_subplot().controller.enabled
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
                # switching between different controllers
                for name, controller_type_iter in controller_types.items():
                    current_type = type(self.get_subplot().controller)

                    clicked, _ = imgui.menu_item(
                        label=name,
                        shortcut="",
                        p_selected=current_type is controller_type_iter,
                    )

                    if clicked and (current_type is not controller_type_iter):
                        # menu item was clicked and the desired controller isn't the current one
                        self.get_subplot().controller = name

                imgui.end_menu()

            imgui.end_popup()
