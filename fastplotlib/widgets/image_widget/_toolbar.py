from imgui_bundle import imgui, icons_fontawesome_6 as fa, imgui_ctx


ID_COUNTER = 0


class ImageWidgetToolbar:
    def __init__(self, image_widget, icons: imgui.ImFont):
        self._image_widget = image_widget
        self.icons = icons

        # required to prevent conflict with multiple Figures
        global ID_COUNTER
        ID_COUNTER += 1

        self.id = ID_COUNTER

    def update(self):
        width, height = self._image_widget.figure.renderer.logical_size
        width -= self._image_widget.figure.imgui_reserved_canvas[0]
        height -= self._image_widget.figure.imgui_reserved_canvas[1]

        pos = (0, height)

        imgui.set_next_window_size((width, 0))
        imgui.set_next_window_pos(pos)
        flags = imgui.WindowFlags_.no_collapse | imgui.WindowFlags_.no_title_bar

        imgui.begin(f"ImageWidget controls", p_open=None, flags=flags)

        # imgui.push_font(self.icons)

        new_index = dict()
        flag_index_changed = False
        imgui.push_id(self.id)  # push ID to prevent conflict between multiple figs with same UI
        for dim in self._image_widget.slider_dims:
            val = self._image_widget.current_index[dim]
            vmax = self._image_widget._dims_max_bounds[dim] - 1

            imgui.text(f"{dim}: ")
            imgui.same_line()
            imgui.set_next_item_width(width * 0.8)  # so that sliders occupies full width
            changed, index = imgui.slider_int(f"{dim}", v=val, v_min=0, v_max=vmax)

            new_index[dim] = index

            flag_index_changed |= changed

        # pad bottom of figure
        self._image_widget.figure.imgui_reserved_canvas[1] = max(self._image_widget.n_scrollable_dims) * 40

        if flag_index_changed:
            self._image_widget.current_index = new_index

        imgui.pop_id()

        # imgui.pop_font()

        imgui.end()
