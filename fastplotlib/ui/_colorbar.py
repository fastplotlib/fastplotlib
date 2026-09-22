import weakref

import numpy as np
import wgpu
from cmap import Colormap
from imgui_bundle import imgui

from ..graphics import Graphic, ImageGraphic, ImageVolumeGraphic
from ..graphics._positions_base import PositionsGraphic
from ..utils.functions import COLORMAP_NAMES, quick_min_max
from ._base import ImguiContainer


def colormaps_equal(a: str | Colormap, b: str | Colormap) -> bool:
    """
    Whether two colormaps, given as names or as ``Colormap`` instances, are the same.

    ``Colormap.__eq__`` compares the color stops and raises if the two colormaps do not have the
    same number of them, which means they are not the same colormap.
    """
    try:
        return a == b
    except ValueError:
        return False


class ImguiColorbar(ImguiContainer):
    LUT_HEIGHT = 256
    TEX_WIDTH = 2
    HANDLE_HEIGHT = 8
    HANDLE_OVERHANG = 3  # how far a handle extends past the bar on each side
    BAR_BORDER = 1.0  # width of the outline drawn around the bar image
    HIST_WIDTH = 50  # width in pixels of the optional histogram drawn left of the bar
    HIST_GAP = 4  # gap in pixels between the histogram and the bar
    FILL_OVERHANG = (
        4  # how far the vmin/vmax fill and lines extend past the histogram line-plot
    )

    # preview textures for the colormap picker, keyed by imgui renderer. They are the same for
    # every colorbar and there is one per non-qualitative colormap, so they are made once per
    # figure and shared. Weakly keyed so a closed figure is not kept alive by its textures.
    _PICKER_TEXTURE_IDS = weakref.WeakKeyDictionary()

    def __init__(
        self,
        graphics: ImageGraphic | ImageVolumeGraphic | PositionsGraphic | list[Graphic],
        histogram: tuple[np.ndarray, np.ndarray] | None = None,
        data_range: tuple[float, float] | None = None,
        title: str | None = None,
        height: int | None = None,
        bar_width: int = 16,
        region_drag: bool = True,
    ):
        """
        An imgui colorbar with draggable vmin/vmax handles, an optional histogram, a gamma slider, and a
        right-click colormap picker.

        Parameters
        ----------
        graphics: ImageGraphic | ImageVolumeGraphic | LineGraphic | ScatterGraphic | list
            the graphic(s) whose colormap and value range this colorbar controls. The bar drives ``vmin`` and
            ``vmax`` of an image, and ``cmap_range`` of a line or scatter, which must already have a ``cmap``.

        histogram: tuple[np.ndarray, np.ndarray], optional
            a precomputed ``(counts, edges)`` histogram drawn to the left of the bar. It is not recomputed when the
            graphic's data changes, set the ``histogram`` property to update it.

        data_range: (min, max), optional
            the value range spanned by the bar. Defaults to the histogram edges if a histogram is provided,
            otherwise to the data range of the first graphic.

        title: str, optional
            title drawn above the bar, no title is drawn if ``None``

        height: int, optional
            height of the colorbar in pixels, fills the available vertical space if ``None``

        bar_width: int
            width of the colored bar in pixels

        region_drag: bool
            if ``True``, dragging between the handles shifts the vmin/vmax window without changing its width
        """
        super().__init__()

        self._graphics = self._validate_graphics(graphics)

        graphic = self._graphics[0]
        self._vmin, self._vmax = self._get_clim(graphic)
        # rgb(a) images have no cmap, display the bar with "gray" so vmin, vmax are still adjustable
        self._cmap_name = graphic.cmap if graphic.cmap is not None else "gray"

        self._gamma = 1.0
        self._title = title
        self._height = int(height) if height is not None else None
        self._bar_width = int(bar_width)
        self._region_drag = bool(region_drag)

        # offset in data units between the grabbed value and the value under the cursor, captured when a drag
        # starts so the handle tracks the cursor without jumping
        self._grab_offset = 0.0

        # prevents feedback loops when syncing vmin, vmax, cmap between this colorbar and the graphics
        self._block_reentrance = False

        # whether a handle is hovered this frame, drives the resize cursor
        self._hovering_handle = False
        self._resize_cursor_set = False

        # GPU resources, created in _fpl_add_hook() once the figure and its device are known
        self._device = None
        self._bar_texture = None
        self._bar_tex_id = None

        # setting the histogram also sets the value axis to the histogram edges
        self._histogram = None
        self.histogram = histogram

        # data_range defaults to the histogram edges, otherwise the data range of the first graphic
        if data_range is None:
            if self._histogram is not None:
                counts, edges = self._histogram
                data_range = (float(edges[0]), float(edges[-1]))
            else:
                data_range = self._get_data_range(graphic)
        self._data_min, self._data_max = self._validate_range(data_range)

    def _fpl_add_hook(self, figure):
        super()._fpl_add_hook(figure)

        self._device = figure.renderer.device

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

        # sync the colorbar when a graphic's value range, cmap, or gamma is changed elsewhere
        for graphic in self._graphics:
            self._connect_graphic(graphic)

    @staticmethod
    def _validate_graphics(graphics) -> list[Graphic]:
        """the graphics this colorbar can manage, as a list"""
        if isinstance(graphics, Graphic):
            graphics = [graphics]

        graphics = list(graphics)
        if len(graphics) == 0:
            raise ValueError("must provide at least one graphic")

        for graphic in graphics:
            if not isinstance(
                graphic, (ImageGraphic, ImageVolumeGraphic, PositionsGraphic)
            ):
                raise TypeError(
                    f"a colorbar can manage images, lines and scatters, you have passed a: "
                    f"{type(graphic).__name__}"
                )
            if isinstance(graphic, PositionsGraphic) and graphic.cmap is None:
                raise ValueError(
                    "a line or scatter must have a `cmap` set to be managed by a colorbar, the bar drives its "
                    "`cmap_range`"
                )

        return graphics

    @staticmethod
    def _get_clim(graphic) -> tuple[float, float]:
        """the (min, max) that ``graphic`` maps onto the colormap"""
        if isinstance(graphic, PositionsGraphic):
            return graphic.cmap_range

        return float(graphic.vmin), float(graphic.vmax)

    @staticmethod
    def _set_clim(graphic, vmin: float, vmax: float):
        """set the (min, max) that ``graphic`` maps onto the colormap"""
        if isinstance(graphic, PositionsGraphic):
            graphic.cmap_range = (vmin, vmax)
            return

        graphic.vmin = vmin
        graphic.vmax = vmax

    @staticmethod
    def _get_data_range(graphic) -> tuple[float, float]:
        """the value range the bar spans by default"""
        if isinstance(graphic, PositionsGraphic):
            transform = graphic.cmap_transform
            return float(transform.min()), float(transform.max())

        return quick_min_max(graphic.data.value)

    @property
    def _has_gamma(self) -> bool:
        """whether any managed graphic has a gamma, lines and scatters do not"""
        return any(
            isinstance(g, (ImageGraphic, ImageVolumeGraphic)) for g in self._graphics
        )

    @property
    def graphics(self) -> tuple:
        """get or set the graphics managed by this colorbar"""
        return tuple(self._graphics)

    @graphics.setter
    def graphics(self, new_graphics):
        self._disconnect_graphics()
        self._graphics = self._validate_graphics(new_graphics)

        # adopt the value range and cmap of the new first graphic
        graphic = self._graphics[0]
        self._vmin, self._vmax = self._get_clim(graphic)
        self._cmap_name = graphic.cmap if graphic.cmap is not None else "gray"
        self._update_bar_texture()

        for g in self._graphics:
            self._connect_graphic(g)

    @property
    def title(self) -> str | None:
        """get or set the title drawn above the bar, ``None`` for no title"""
        return self._title

    @title.setter
    def title(self, value: str | None):
        self._title = value

    @property
    def height(self) -> int | None:
        """get or set the height of the colorbar in pixels, ``None`` fills the available space"""
        return self._height

    @height.setter
    def height(self, value: int | None):
        self._height = int(value) if value is not None else None

    @property
    def cmap(self) -> str:
        """get or set the colormap"""
        return self._cmap_name

    @cmap.setter
    def cmap(self, name: str):
        if self._block_reentrance or name is None:
            return

        if colormaps_equal(name, self._cmap_name):
            return
        self._block_reentrance = True
        try:
            self._cmap_name = name
            self._update_bar_texture()
            for graphic in self._graphics:
                if graphic.cmap is None:
                    # rgb(a) images have no cmap
                    continue
                graphic.cmap = name
        finally:
            self._block_reentrance = False

    @property
    def vmin(self) -> float:
        """get or set the lower contrast limit"""
        return max(self._vmin, self._axis_range()[0])

    @vmin.setter
    def vmin(self, value: float):
        value = float(value)
        if self._block_reentrance or value == self._vmin:
            return
        self._block_reentrance = True
        try:
            self._vmin = value
            self._update_bar_texture()
            self._apply_clim()
        finally:
            self._block_reentrance = False

    @property
    def vmax(self) -> float:
        """get or set the upper contrast limit"""
        return min(self._vmax, self._axis_range()[1])

    @vmax.setter
    def vmax(self, value: float):
        value = float(value)
        if self._block_reentrance or value == self._vmax:
            return
        self._block_reentrance = True
        try:
            self._vmax = value
            self._update_bar_texture()
            self._apply_clim()
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
            for graphic in self._graphics:
                if isinstance(graphic, PositionsGraphic):
                    # lines and scatters have no gamma
                    continue
                graphic.gamma = value
        finally:
            self._block_reentrance = False

    @property
    def bar_width(self) -> int:
        """get or set the width of the colored bar in pixels"""
        return self._bar_width

    @bar_width.setter
    def bar_width(self, value: int):
        self._bar_width = int(value)

    @staticmethod
    def _validate_range(data_range):
        data_min, data_max = float(data_range[0]), float(data_range[1])
        if data_max <= data_min:
            raise ValueError(
                f"data_range max ({data_max}) must be greater than min ({data_min})"
            )
        return data_min, data_max

    def _apply_clim(self):
        """write the current vmin, vmax to the managed graphics"""
        for graphic in self._graphics:
            self._set_clim(graphic, self._vmin, self._vmax)

    def _graphic_event_handler(self, ev):
        """when a graphic's value range, cmap, or gamma changes, update this colorbar to match"""
        if ev.type == "cmap_range":
            self.vmin, self.vmax = ev.info["value"]
            return

        setattr(self, ev.type, ev.info["value"])

    def _connect_graphic(self, graphic):
        """subscribe to the events of the properties this colorbar drives"""
        if isinstance(graphic, PositionsGraphic):
            events = ["cmap_range", "cmap"]
        else:
            events = ["vmin", "vmax", "gamma"]
            # rgb(a) images have no cmap feature to listen to
            if graphic.cmap is not None:
                events.append("cmap")

        graphic.add_event_handler(self._graphic_event_handler, *events)

    def _disconnect_graphics(self, *args):
        """disconnect the event handlers of the managed graphics"""
        for graphic in self._graphics:
            for ev, handlers in graphic.event_handlers:
                if self._graphic_event_handler in handlers:
                    graphic.remove_event_handler(self._graphic_event_handler, ev)

    def _get_picker_texture_ids(self) -> dict:
        """the colormap preview textures of the picker, made on first use and shared per figure"""
        renderer = self._figure.imgui_renderer

        texture_ids = self._PICKER_TEXTURE_IDS.get(renderer)
        if texture_ids is not None:
            return texture_ids

        # a preview texture for each non-qualitative colormap
        texture_ids = dict()
        for category, names in COLORMAP_NAMES.items():
            if category == "qualitative":
                continue
            for name in names:
                texture_ids[name] = self._make_picker_texture(name)

        self._PICKER_TEXTURE_IDS[renderer] = texture_ids

        return texture_ids

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
        lo = (self.vmin - axis_min) / span
        hi = (self.vmax - axis_min) / span
        t = np.linspace(1.0, 0.0, self.LUT_HEIGHT)
        norm = np.clip((t - lo) / (hi - lo), 0.0, 1.0)
        norm = norm**self._gamma
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
        total_h = avail.y if self._height is None else float(self._height)

        if self._title is not None:
            # centered above the bar, the region below it is what the bar is drawn in
            text_w = imgui.calc_text_size(self._title).x
            imgui.set_cursor_pos_x(
                imgui.get_cursor_pos_x() + max(0.0, (avail.x - text_w) * 0.5)
            )
            imgui.text(self._title)
            p0 = imgui.get_cursor_screen_pos()
            total_h -= line_h

        bar_w = self._bar_width
        # the value axis spans the height minus a line of padding at the top and bottom
        bar_y = p0.y + line_h
        bar_h = max(50.0, total_h - 2 * line_h)

        # accumulated across the region lines and bar handles to drive the resize cursor
        self._hovering_handle = False

        # anchor the bar to the right edge of the window; the histogram and value text sit to its left,
        # the handle overhang stays within the window padding
        bar_x = p0.x + avail.x - self.HANDLE_OVERHANG - bar_w

        has_hist = self._histogram is not None
        if has_hist:
            # the histogram has a fixed width (HIST_WIDTH), drawn to the left of the bar
            hist_x_right = bar_x - self.HIST_GAP
            hist_x_left = hist_x_right - self.HIST_WIDTH

            # histogram line profile, inset so the vmin/vmax fill and lines extend beyond it
            self._draw_histogram(
                draw_list,
                hist_x_left + self.FILL_OVERHANG,
                hist_x_right - self.FILL_OVERHANG,
                bar_y,
                bar_h,
            )
            # draggable vmin, vmax lines, shaded region, and value text drawn over the histogram
            self._draw_region(hist_x_left, hist_x_right, bar_y, bar_h)

        # the colorbar bar
        imgui.set_cursor_screen_pos((bar_x, bar_y))
        imgui.push_style_color(imgui.Col_.border, (1.0, 1.0, 1.0, 1.0))
        imgui.push_style_var(imgui.StyleVar_.image_border_size, self.BAR_BORDER)
        imgui.image(self._bar_tex_id, image_size=(bar_w - 2 * self.BAR_BORDER, bar_h))
        imgui.pop_style_var()
        imgui.pop_style_color()

        # right-click for the gamma slider and colormap picker
        if imgui.begin_popup_context_window("##colorbar_popup"):
            self._draw_popup()
            imgui.end_popup()

        # without a histogram the vmin, vmax handles live on the bar itself
        if not has_hist:
            self._draw_bar_handles(bar_x, bar_y, bar_w, bar_h)

        # show a vertical-resize cursor while hovering any handle
        if self._hovering_handle and not self._resize_cursor_set:
            self._figure.canvas.set_cursor("ns_resize")
            self._resize_cursor_set = True
        elif not self._hovering_handle and self._resize_cursor_set:
            self._figure.canvas.set_cursor("default")
            self._resize_cursor_set = False

        # reserve the region so anything drawn after the colorbar is placed below it
        imgui.set_cursor_screen_pos(p0)
        imgui.dummy((avail.x, total_h))

    def _value_to_y(self, v, y0, bar_h):
        axis_min, axis_max = self._axis_range()
        return y0 + (1.0 - (v - axis_min) / (axis_max - axis_min)) * bar_h

    def _y_to_value(self, y, y0, bar_h):
        axis_min, axis_max = self._axis_range()
        return axis_min + (1.0 - (y - y0) / bar_h) * (axis_max - axis_min)

    def _draw_histogram(self, draw_list, x_left, x_right, bar_y, bar_h):
        counts, edges = self._histogram
        cmin = counts.min()
        cmax = counts.max()
        span = cmax - cmin
        if span <= 0:
            return

        color = imgui.color_convert_float4_to_u32((0.7, 0.7, 0.7, 1.0))
        hist_w = x_right - x_left
        if hist_w <= 0:
            return
        # min count maps to the right edge next to the bar, max count to the left edge, filling the width
        norm = (counts - cmin) / span
        centers = 0.5 * (edges[:-1] + edges[1:])

        # frequency increases to the left, away from the bar, value maps to y, drawn as a line profile
        points = [
            imgui.ImVec2(x_right - frac * hist_w, self._value_to_y(c, bar_y, bar_h))
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
        y_vmax = self._value_to_y(self.vmax, bar_y, bar_h)
        y_vmin = self._value_to_y(self.vmin, bar_y, bar_h)
        draw_list.add_rect_filled((x_left, y_vmax), (x_right, y_vmin), fill_color)

        # drag the region between the lines to move both together
        if self._region_drag:
            top = y_vmax + grab / 2
            bottom = y_vmin - grab / 2
            if bottom > top:
                imgui.set_cursor_screen_pos((x_left, top))
                imgui.invisible_button("##region", (width, bottom - top))
                if imgui.is_item_activated():
                    self._grab_offset = 0.5 * (self.vmin + self.vmax) - cursor_value()
                if imgui.is_item_active():
                    half = 0.5 * (self.vmax - self.vmin)
                    center = cursor_value() + self._grab_offset
                    center = max(axis_min + half, min(axis_max - half, center))
                    self.vmin = center - half
                    self.vmax = center + half

        # each line has a hit-window for hovering/dragging; the line turns yellow when hovered or dragged
        for label, attr, lo_fn, hi_fn in (
            ("##vmax_line", "vmax", lambda: self.vmin + min_sep, lambda: axis_max),
            ("##vmin_line", "vmin", lambda: axis_min, lambda: self.vmax - min_sep),
        ):
            cur = getattr(self, attr)
            y = self._value_to_y(cur, bar_y, bar_h)
            imgui.set_cursor_screen_pos((x_left, y - grab / 2))
            imgui.invisible_button(label, (width, grab))
            hovered = imgui.is_item_hovered() or imgui.is_item_active()
            self._hovering_handle = self._hovering_handle or hovered
            if imgui.is_item_activated():
                self._grab_offset = cur - cursor_value()
            if imgui.is_item_active():
                setattr(
                    self,
                    attr,
                    max(lo_fn(), min(hi_fn(), cursor_value() + self._grab_offset)),
                )
                y = self._value_to_y(getattr(self, attr), bar_y, bar_h)
            draw_list.add_line(
                (x_left, y), (x_right, y), yellow if hovered else white, 2.0
            )

        # current vmax above its line, vmin below its line
        y_vmax = self._value_to_y(self.vmax, bar_y, bar_h)
        y_vmin = self._value_to_y(self.vmin, bar_y, bar_h)
        self._text_right(
            draw_list,
            f"{self.vmax:.4g}",
            x_right,
            y_vmax - imgui.get_text_line_height(),
        )
        self._text_right(draw_list, f"{self.vmin:.4g}", x_right, y_vmin)

    def _text_right(self, draw_list, text: str, x_right: float, y: float):
        """draw text right-aligned so it ends at x_right"""
        tw = imgui.calc_text_size(text).x
        draw_list.add_text(
            (x_right - tw, y), imgui.get_color_u32(imgui.Col_.text), text
        )

    def _draw_bar_handles(self, bar_x, bar_y, bar_w, bar_h):
        draw_list = imgui.get_window_draw_list()
        white = imgui.color_convert_float4_to_u32((1.0, 1.0, 1.0, 1.0))
        # yellow highlight when a handle is hovered/dragged, like the region lines
        yellow = imgui.color_convert_float4_to_u32((1.0, 1.0, 0.0, 1.0))
        outline = imgui.color_convert_float4_to_u32((0.0, 0.0, 0.0, 1.0))
        text_color = imgui.get_color_u32(imgui.Col_.text)

        axis_min, axis_max = self._axis_range()
        span = axis_max - axis_min
        h = self.HANDLE_HEIGHT
        # the handles extend past the bar on each side
        x_left = bar_x - self.HANDLE_OVERHANG
        x_right = bar_x + bar_w + self.HANDLE_OVERHANG
        min_sep = (h / bar_h) * span

        def cursor_value():
            return self._y_to_value(imgui.get_io().mouse_pos.y, bar_y, bar_h)

        # thin reference lines at the data min and max, so the flank beyond the data range is visible
        ref = imgui.color_convert_float4_to_u32((1.0, 1.0, 1.0, 1.0))
        for v in (self._data_min, self._data_max):
            y = self._value_to_y(v, bar_y, bar_h)
            draw_list.add_line((x_left, y), (x_right, y), ref, 1.0)

        # drag the region between the handles to move vmin and vmax together
        if self._region_drag:
            y_vmax = self._value_to_y(self.vmax, bar_y, bar_h)
            y_vmin = self._value_to_y(self.vmin, bar_y, bar_h)
            top = y_vmax + h / 2
            bottom = y_vmin - h / 2
            if bottom > top:
                imgui.set_cursor_screen_pos((x_left, top))
                imgui.invisible_button("##bar_region", (x_right - x_left, bottom - top))
                if imgui.is_item_activated():
                    self._grab_offset = 0.5 * (self.vmin + self.vmax) - cursor_value()
                if imgui.is_item_active():
                    half = 0.5 * (self.vmax - self.vmin)
                    center = cursor_value() + self._grab_offset
                    center = max(axis_min + half, min(axis_max - half, center))
                    self.vmin = center - half
                    self.vmax = center + half

        for label, attr, lo_fn, hi_fn in (
            ("##bar_vmax", "vmax", lambda: self.vmin + min_sep, lambda: axis_max),
            ("##bar_vmin", "vmin", lambda: axis_min, lambda: self.vmax - min_sep),
        ):
            cur = getattr(self, attr)
            y = self._value_to_y(cur, bar_y, bar_h)
            imgui.set_cursor_screen_pos((x_left, y - h / 2))
            imgui.invisible_button(label, (x_right - x_left, h))
            hovered = imgui.is_item_hovered() or imgui.is_item_active()
            self._hovering_handle = self._hovering_handle or hovered
            if imgui.is_item_activated():
                self._grab_offset = cur - cursor_value()
            if imgui.is_item_active():
                setattr(
                    self,
                    attr,
                    max(lo_fn(), min(hi_fn(), cursor_value() + self._grab_offset)),
                )
                y = self._value_to_y(getattr(self, attr), bar_y, bar_h)

            draw_list.add_rect_filled(
                (x_left, y - h / 2), (x_right, y + h / 2), yellow if hovered else white
            )
            draw_list.add_rect(
                (x_left, y - h / 2), (x_right, y + h / 2), outline, thickness=1.0
            )

            # current value to the left of the bar, vmax above its handle and vmin below
            text = f"{getattr(self, attr):.4g}"
            ty = y - imgui.get_text_line_height() if attr == "vmax" else y
            tw = imgui.calc_text_size(text).x
            draw_list.add_text((x_left - 3 - tw, ty), text_color, text)

    def _draw_popup(self):
        if self._has_gamma:
            imgui.set_next_item_width(150)
            changed, gamma = imgui.slider_float("gamma", self._gamma, 0.1, 5.0)
            if changed:
                self.gamma = gamma

            # reset gamma to 1.0
            if imgui.menu_item("Reset gamma", "", False)[0]:
                self.gamma = 1.0

        # reset the value range using the data of each graphic
        if imgui.menu_item("Reset range", "", False)[0]:
            for graphic in self._graphics:
                if isinstance(graphic, PositionsGraphic):
                    self._set_clim(graphic, *self._get_data_range(graphic))
                else:
                    graphic.reset_vmin_vmax()

        texture_height = imgui.get_font_size() - 2
        picker_texture_ids = self._get_picker_texture_ids()

        # colormaps grouped by category, qualitative colormaps are not useful for a quantitative colorbar
        for category, names in COLORMAP_NAMES.items():
            if category == "qualitative":
                continue

            imgui.separator()
            imgui.text(category.capitalize())

            for name in names:
                imgui.push_style_color(imgui.Col_.border, (1.0, 1.0, 1.0, 1.0))
                imgui.push_style_var(imgui.StyleVar_.image_border_size, 1.0)
                imgui.image(picker_texture_ids[name], image_size=(75, texture_height))
                imgui.pop_style_var()
                imgui.pop_style_color()

                imgui.same_line()

                clicked, selected = imgui.selectable(
                    name, p_selected=colormaps_equal(name, self._cmap_name)
                )
                if clicked and selected:
                    self.cmap = name
