from imgui_bundle import imgui

from ...layouts._utils import controller_types
from ...layouts._plot_area import PlotArea
from ...ui import ImguiPopup


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


class StandardRightClickMenu(ImguiPopup):
    """Right click menu that is shown on subplots"""

    def __init__(self):
        super().__init__()

        # the subplot whose controller window is open, False if no controller window is open
        self._controller_window_open: bool | PlotArea = False

    def update(self):
        subplot = self.subplot

        if subplot.name is not None:
            # text label at the top of the menu
            imgui.text(f"subplot: {subplot.name}")
            imgui.separator()

        _, show_fps = imgui.menu_item("Show fps", "", self._figure.imgui_show_fps)
        self._figure.imgui_show_fps = show_fps

        # autoscale, center, maintain aspect
        if imgui.menu_item("Autoscale", "", False)[0]:
            subplot.auto_scale()

        if imgui.menu_item("Center", "", False)[0]:
            subplot.center_scene()

        _, maintain_aspect = imgui.menu_item(
            "Maintain Aspect", "", subplot.camera.maintain_aspect
        )
        subplot.camera.maintain_aspect = maintain_aspect

        _, tooltip_enabled = imgui.menu_item("Tooltip", "", subplot.tooltip.enabled)
        subplot.tooltip.enabled = tooltip_enabled

        imgui.separator()

        # toggles to flip axes cameras
        for axis in ["x", "y", "z"]:
            scale = getattr(subplot.camera.local, f"scale_{axis}")
            changed, flip = imgui.menu_item(f"Flip {axis} axis", "", bool(scale < 0))

            if changed:
                flip_axis(subplot, axis, flip)

        imgui.separator()

        # toggles to show/hide the grid
        for plane in ["xy", "xz", "yz"]:
            grid = getattr(subplot.axes.grids, plane)
            changed, visible = imgui.menu_item(f"Grid {plane}", "", grid.visible)

            if changed:
                grid.visible = visible

        imgui.separator()

        # camera FOV
        changed, fov = imgui.slider_float(
            "FOV", v=subplot.camera.fov, v_min=0.0, v_max=180.0
        )

        if changed:
            # FOV between 0 and 1 is numerically unstable
            if 0 < fov < 1:
                fov = 1

            # need to update FOV via controller, if FOV is directly set
            # on the camera the controller will immediately set it back
            subplot.controller.update_fov(fov - subplot.camera.fov, animate=False)

        imgui.separator()

        # controller options
        if imgui.menu_item("Controller Options", "", False)[0]:
            self._controller_window_open = subplot

    def draw(self):
        super().draw()

        # the controller window is not part of the popup, it stays open after the popup closes
        if self._controller_window_open:
            self._draw_controller_window()

    def _draw_controller_window(self):
        subplot = self._controller_window_open

        imgui.set_next_window_size((0, 0))
        _, keep_open = imgui.begin(f"Controller", True)
        imgui.text(f"subplot: {subplot.name}")
        _, enabled = imgui.menu_item(
            "Enabled", "", subplot.controller.enabled
        )

        subplot.controller.enabled = enabled

        changed, damping = imgui.slider_float(
            "Damping",
            v=subplot.controller.damping,
            v_min=0.0,
            v_max=10.0,
        )

        if changed:
            subplot.controller.damping = damping

        imgui.separator()
        imgui.text("Controller type:")
        # switching between different controllers
        for name, controller_type_iter in controller_types.items():
            current_type = type(subplot.controller)

            clicked, _ = imgui.menu_item(
                label=name,
                shortcut="",
                p_selected=current_type is controller_type_iter,
            )

            if clicked and (current_type is not controller_type_iter):
                # menu item was clicked and the desired controller isn't the current one
                subplot.controller = name

        if not keep_open:
            self._controller_window_open = False

        imgui.end()
