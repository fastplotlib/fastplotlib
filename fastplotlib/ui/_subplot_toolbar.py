from imgui_bundle import imgui, icons_fontawesome_6 as fa, imgui_ctx

from ..layouts._subplot import Subplot
from ._base import Window
from ..layouts._utils import IMGUI_TOOLBAR_HEIGHT


class SubplotToolbar(Window):
    def __init__(self, subplot: Subplot, fa_icons: imgui.ImFont):
        """
        Subplot toolbar shown below all subplots
        """
        super().__init__()

        self._subplot = subplot
        self._fa_icons = fa_icons

    def update(self):
        # get subplot rect
        x, y, width, height = self._subplot.frame.rect

        # place the toolbar window below the subplot
        pos = (x + 1, y + height - IMGUI_TOOLBAR_HEIGHT)

        imgui.set_next_window_size((width - 18, 0))
        imgui.set_next_window_pos(pos)
        flags = (
            imgui.WindowFlags_.no_collapse
            | imgui.WindowFlags_.no_title_bar
            | imgui.WindowFlags_.no_background
        )

        imgui.begin(f"Toolbar-{hex(id(self._subplot))}", p_open=None, flags=flags)

        # icons for buttons
        imgui.push_font(self._fa_icons)

        # push ID to prevent conflict between multiple figs with same UI
        imgui.push_id(self._id_counter)
        with imgui_ctx.begin_horizontal(f"toolbar-{hex(id(self._subplot))}"):
            # autoscale button
            if imgui.button(fa.ICON_FA_MAXIMIZE):
                self._subplot.auto_scale()
            imgui.pop_font()
            if imgui.is_item_hovered(0):
                imgui.set_tooltip("autoscale scene")

            # center scene
            imgui.push_font(self._fa_icons)
            if imgui.button(fa.ICON_FA_ALIGN_CENTER):
                self._subplot.center_scene()
            imgui.pop_font()
            if imgui.is_item_hovered(0):
                imgui.set_tooltip("center scene")

            imgui.push_font(self._fa_icons)
            # checkbox controller
            _, self._subplot.controller.enabled = imgui.checkbox(
                fa.ICON_FA_COMPUTER_MOUSE, self._subplot.controller.enabled
            )
            imgui.pop_font()
            if imgui.is_item_hovered(0):
                imgui.set_tooltip("enable/disable controller")

            imgui.push_font(self._fa_icons)
            # checkbox maintain_apsect
            _, self._subplot.camera.maintain_aspect = imgui.checkbox(
                fa.ICON_FA_EXPAND, self._subplot.camera.maintain_aspect
            )
            imgui.pop_font()
            if imgui.is_item_hovered(0):
                imgui.set_tooltip("maintain aspect")

        # pop id when all UI has been written to window
        imgui.pop_id()

        # end window
        imgui.end()
