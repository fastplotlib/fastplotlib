from imgui_bundle import imgui, icons_fontawesome_6 as fa, imgui_ctx

from .._plot_area import PlotArea


class SubplotToolbar:
    def __init__(self, subplot: PlotArea, icons: imgui.ImFont):
        self._subplot = subplot
        self.icons = icons

    @property
    def subplot(self):
        return self._subplot

    def update(self):
        # imgui.new_frame()

        x, y, width, height = self.subplot.get_rect()

        pos = (x, y + height)

        imgui.set_next_window_size((width, 0))
        imgui.set_next_window_pos(pos)
        flags = imgui.WindowFlags_.no_collapse | imgui.WindowFlags_.no_title_bar

        imgui.begin(f"Toolbar-{self._subplot.position}", p_open=None, flags=flags)

        imgui.push_font(self.icons)
        with imgui_ctx.begin_horizontal(f"toolbar-{self._subplot.position}"):
            if imgui.button(fa.ICON_FA_MAXIMIZE):
                self._subplot.auto_scale()
            imgui.pop_font()

            if imgui.is_item_hovered(0):
                imgui.set_tooltip("autoscale scene")

            imgui.push_font(self.icons)

            if imgui.button(fa.ICON_FA_ALIGN_CENTER):
                self._subplot.center_scene()

            _, self._subplot.controller.enabled = imgui.checkbox(fa.ICON_FA_COMPUTER_MOUSE, self._subplot.controller.enabled)
            _, self._subplot.camera.maintain_aspect = imgui.checkbox(fa.ICON_FA_EXPAND, self._subplot.camera.maintain_aspect)

        imgui.pop_font()

        imgui.end()
        #
        # imgui.end_frame()
        # imgui.render()

        # return imgui.get_draw_data()
