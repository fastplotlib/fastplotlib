import os
from time import perf_counter

from imgui_bundle import imgui, icons_fontawesome_6 as fa

from ...ui import EdgeWindow


class ImageWidgetSliders(EdgeWindow):
    def __init__(self, figure, size, location, title, image_widget):
        super().__init__(figure=figure, size=size, location=location, title=title)
        self._image_widget = image_widget

        n_sliders = self._image_widget.n_sliders

        # whether or not a dimension is in play mode
        self._playing: list[bool] = [False] * n_sliders

        # approximate framerate for playing
        self._fps: list[int] = [20] * n_sliders

        # framerate converted to frame time
        self._frame_time: list[float] = [1 / 20] * n_sliders

        # last timepoint that a frame was displayed from a given dimension
        self._last_frame_time: list[float] = [perf_counter()] * n_sliders

        # loop playback
        self._loop = False

        # auto-plays the ImageWidget's left-most dimension in docs galleries
        if "DOCS_BUILD" in os.environ.keys():
            if os.environ["DOCS_BUILD"] == "1":
                self._playing[0] = True
                self._loop = True

        self.pause = False

    def pop_dim(self):
        """pop right most dim"""
        i = 0 # len(self._image_widget.indices) - 1
        for l in [self._playing, self._fps, self._frame_time, self._last_frame_time]:
            l.pop(i)

    def push_dim(self):
        """push a new dim"""
        self._playing.insert(0, False)
        self._fps.insert(0, 20)
        self._frame_time.insert(0, 1 / 20)
        self._last_frame_time.insert(0, perf_counter())

    def set_index(self, dim: int, new_index: int):
        """set the index of the ImageWidget"""

        # make sure the max index for this dim is not exceeded
        max_index = self._image_widget.bounds[dim] - 1
        if new_index > max_index:
            if self._loop:
                # loop back to index zero if looping is enabled
                new_index = 0
            else:
                # if looping not enabled, stop playing this dimension
                self._playing[dim] = False
                return

        # set new index
        new_indices = list(self._image_widget.indices)
        new_indices[dim] = new_index
        self._image_widget.indices = new_indices

    def update(self):
        """called on every render cycle to update the GUI elements"""

        # reset vmin-vmax using full orig data
        if imgui.button(label=fa.ICON_FA_CIRCLE_HALF_STROKE + fa.ICON_FA_FILM):
            self._image_widget.reset_vmin_vmax()
        if imgui.is_item_hovered(0):
            imgui.set_tooltip("reset contrast limits using full movie/stack")

        # reset vmin-vmax using currently displayed ImageGraphic data
        imgui.same_line()
        if imgui.button(label=fa.ICON_FA_CIRCLE_HALF_STROKE):
            self._image_widget.reset_vmin_vmax_frame()
        if imgui.is_item_hovered(0):
            imgui.set_tooltip("reset contrast limits using current frame")

        # time now
        now = perf_counter()

        # self._size = 300#57 + (self._image_widget.n_sliders * 50)

        # buttons and slider UI elements for each dim
        for dim in range(self._image_widget.n_sliders):
            imgui.push_id(f"{self._id_counter}_{dim}")

            if self._playing[dim]:
                # show pause button if playing
                if imgui.button(label=fa.ICON_FA_PAUSE):
                    # if pause button clicked, then set playing to false
                    self._playing[dim] = False

                # if in play mode and enough time has elapsed w.r.t. the desired framerate, increment the index
                if now - self._last_frame_time[dim] >= self._frame_time[dim]:
                    self.set_index(dim, self._image_widget.indices[dim] + 1)
                    self._last_frame_time[dim] = now

            else:
                # we are not playing, so display play button
                if imgui.button(label=fa.ICON_FA_PLAY):
                    # if play button is clicked, set last frame time to 0 so that index increments on next render
                    self._last_frame_time[dim] = 0
                    # set playing to True since play button was clicked
                    self._playing[dim] = True

            imgui.same_line()
            # step back one frame button
            if imgui.button(label=fa.ICON_FA_BACKWARD_STEP) and not self._playing[dim]:
                self.set_index(dim, self._image_widget.indices[dim] - 1)

            imgui.same_line()
            # step forward one frame button
            if imgui.button(label=fa.ICON_FA_FORWARD_STEP) and not self._playing[dim]:
                self.set_index(dim, self._image_widget.indices[dim] + 1)

            imgui.same_line()
            # stop button
            if imgui.button(label=fa.ICON_FA_STOP):
                self._playing[dim] = False
                self._last_frame_time[dim] = 0
                self.set_index(dim, 0)

            imgui.same_line()
            # loop checkbox
            _, self._loop = imgui.checkbox(label=fa.ICON_FA_ROTATE, v=self._loop)
            if imgui.is_item_hovered(0):
                imgui.set_tooltip("loop playback")

            imgui.same_line()
            imgui.text("framerate :")
            imgui.same_line()
            imgui.set_next_item_width(100)
            # framerate int entry
            fps_changed, value = imgui.input_int(
                label="fps", v=self._fps[dim], step_fast=5
            )
            if imgui.is_item_hovered(0):
                imgui.set_tooltip(
                    "framerate is approximate and less reliable as it approaches your monitor refresh rate"
                )
            if fps_changed:
                if value < 1:
                    value = 1
                if value > 50:
                    value = 50
                self._fps[dim] = value
                self._frame_time[dim] = 1 / value

            val = self._image_widget.indices[dim]
            vmax = self._image_widget.bounds[dim] - 1

            dim_name = dim
            if self._image_widget._slider_dim_names is not None:
                if dim < len(self._image_widget._slider_dim_names):
                    dim_name = self._image_widget._slider_dim_names[dim]

            imgui.text(f"dim {dim_name}: ")
            imgui.same_line()
            # so that slider occupies full width
            imgui.set_next_item_width(self.width * 0.85)

            if "Jupyter" in self._image_widget.figure.canvas.__class__.__name__:
                # until https://github.com/pygfx/wgpu-py/issues/530
                flags = imgui.SliderFlags_.no_input
            else:
                # clamps to min, max if user inputs value outside these bounds
                flags = imgui.SliderFlags_.always_clamp

            # slider for this dimension
            changed, index = imgui.slider_int(
                f"{dim}", v=val, v_min=0, v_max=vmax, flags=flags
            )

            if changed:
                new_indices = list(self._image_widget.indices)
                new_indices[dim] = index
                self._image_widget.indices = new_indices

            imgui.pop_id()

        self.size = int(imgui.get_window_height())
