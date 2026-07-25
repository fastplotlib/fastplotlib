import numpy as np
import wgpu
from cmap import Colormap
from imgui_bundle import imgui

from ..graphics import ImageGraphic, ImageVolumeGraphic
from ..utils.functions import COLORMAP_NAMES, quick_min_max
from ._base import ImguiWindow


class ImguiColorbar(ImguiWindow):
    LUT_HEIGHT = 256
    TEX_WIDTH = 2
    HANDLE_HEIGHT = 8
    HANDLE_OVERHANG = 3  # how far a handle extends past the bar on each side
    BAR_BORDER = 1.0  # width of the outline drawn around the bar image
    HIST_WIDTH = 10  # width in pixels of the optional histogram drawn left of the bar
    HIST_GAP = 4  # gap in pixels between the histogram and the bar
    FILL_OVERHANG = 4  # how far the vmin/vmax fill and lines extend past the histogram line-plot

    def __init__(
        self,
        images: ImageGraphic | ImageVolumeGraphic | list,
        histogram: tuple[np.ndarray, np.ndarray] | None = None,
        data_range: tuple[float, float] | None = None,
        bar_width: int = 24,
        region_drag: bool = True,
    ):
        """
        An imgui colorbar with draggable vmin/vmax handles, an optional histogram, a gamma slider, and a
        right-click colormap picker. Bound to one or more images, it replaces the ``HistogramLUTTool``. Add it to a
        subplot edge using ``subplot.add_imgui_window()``.

        Parameters
        ----------
        images: ImageGraphic | ImageVolumeGraphic | list
            the image(s) whose vmin, vmax and cmap this colorbar controls

        histogram: tuple[np.ndarray, np.ndarray], optional
            a precomputed ``(counts, edges)`` histogram drawn to the left of the bar. It is not recomputed when the
            image data changes, set the ``histogram`` property to update it.

        data_range: (min, max), optional
            the value range spanned by the bar. Defaults to the histogram edges if a histogram is provided,
            otherwise to the data range of the first image.

        bar_width: int
            width of the colored bar in pixels

        region_drag: bool
            if ``True``, dragging between the handles shifts the vmin/vmax window without changing its width
        """
        super().__init__()

        if isinstance(images, (ImageGraphic, ImageVolumeGraphic)):
            images = [images]
        self._images = list(images)
        if len(self._images) == 0:
            raise ValueError("must provide at least one image")

        image = self._images[0]
        self._vmin = float(image.vmin)
        self._vmax = float(image.vmax)
        # rgb(a) images have no cmap, display the bar with "gray" so vmin, vmax are still adjustable
        self._cmap_name = image.cmap if image.cmap is not None else "gray"

        self._gamma = 1.0
        self._bar_width = int(bar_width)
        self._region_drag = bool(region_drag)

        # offset in data units between the grabbed value and the value under the cursor, captured when a drag
        # starts so the handle tracks the cursor without jumping
        self._grab_offset = 0.0

        # prevents feedback loops when syncing vmin, vmax, cmap between this colorbar and the images
        self._block_reentrance = False

        # GPU resources, created in _fpl_add_hook() once the figure and its device are known
        self._device = None
        self._bar_texture = None
        self._bar_tex_id = None
        self._picker_tex_ids = dict()

        # setting the histogram also sets the value axis to the histogram edges
        self._histogram = None
        self.histogram = histogram

        # data_range defaults to the histogram edges, otherwise the data range of the first image
        if data_range is None:
            if self._histogram is not None:
                counts, edges = self._histogram
                data_range = (float(edges[0]), float(edges[-1]))
            else:
                data_range = quick_min_max(image.data.value)
        self._data_min, self._data_max = self._validate_range(data_range)

    def _fpl_add_hook(
        self,
        figure,
        subplot=None,
        location: str = None,
        size: int = None,
        rect: tuple = None,
        extent: tuple = None,
        title: str = "",
        window_flags=None,
    ):
        super()._fpl_add_hook(
            figure,
            subplot=subplot,
            location=location,
            size=size,
            rect=rect,
            extent=extent,
            title=title,
            window_flags=window_flags,
        )

        # the colorbar manages its own layout and should never show a scrollbar
        self.window_flags = self._window_flags | imgui.WindowFlags_.no_scrollbar

        self._device = figure.renderer.device

        # a preview texture for each non-qualitative colormap, used in the picker
        for category, names in COLORMAP_NAMES.items():
            if category == "qualitative":
                continue
            for name in names:
                self._picker_tex_ids[name] = self._make_picker_texture(name)

        self._bar_texture = self._device.create_texture(
            size=(self.TEX_WIDTH, self.LUT_HEIGHT, 1),
            usage=wgpu.TextureUsage.COPY_DST | wgpu.TextureUsage.TEXTURE_BINDING,
            dimension=wgpu.TextureDimension.d2,
            format=wgpu.TextureFormat.rgba8unorm,
            mip_level_count=1,
            sample_count=1,
        )
        self._bar_tex_id = figure.imgui_renderer.backend.register_texture(
            self._bar_texture.create_view()
        )
        self._update_bar_texture()

        # sync the colorbar when an image's vmin, vmax, cmap, or gamma is changed elsewhere
        for image in self._images:
            image.add_event_handler(self._image_event_handler, "vmin", "vmax", "cmap", "gamma")

    @property
    def images(self) -> tuple:
        """get or set the images managed by this colorbar"""
        return tuple(self._images)

    @images.setter
    def images(self, new_images):
        self._disconnect_images()
        if isinstance(new_images, (ImageGraphic, ImageVolumeGraphic)):
            new_images = [new_images]
        self._images = list(new_images)

        # adopt the vmin, vmax, and cmap of the new first image
        image = self._images[0]
        self._vmin = float(image.vmin)
        self._vmax = float(image.vmax)
        self._cmap_name = image.cmap if image.cmap is not None else "gray"
        self._update_bar_texture()

        for img in self._images:
            img.add_event_handler(self._image_event_handler, "vmin", "vmax", "cmap", "gamma")

    @property
    def cmap(self) -> str:
        """get or set the colormap"""
        return self._cmap_name

    @cmap.setter
    def cmap(self, name: str):
        if self._block_reentrance or name is None or name == self._cmap_name:
            return
        self._block_reentrance = True
        try:
            self._cmap_name = name
            self._update_bar_texture()
            for image in self._images:
                if image.cmap is None:
                    # rgb(a) images have no cmap
                    continue
                image.cmap = name
        finally:
            self._block_reentrance = False

    @property
    def vmin(self) -> float:
        """get or set the lower contrast limit"""
        return self._vmin

    @vmin.setter
    def vmin(self, value: float):
        value = float(value)
        if self._block_reentrance or value == self._vmin:
            return
        self._block_reentrance = True
        try:
            self._vmin = value
            self._update_bar_texture()
            for image in self._images:
                image.vmin = value
        finally:
            self._block_reentrance = False

    @property
    def vmax(self) -> float:
        """get or set the upper contrast limit"""
        return self._vmax

    @vmax.setter
    def vmax(self, value: float):
        value = float(value)
        if self._block_reentrance or value == self._vmax:
            return
        self._block_reentrance = True
        try:
            self._vmax = value
            self._update_bar_texture()
            for image in self._images:
                image.vmax = value
        finally:
            self._block_reentrance = False

    @property
    def histogram(self) -> tuple[np.ndarray, np.ndarray] | None:
        """the histogram as a precomputed (counts, edges) tuple, or ``None`` for no histogram"""
        return self._histogram

    @histogram.setter
    def histogram(self, value):
        if value is None:
            self._histogram = None
            return
        counts, edges = value
        counts = np.asarray(counts, dtype=np.float32)
        edges = np.asarray(edges, dtype=np.float64)
        if edges.shape[0] != counts.shape[0] + 1:
            raise ValueError(
                "histogram edges must have one more element than counts, you have passed "
                f"counts: {counts.shape[0]} and edges: {edges.shape[0]}"
            )
        self._histogram = (counts, edges)

        # the histogram defines the value axis
        self._data_min = float(edges[0])
        self._data_max = float(edges[-1])
        self._update_bar_texture()

    @property
    def data_range(self) -> tuple[float, float]:
        """the value range spanned by the bar"""
        return (self._data_min, self._data_max)

    @data_range.setter
    def data_range(self, value):
        self._data_min, self._data_max = self._validate_range(value)
        self._update_bar_texture()

    @property
    def gamma(self) -> float:
        """get or set the gamma, applied to the images and the bar"""
        return self._gamma

    @gamma.setter
    def gamma(self, value: float):
        value = float(value)
        if self._block_reentrance or value == self._gamma:
            return
        self._block_reentrance = True
        try:
            self._gamma = value
            self._update_bar_texture()
            for image in self._images:
                image.gamma = value
        finally:
            self._block_reentrance = False

    @staticmethod
    def _validate_range(data_range):
        data_min, data_max = float(data_range[0]), float(data_range[1])
        if data_max <= data_min:
            raise ValueError(
                f"data_range max ({data_max}) must be greater than min ({data_min})"
            )
        return data_min, data_max

    def _image_event_handler(self, ev):
        """when an image's vmin, vmax, or cmap changes, update this colorbar to match"""
        setattr(self, ev.type, ev.info["value"])

    def _disconnect_images(self, *args):
        """disconnect the event handlers of the managed images"""
        for image in self._images:
            for ev, handlers in image.event_handlers:
                if self._image_event_handler in handlers:
                    image.remove_event_handler(self._image_event_handler, ev)

    def _make_picker_texture(self, name):
        lut = (Colormap(name)(np.linspace(0, 1, 256)) * 255).astype(np.uint8)
        data = np.ascontiguousarray(np.tile(lut[None, :, :], (2, 1, 1)))
        h, w = data.shape[:2]
        texture = self._device.create_texture(
            size=(w, h, 1),
            usage=wgpu.TextureUsage.COPY_DST | wgpu.TextureUsage.TEXTURE_BINDING,
            dimension=wgpu.TextureDimension.d2,
            format=wgpu.TextureFormat.rgba8unorm,
            mip_level_count=1,
            sample_count=1,
        )
        self._device.queue.write_texture(
            {"texture": texture, "mip_level": 0, "origin": (0, 0, 0)},
            data,
            {"offset": 0, "bytes_per_row": w * 4},
            (w, h, 1),
        )
        return self._renderer.backend.register_texture(texture.create_view())

    def _update_bar_texture(self):
        if self._bar_texture is None:
            # not added to a figure yet, no device
            return
        # the bar spans the flanked axis so it aligns with the histogram and the handles
        axis_min, axis_max = self._axis_range()
        span = axis_max - axis_min
        lo = (self._vmin - axis_min) / span
        hi = (self._vmax - axis_min) / span
        t = np.linspace(1.0, 0.0, self.LUT_HEIGHT)
        norm = np.clip((t - lo) / (hi - lo), 0.0, 1.0)
        norm = norm ** self._gamma
        colors = (Colormap(self._cmap_name)(norm) * 255).astype(np.uint8)
        data = np.ascontiguousarray(np.tile(colors[:, None, :], (1, self.TEX_WIDTH, 1)))
        self._device.queue.write_texture(
            {"texture": self._bar_texture, "mip_level": 0, "origin": (0, 0, 0)},
            data,
            {"offset": 0, "bytes_per_row": self.TEX_WIDTH * 4},
            (self.TEX_WIDTH, self.LUT_HEIGHT, 1),
        )

    @property
    def _renderer(self):
        return self._figure.imgui_renderer

    def _axis_range(self) -> tuple[float, float]:
        """the value axis: the data range flanked on each side so handles can move past the data extremes"""
        flank = 0.1 * (self._data_max - self._data_min)
        return self._data_min - flank, self._data_max + flank

    def update(self):
        draw_list = imgui.get_window_draw_list()
        avail = imgui.get_content_region_avail()
        line_h = imgui.get_text_line_height_with_spacing()

        p0 = imgui.get_cursor_screen_pos()
        total_w = max(avail.x, self._bar_width + self.HIST_WIDTH + 40)
        total_h = avail.y

        bar_w = self._bar_width
        # the value axis spans the height minus a line for the data max at top and data min at bottom
        bar_y = p0.y + line_h
        bar_h = max(50.0, total_h - 2 * line_h)

        # the colorbar bar is on the right, the histogram fills the space to its left
        bar_x = p0.x + total_w - bar_w
        hist_x_right = bar_x - self.HIST_GAP
        hist_x_left = p0.x

        # data min and max at the top-right and bottom-right
        self._text_right(draw_list, f"{self._data_max:.4g}", bar_x + bar_w, p0.y)
        self._text_right(draw_list, f"{self._data_min:.4g}", bar_x + bar_w, bar_y + bar_h)

        # histogram line profile, inset so the vmin/vmax fill and lines extend beyond it
        if self._histogram is not None:
            self._draw_histogram(
                draw_list,
                hist_x_left + self.FILL_OVERHANG,
                hist_x_right - self.FILL_OVERHANG,
                bar_y,
                bar_h,
            )

        # draggable vmin, vmax lines and shaded region drawn over the histogram
        self._draw_region(hist_x_left, hist_x_right, bar_y, bar_h)

        # the colorbar bar
        imgui.set_cursor_screen_pos((bar_x, bar_y))
        imgui.push_style_color(imgui.Col_.border, (1.0, 1.0, 1.0, 1.0))
        imgui.push_style_var(imgui.StyleVar_.image_border_size, self.BAR_BORDER)
        imgui.image(self._bar_tex_id, image_size=(bar_w - 2 * self.BAR_BORDER, bar_h))
        imgui.pop_style_var()
        imgui.pop_style_color()

        # right-click the bar for the gamma slider and colormap picker
        if imgui.begin_popup_context_item("##colorbar_popup"):
            self._draw_popup()
            imgui.end_popup()

    def _value_to_y(self, v, y0, bar_h):
        axis_min, axis_max = self._axis_range()
        return y0 + (1.0 - (v - axis_min) / (axis_max - axis_min)) * bar_h

    def _y_to_value(self, y, y0, bar_h):
        axis_min, axis_max = self._axis_range()
        return axis_min + (1.0 - (y - y0) / bar_h) * (axis_max - axis_min)

    def _text_right(self, draw_list, text: str, x_right: float, y: float):
        """draw text right-aligned so it ends at x_right"""
        tw = imgui.calc_text_size(text).x
        draw_list.add_text((x_right - tw, y), imgui.get_color_u32(imgui.Col_.text), text)

    def _draw_histogram(self, draw_list, x_left, x_right, bar_y, bar_h):
        counts, edges = self._histogram
        cmin = counts.min()
        cmax = counts.max()
        span = cmax - cmin
        if span <= 0:
            return

        color = imgui.color_convert_float4_to_u32((0.7, 0.7, 0.7, 1.0))
        hist_w = x_right - x_left
        # min count maps to the left edge, max count to the right edge, filling the width
        norm = (counts - cmin) / span
        centers = 0.5 * (edges[:-1] + edges[1:])

        # frequency increases to the right, value maps to y, drawn as a line profile
        points = [
            imgui.ImVec2(x_left + frac * hist_w, self._value_to_y(c, bar_y, bar_h))
            for frac, c in zip(norm, centers)
        ]
        draw_list.add_polyline(points, color, 1.5, 0)

    def _draw_region(self, x_left, x_right, bar_y, bar_h):
        draw_list = imgui.get_window_draw_list()
        white = imgui.color_convert_float4_to_u32((1.0, 1.0, 1.0, 1.0))
        # yellow highlight when a line is hovered/dragged, like the HistogramLUTTool
        yellow = imgui.color_convert_float4_to_u32((1.0, 1.0, 0.0, 1.0))
        # dark blue fill, the same color as the HistogramLUTTool LinearRegionSelector
        fill_color = imgui.color_convert_float4_to_u32((0.0, 0.0, 0.35, 0.4))

        axis_min, axis_max = self._axis_range()
        span = axis_max - axis_min
        width = x_right - x_left
        grab = self.HANDLE_HEIGHT
        min_sep = (grab / bar_h) * span

        def cursor_value():
            # the data value under the cursor. Lines track this absolute position (plus the grab offset)
            # rather than accumulating per-frame deltas, so a fast drag past an edge pins the line to the extreme
            return self._y_to_value(imgui.get_io().mouse_pos.y, bar_y, bar_h)

        # shaded fill between the vmin and vmax lines
        y_vmax = self._value_to_y(self._vmax, bar_y, bar_h)
        y_vmin = self._value_to_y(self._vmin, bar_y, bar_h)
        draw_list.add_rect_filled((x_left, y_vmax), (x_right, y_vmin), fill_color)

        # drag the region between the lines to move both together
        if self._region_drag:
            top = y_vmax + grab / 2
            bottom = y_vmin - grab / 2
            if bottom > top:
                imgui.set_cursor_screen_pos((x_left, top))
                imgui.invisible_button("##region", (width, bottom - top))
                if imgui.is_item_activated():
                    self._grab_offset = 0.5 * (self._vmin + self._vmax) - cursor_value()
                if imgui.is_item_active():
                    half = 0.5 * (self._vmax - self._vmin)
                    center = cursor_value() + self._grab_offset
                    center = max(axis_min + half, min(axis_max - half, center))
                    self.vmin = center - half
                    self.vmax = center + half

        # each line has a hit-window for hovering/dragging; the line turns yellow when hovered or dragged
        for label, attr, lo_fn, hi_fn in (
            ("##vmax_line", "vmax", lambda: self._vmin + min_sep, lambda: axis_max),
            ("##vmin_line", "vmin", lambda: axis_min, lambda: self._vmax - min_sep),
        ):
            cur = getattr(self, attr)
            y = self._value_to_y(cur, bar_y, bar_h)
            imgui.set_cursor_screen_pos((x_left, y - grab / 2))
            imgui.invisible_button(label, (width, grab))
            hovered = imgui.is_item_hovered() or imgui.is_item_active()
            if imgui.is_item_activated():
                self._grab_offset = cur - cursor_value()
            if imgui.is_item_active():
                setattr(self, attr, max(lo_fn(), min(hi_fn(), cursor_value() + self._grab_offset)))
                y = self._value_to_y(getattr(self, attr), bar_y, bar_h)
            draw_list.add_line((x_left, y), (x_right, y), yellow if hovered else white, 2.0)

        # current vmax above its line, vmin below its line
        y_vmax = self._value_to_y(self._vmax, bar_y, bar_h)
        y_vmin = self._value_to_y(self._vmin, bar_y, bar_h)
        self._text_right(draw_list, f"{self._vmax:.4g}", x_right, y_vmax - imgui.get_text_line_height())
        self._text_right(draw_list, f"{self._vmin:.4g}", x_right, y_vmin)

    def _draw_popup(self):
        imgui.set_next_item_width(150)
        changed, gamma = imgui.slider_float("gamma", self._gamma, 0.1, 5.0)
        if changed:
            self.gamma = gamma

        # reset vmin, vmax using the data of each image
        if imgui.menu_item("Reset vmin-vmax", "", False)[0]:
            for image in self._images:
                image.reset_vmin_vmax()

        texture_height = imgui.get_font_size() - 2

        # colormaps grouped by category, qualitative colormaps are not useful for a continuous colorbar
        for category, names in COLORMAP_NAMES.items():
            if category == "qualitative":
                continue

            imgui.separator()
            imgui.text(category.capitalize())

            for name in names:
                imgui.push_style_color(imgui.Col_.border, (1.0, 1.0, 1.0, 1.0))
                imgui.push_style_var(imgui.StyleVar_.image_border_size, 1.0)
                imgui.image(self._picker_tex_ids[name], image_size=(50, texture_height))
                imgui.pop_style_var()
                imgui.pop_style_color()

                imgui.same_line()

                clicked, selected = imgui.selectable(name, p_selected=(name == self._cmap_name))
                if clicked and selected:
                    self.cmap = name
