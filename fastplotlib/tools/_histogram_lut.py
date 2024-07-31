from math import ceil
import weakref

import numpy as np

import pygfx

from ..graphics import LineGraphic, ImageGraphic, TextGraphic
from ..graphics.utils import pause_events
from ..graphics._base import Graphic
from ..graphics.selectors import LinearRegionSelector


def _get_image_graphic_events(image_graphic: ImageGraphic) -> list[str]:
    """Small helper function to return the relevant events for an ImageGraphic"""
    events = ["vmin", "vmax"]

    if not image_graphic.data.value.ndim > 2:
        events.append("cmap")

    # if RGB(A), do not add cmap

    return events


# TODO: This is a widget, we can think about a BaseWidget class later if necessary
class HistogramLUTTool(Graphic):
    def __init__(
        self,
        data: np.ndarray,
        image_graphic: ImageGraphic,
        nbins: int = 100,
        flank_divisor: float = 5.0,
        **kwargs,
    ):
        """

        Parameters
        ----------
        data
        image_graphic
        nbins: int, defaut 100.
            Total number of bins used in the histogram
        flank_divisor: float, default 5.0.
            Fraction of empty histogram bins on the tails of the distribution set `np.inf` for no flanks
        kwargs
        """
        super().__init__(**kwargs)

        self._nbins = nbins
        self._flank_divisor = flank_divisor
        self._image_graphic = image_graphic

        self._data = weakref.proxy(data)

        self._scale_factor: float = 1.0

        hist, edges, hist_scaled, edges_flanked = self._calculate_histogram(data)

        line_data = np.column_stack([hist_scaled, edges_flanked])

        self._histogram_line = LineGraphic(line_data)

        bounds = (edges[0] * self._scale_factor, edges[-1] * self._scale_factor)
        limits = (edges_flanked[0], edges_flanked[-1])
        size = 120  # since it's scaled to 100
        origin = (hist_scaled.max() / 2, 0)

        self._linear_region_selector = LinearRegionSelector(
            selection=bounds,
            limits=limits,
            size=size,
            center=origin[0],
            axis="y",
            edge_thickness=8,
            parent=self._histogram_line,
        )

        # there will be a small difference with the histogram edges so this makes them both line up exactly
        self._linear_region_selector.selection = (
            self._image_graphic.vmin * self._scale_factor,
            self._image_graphic.vmax * self._scale_factor,
        )

        self._vmin = self.image_graphic.vmin
        self._vmax = self.image_graphic.vmax

        vmin_str, vmax_str = self._get_vmin_vmax_str()

        self._text_vmin = TextGraphic(
            text=vmin_str,
            font_size=16,
            offset=(0, 0, 0),
            anchor="top-left",
            outline_color="black",
            outline_thickness=1,
        )

        self._text_vmin.world_object.material.pick_write = False

        self._text_vmax = TextGraphic(
            text=vmax_str,
            font_size=16,
            offset=(0, 0, 0),
            anchor="bottom-left",
            outline_color="black",
            outline_thickness=1,
        )

        self._text_vmax.world_object.material.pick_write = False

        widget_wo = pygfx.Group()
        widget_wo.add(
            self._histogram_line.world_object,
            self._linear_region_selector.world_object,
            self._text_vmin.world_object,
            self._text_vmax.world_object,
        )

        self._set_world_object(widget_wo)

        self.world_object.local.scale_x *= -1

        self._text_vmin.offset = (-120, self._linear_region_selector.selection[0], 0)

        self._text_vmax.offset = (-120, self._linear_region_selector.selection[1], 0)

        self._linear_region_selector.add_event_handler(
            self._linear_region_handler, "selection"
        )

        ig_events = _get_image_graphic_events(self.image_graphic)

        self.image_graphic.add_event_handler(self._image_cmap_handler, *ig_events)

        # colorbar for grayscale images
        if self.image_graphic.data.value.ndim != 3:
            self._colorbar: ImageGraphic = self._make_colorbar(edges_flanked)
            self._colorbar.add_event_handler(self._open_cmap_picker, "click")

            self.world_object.add(self._colorbar.world_object)
        else:
            self._colorbar = None
            self._cmap = None

    def _make_colorbar(self, edges_flanked) -> ImageGraphic:
        # use the histogram edge values as data for an
        # image with 2 columns, this will be our colorbar!
        colorbar_data = np.column_stack(
            [
                np.linspace(
                    edges_flanked[0], edges_flanked[-1], ceil(np.ptp(edges_flanked))
                )
            ]
            * 2
        ).astype(np.float32)

        colorbar_data /= self._scale_factor

        cbar = ImageGraphic(
            data=colorbar_data,
            vmin=self.vmin,
            vmax=self.vmax,
            cmap=self.image_graphic.cmap,
            interpolation="linear",
            offset=(-55, edges_flanked[0], -1),
        )

        cbar.world_object.world.scale_x = 20
        self._cmap = self.image_graphic.cmap

        return cbar

    def _get_vmin_vmax_str(self) -> tuple[str, str]:
        if self.vmin < 0.001 or self.vmin > 99_999:
            vmin_str = f"{self.vmin:.2e}"
        else:
            vmin_str = f"{self.vmin:.2f}"

        if self.vmax < 0.001 or self.vmax > 99_999:
            vmax_str = f"{self.vmax:.2e}"
        else:
            vmax_str = f"{self.vmax:.2f}"

        return vmin_str, vmax_str

    def _fpl_add_plot_area_hook(self, plot_area):
        self._plot_area = plot_area
        self._linear_region_selector._fpl_add_plot_area_hook(plot_area)
        self._histogram_line._fpl_add_plot_area_hook(plot_area)

        self._plot_area.auto_scale()
        self._plot_area.controller.enabled = True

    def _calculate_histogram(self, data):
        if data.ndim > 2:
            # subsample to max of 500 x 100 x 100,
            # np.histogram takes ~30ms with this size on a 8 core Ryzen laptop
            # dim0 is usually time, allow max of 500 timepoints
            ss0 = max(1, int(data.shape[0] / 500))  # max to prevent step = 0
            # allow max of 100 for x and y if ndim > 2
            ss1 = max(1, int(data.shape[1] / 100))
            ss2 = max(1, int(data.shape[2] / 100))

            data_ss = data[::ss0, ::ss1, ::ss2]

            hist, edges = np.histogram(data_ss, bins=self._nbins)

        else:
            # allow max of 1000 x 1000
            # this takes ~4ms on a 8 core Ryzen laptop
            ss0 = max(1, int(data.shape[0] / 1_000))
            ss1 = max(1, int(data.shape[1] / 1_000))

            data_ss = data[::ss0, ::ss1]

            hist, edges = np.histogram(data_ss, bins=self._nbins)

        # used if data ptp <= 10 because event things get weird
        # with tiny world objects due to floating point error
        # so if ptp <= 10, scale up by a factor
        data_interval = edges[-1] - edges[0]
        self._scale_factor: int = max(1, 100 * int(10 / data_interval))

        edges = edges * self._scale_factor

        bin_width = edges[1] - edges[0]

        flank_nbins = int(self._nbins / self._flank_divisor)
        flank_size = flank_nbins * bin_width

        flank_left = np.arange(edges[0] - flank_size, edges[0], bin_width)
        flank_right = np.arange(
            edges[-1] + bin_width, edges[-1] + flank_size, bin_width
        )

        edges_flanked = np.concatenate((flank_left, edges, flank_right))

        hist_flanked = np.concatenate(
            (np.zeros(flank_nbins), hist, np.zeros(flank_nbins))
        )

        # scale 0-100 to make it easier to see
        # float32 data can produce unnecessarily high values
        hist_scale_value = hist_flanked.max()
        if np.allclose(hist_scale_value, 0):
            hist_scale_value = 1
        hist_scaled = hist_flanked / (hist_scale_value / 100)

        if edges_flanked.size > hist_scaled.size:
            # we don't care about accuracy here so if it's off by 1-2 bins that's fine
            edges_flanked = edges_flanked[: hist_scaled.size]

        return hist, edges, hist_scaled, edges_flanked

    def _linear_region_handler(self, ev):
        # must use world coordinate values directly from selection()
        # otherwise the linear region bounds jump to the closest bin edges
        selected_ixs = self._linear_region_selector.selection
        vmin, vmax = selected_ixs[0], selected_ixs[1]
        vmin, vmax = vmin / self._scale_factor, vmax / self._scale_factor
        self.vmin, self.vmax = vmin, vmax

    def _image_cmap_handler(self, ev):
        setattr(self, ev.type, ev.info["value"])

    @property
    def cmap(self) -> str:
        return self._cmap

    @cmap.setter
    def cmap(self, name: str):
        if self._colorbar is None:
            return

        with pause_events(self.image_graphic):
            self.image_graphic.cmap = name

            self._cmap = name
            self._colorbar.cmap = name

    @property
    def vmin(self) -> float:
        return self._vmin

    @vmin.setter
    def vmin(self, value: float):
        with pause_events(self.image_graphic, self._linear_region_selector):
            # must use world coordinate values directly from selection()
            # otherwise the linear region bounds jump to the closest bin edges
            self._linear_region_selector.selection = (
                value * self._scale_factor,
                self._linear_region_selector.selection[1],
            )
            self.image_graphic.vmin = value

        self._vmin = value
        if self._colorbar is not None:
            self._colorbar.vmin = value

        vmin_str, vmax_str = self._get_vmin_vmax_str()
        self._text_vmin.offset = (-120, self._linear_region_selector.selection[0], 0)
        self._text_vmin.text = vmin_str

    @property
    def vmax(self) -> float:
        return self._vmax

    @vmax.setter
    def vmax(self, value: float):
        with pause_events(self.image_graphic, self._linear_region_selector):
            # must use world coordinate values directly from selection()
            # otherwise the linear region bounds jump to the closest bin edges
            self._linear_region_selector.selection = (
                self._linear_region_selector.selection[0],
                value * self._scale_factor,
            )

            self.image_graphic.vmax = value

        self._vmax = value
        if self._colorbar is not None:
            self._colorbar.vmax = value

        vmin_str, vmax_str = self._get_vmin_vmax_str()
        self._text_vmax.offset = (-120, self._linear_region_selector.selection[1], 0)
        self._text_vmax.text = vmax_str

    def set_data(self, data, reset_vmin_vmax: bool = True):
        hist, edges, hist_scaled, edges_flanked = self._calculate_histogram(data)

        line_data = np.column_stack([hist_scaled, edges_flanked])

        # set x and y vals
        self._histogram_line.data[:, :2] = line_data

        bounds = (edges[0], edges[-1])
        limits = (edges_flanked[0], edges_flanked[-11])
        origin = (hist_scaled.max() / 2, 0)

        if reset_vmin_vmax:
            # reset according to the new data
            self._linear_region_selector.limits = limits
            self._linear_region_selector.selection = bounds
        else:
            with pause_events(self.image_graphic, self._linear_region_selector):
                # don't change the current selection
                self._linear_region_selector.limits = limits

        self._data = weakref.proxy(data)

        if self._colorbar is not None:
            self._colorbar.clear_event_handlers()
            self.world_object.remove(self._colorbar.world_object)

        if self.image_graphic.data.value.ndim != 3:
            self._colorbar: ImageGraphic = self._make_colorbar(edges_flanked)
            self._colorbar.add_event_handler(self._open_cmap_picker, "click")

            self.world_object.add(self._colorbar.world_object)
        else:
            self._colorbar = None
            self._cmap = None

        # reset plotarea dims
        self._plot_area.auto_scale()

    @property
    def image_graphic(self) -> ImageGraphic:
        return self._image_graphic

    @image_graphic.setter
    def image_graphic(self, graphic):
        if not isinstance(graphic, ImageGraphic):
            raise TypeError(
                f"HistogramLUTTool can only use ImageGraphic types, you have passed: {type(graphic)}"
            )

        if self._image_graphic is not None:
            # cleanup events from current image graphic
            ig_events = _get_image_graphic_events(self._image_graphic)
            self._image_graphic.remove_event_handler(
                self._image_cmap_handler, *ig_events
            )

        self._image_graphic = graphic

        ig_events = _get_image_graphic_events(self._image_graphic)

        self.image_graphic.add_event_handler(self._image_cmap_handler, *ig_events)

    def disconnect_image_graphic(self):
        ig_events = _get_image_graphic_events(self._image_graphic)
        self._image_graphic.remove_event_handler(self._image_cmap_handler, *ig_events)
        del self._image_graphic
        # self._image_graphic = None

    def _open_cmap_picker(self, ev):
        # check if right click
        if ev.button != 2:
            return

        pos = ev.x, ev.y

        self._plot_area.get_figure().open_popup("colormap-picker", pos, lut_tool=self)

    def _fpl_prepare_del(self):
        self._linear_region_selector._fpl_prepare_del()
        self._histogram_line._fpl_prepare_del()
        del self._histogram_line
        del self._linear_region_selector
