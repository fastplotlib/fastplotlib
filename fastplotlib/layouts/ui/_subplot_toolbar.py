from imgui_bundle import imgui, icons_fontawesome_6 as fa, imgui_ctx

from .._plot_area import PlotArea
from ._base import BaseGUI


class SubplotToolbar(BaseGUI):
    def __init__(self, owner: PlotArea, fa_icons: imgui.ImFont):
        super().__init__(owner=owner, fa_icons=fa_icons, size=None)

    def update(self):
        x, y, width, height = self.owner.get_rect()

        pos = (x, y + height)

        imgui.set_next_window_size((width, 0))
        imgui.set_next_window_pos(pos)
        flags = imgui.WindowFlags_.no_collapse | imgui.WindowFlags_.no_title_bar

        imgui.begin(f"Toolbar-{self.owner.position}", p_open=None, flags=flags)

        imgui.push_font(self._fa_icons)

        imgui.push_id(
            self._id_counter
        )  # push ID to prevent conflict between multiple figs with same UI
        with imgui_ctx.begin_horizontal(f"toolbar-{self.owner.position}"):
            # autoscale button
            if imgui.button(fa.ICON_FA_MAXIMIZE):
                self.owner.auto_scale()
            imgui.pop_font()
            if imgui.is_item_hovered(0):
                imgui.set_tooltip("autoscale scene")

            # center scene
            imgui.push_font(self._fa_icons)
            if imgui.button(fa.ICON_FA_ALIGN_CENTER):
                self.owner.center_scene()
            imgui.pop_font()
            if imgui.is_item_hovered(0):
                imgui.set_tooltip("center scene")

            imgui.push_font(self._fa_icons)
            # checkbox controller
            _, self.owner.controller.enabled = imgui.checkbox(
                fa.ICON_FA_COMPUTER_MOUSE, self.owner.controller.enabled
            )
            imgui.pop_font()
            if imgui.is_item_hovered(0):
                imgui.set_tooltip("enable/disable controller")

            imgui.push_font(self._fa_icons)
            # checkbox maintain_apsect
            _, self.owner.camera.maintain_aspect = imgui.checkbox(
                fa.ICON_FA_EXPAND, self.owner.camera.maintain_aspect
            )
            imgui.pop_font()
            if imgui.is_item_hovered(0):
                imgui.set_tooltip("maintain aspect")

        imgui.pop_id()

        imgui.end()
