from imgui_bundle import imgui

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
                imgui.open_popup(f"cmap-picker")
                self._is_open = True
                self.figure.renderer.disable_events()
                self.get_subplot().controller._actions = (
                    {}
                )  # cancel any scheduled events

        if imgui.begin_popup(f"cmap-picker"):
            imgui.text("Uniform")
