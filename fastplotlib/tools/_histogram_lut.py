from math import ceil
from typing import Sequence
import weakref

import numpy as np

import pygfx

from ..utils import subsample_array
from ..graphics import LineGraphic, ImageGraphic, ImageVolumeGraphic, TextGraphic
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
        images: (
            ImageGraphic
            | ImageVolumeGraphic
            | Sequence[ImageGraphic | ImageVolumeGraphic]
        ),
        nbins: int = 100,
        flank_divisor: float = 5.0,
        **kwargs,
    ):
        """
        HistogramLUT tool that can be used to control the vmin, vmax of ImageGraphics or ImageVolumeGraphics.
        If used to control multiple images or image volumes it is assumed that they share a representation of
        the same data, and that their histogram, vmin, and vmax are identical. For example, displaying a
        ImageVolumeGraphic and several images that represent slices of the same volume data.

        Parameters
        ----------
        data: np.ndarray

        images: ImageGraphic | ImageVolumeGraphic | tuple[ImageGraphic | ImageVolumeGraphic]

        nbins: int, defaut 100.
            Total number of bins used in the histogram

        flank_divisor: float, default 5.0.
            Fraction of empty histogram bins on the tails of the distribution set `np.inf` for no flanks

        kwargs: passed to ``Graphic``

        """
        super().__init__(create_tooltip, **kwargs)

        self._nbins = nbins
        self._flank_divisor = flank_divisor

        if isinstance(images, (ImageGraphic, ImageVolumeGraphic)):
            images = (images,)
        elif isinstance(images, Sequence):
            if not all(
                [isinstance(ig, (ImageGraphic, ImageVolumeGraphic)) for ig in images]
            ):
                raise TypeError(
                    f"`images` argument must be an ImageGraphic, ImageVolumeGraphic, or a "
                    f"tuple or list or ImageGraphic | ImageVolumeGraphic"
                )
        else:
            raise TypeError(
                f"`images` argument must be an ImageGraphic, ImageVolumeGraphic, or a "
                f"tuple or list or ImageGraphic | ImageVolumeGraphic"
            )

        self._images = images

        self._data = weakref.proxy(data)

        self._scale_factor: float = 1.0

        hist, edges, hist_scaled, edges_flanked = self._calculate_histogram(data)

        line_data = np.column_stack([hist_scaled, edges_flanked])

        self._histogram_line = LineGraphic(
            line_data, colors=(0.8, 0.8, 0.8), alpha_mode="solid", offset=(0, 0, -1)
        )

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
            parent=self._histogram_line,
        )

        self._vmin = self.images[0].vmin
        self._vmax = self.images[0].vmax

        # there will be a small difference with the histogram edges so this makes them both line up exactly
        self._linear_region_selector.selection = (
            self._vmin * self._scale_factor,
            self._vmax * self._scale_factor,
        )

        vmin_str, vmax_str = self._get_vmin_vmax_str()

        self._text_vmin = TextGraphic(
            text=vmin_str,
            font_size=16,
            offset=(0, 0, 0),
            anchor="top-left",
            outline_color="black",
            outline_thickness=0.5,
            alpha_mode="solid",
        )

        self._text_vmin.world_object.material.pick_write = False

        self._text_vmax = TextGraphic(
            text=vmax_str,
            font_size=16,
            offset=(0, 0, 0),
            anchor="bottom-left",
            outline_color="black",
            outline_thickness=0.5,
            alpha_mode="solid",
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

        ig_events = _get_image_graphic_events(self.images[0])

        for ig in self.images:
            ig.add_event_handler(self._image_cmap_handler, *ig_events)

        # colorbar for grayscale images
        if self.images[0].cmap is not None:
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
            cmap=self.images[0].cmap,
            interpolation="linear",
            offset=(-55, edges_flanked[0], -1),
        )

        cbar.world_object.world.scale_x = 20
        self._cmap = self.images[0].cmap

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

        # get a subsampled view of this array
        data_ss = subsample_array(data, max_size=int(1e6))  # 1e6 is default
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

        with pause_events(*self.images):
            for ig in self.images:
                ig.cmap = name

            self._cmap = name
            self._colorbar.cmap = name

    @property
    def vmin(self) -> float:
        return self._vmin

    @vmin.setter
    def vmin(self, value: float):
        with pause_events(self._linear_region_selector, *self.images):
            # must use world coordinate values directly from selection()
            # otherwise the linear region bounds jump to the closest bin edges
            self._linear_region_selector.selection = (
                value * self._scale_factor,
                self._linear_region_selector.selection[1],
            )
            for ig in self.images:
                ig.vmin = value

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
        with pause_events(self._linear_region_selector, *self.images):
            # must use world coordinate values directly from selection()
            # otherwise the linear region bounds jump to the closest bin edges
            self._linear_region_selector.selection = (
                self._linear_region_selector.selection[0],
                value * self._scale_factor,
            )

            for ig in self.images:
                ig.vmax = value

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
            with pause_events(self._linear_region_selector, *self.images):
                # don't change the current selection
                self._linear_region_selector.limits = limits

        self._data = weakref.proxy(data)

        if self._colorbar is not None:
            self._colorbar.clear_event_handlers()
            self.world_object.remove(self._colorbar.world_object)

        if self.images[0].cmap is not None:
            self._colorbar: ImageGraphic = self._make_colorbar(edges_flanked)
            self._colorbar.add_event_handler(self._open_cmap_picker, "click")

            self.world_object.add(self._colorbar.world_object)
        else:
            self._colorbar = None
            self._cmap = None

        # reset plotarea dims
        self._plot_area.auto_scale()

    @property
    def images(self) -> tuple[ImageGraphic | ImageVolumeGraphic]:
        return self._images

    @images.setter
    def images(self, images):
        if isinstance(images, (ImageGraphic, ImageVolumeGraphic)):
            images = (images,)
        elif isinstance(images, Sequence):
            if not all(
                [isinstance(ig, (ImageGraphic, ImageVolumeGraphic)) for ig in images]
            ):
                raise TypeError(
                    f"`images` argument must be an ImageGraphic, ImageVolumeGraphic, or a "
                    f"tuple or list or ImageGraphic | ImageVolumeGraphic"
                )
        else:
            raise TypeError(
                f"`images` argument must be an ImageGraphic, ImageVolumeGraphic, or a "
                f"tuple or list or ImageGraphic | ImageVolumeGraphic"
            )

        if self._images is not None:
            for ig in self._images:
                # cleanup events from current image graphics
                ig_events = _get_image_graphic_events(ig)
                ig.remove_event_handler(self._image_cmap_handler, *ig_events)

        self._images = images

        ig_events = _get_image_graphic_events(self._images[0])

        for ig in self.images:
            ig.add_event_handler(self._image_cmap_handler, *ig_events)

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
