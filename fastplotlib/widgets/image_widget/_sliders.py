from time import perf_counter

from imgui_bundle import imgui, icons_fontawesome_6 as fa

from ...ui import EdgeWindow


class ImageWidgetSliders(EdgeWindow):
    def __init__(self, figure, size, location, title, image_widget):
        super().__init__(figure=figure, size=size, location=location, title=title)
        self._image_widget = image_widget

        self._playing: dict[str, bool] = {"t": False, "z": False}

        self._step_size = 1

        self._fps: dict[str, int] = {"t": 20, "z": 20}
        self._frame_time: dict[str, float] = {"t": 1 / 20, "z": 1 / 20}

        # last timepoint a frame was displayed from a given dimension
        self._last_frame_time: dict[str, float] = {"t": 0, "z": 0}

        self._loop = False

    def set_index(self, dim: str, index: int):
        max_index = self._image_widget._dims_max_bounds[dim] - 1
        if index > max_index:
            if self._loop:
                index = 0
            else:
                self._playing[dim] = False
                return

        self._image_widget.current_index = {dim: min(index, max_index)}

    def update(self):
        new_index = dict()
        flag_index_changed = False

        imgui.push_font(self._fa_icons)
        if imgui.button(label=fa.ICON_FA_CIRCLE_HALF_STROKE + fa.ICON_FA_FILM):
            self._image_widget.reset_vmin_vmax()
        imgui.pop_font()
        if imgui.is_item_hovered(0):
            imgui.set_tooltip("reset contrast limits using full movie/stack")

        imgui.push_font(self._fa_icons)
        imgui.same_line()
        if imgui.button(label=fa.ICON_FA_CIRCLE_HALF_STROKE):
            self._image_widget.reset_vmin_vmax_frame()
        imgui.pop_font()
        if imgui.is_item_hovered(0):
            imgui.set_tooltip("reset contrast limits using current frame")

        now = perf_counter()
        for dim in self._image_widget.slider_dims:
            imgui.push_id(f"{self._id_counter}_{dim}")
            imgui.push_font(self._fa_icons)

            if self._playing[dim]:
                if imgui.button(label=fa.ICON_FA_PAUSE):
                    self._playing[dim] = False

                if now - self._last_frame_time[dim] >= self._frame_time[dim]:
                    self.set_index(dim, self._image_widget.current_index[dim] + 1)
                    self._last_frame_time[dim] = now

            else:
                if imgui.button(label=fa.ICON_FA_PLAY):
                    self._last_frame_time[dim] = 0
                    self._playing[dim] = True

            imgui.same_line()
            if imgui.button(label=fa.ICON_FA_BACKWARD_STEP) and not self._playing[dim]:
                self.set_index(dim, self._image_widget.current_index[dim] - 1)

            imgui.same_line()
            if imgui.button(label=fa.ICON_FA_FORWARD_STEP) and not self._playing[dim]:
                self.set_index(dim, self._image_widget.current_index[dim] + 1)

            imgui.same_line()
            if imgui.button(label=fa.ICON_FA_STOP):
                self._playing[dim] = False
                self._last_frame_time[dim] = 0
                self.set_index(dim, 0)

            imgui.same_line()
            _, self._loop = imgui.checkbox(label=fa.ICON_FA_ROTATE, v=self._loop)

            imgui.pop_font()

            imgui.same_line()
            imgui.text("framerate :")
            imgui.same_line()
            imgui.set_next_item_width(100)
            changed, value = imgui.input_int(label="fps", v=self._fps[dim], step_fast=5)
            if changed:
                if value < 1:
                    value = 1
                if value > 50:
                    value = 50
                self._fps[dim] = value
                self._frame_time[dim] = 1 / value

            val = self._image_widget.current_index[dim]
            vmax = self._image_widget._dims_max_bounds[dim] - 1

            imgui.text(f"{dim}: ")
            imgui.same_line()
            # so that slider occupies full width
            imgui.set_next_item_width(self.width * 0.85)
            changed, index = imgui.slider_int(f"{dim}", v=val, v_min=0, v_max=vmax)

            new_index[dim] = index

            flag_index_changed |= changed

            imgui.pop_id()

        if flag_index_changed:
            self._image_widget.current_index = new_index

        self.size = int(imgui.get_window_height())
