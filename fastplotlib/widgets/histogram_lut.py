import numpy as np

from pygfx import Group

from ..graphics import LineGraphic, ImageGraphic
from ..graphics._base import Graphic
from ..graphics.selectors import LinearRegionSelector


# TODO: This is a widget, we can think about a BaseWidget class later if necessary
class HistogramLUT(Graphic):
    def __init__(
            self,
            data: np.ndarray,
            image_graphic: ImageGraphic,
            nbins: int = 100,
            **kwargs
    ):
        super().__init__(**kwargs)

        self.nbins = nbins
        self._image_graphic = image_graphic

        hist, edges, hist_scaled, edges_flanked = self._calculate_histogram(data)

        line_data = np.column_stack([hist_scaled, edges_flanked])

        self.line = LineGraphic(line_data)

        bounds = (edges[0], edges[-1])
        limits = (edges_flanked[0], edges_flanked[-1])
        size = 120  # since it's scaled to 100
        origin = (hist_scaled.max() / 2, 0)

        self.linear_region = LinearRegionSelector(
            bounds=bounds,
            limits=limits,
            size=size,
            origin=origin,
            axis="y",
        )

        widget_wo = Group()
        widget_wo.add(self.line.world_object, self.linear_region.world_object)

        self._set_world_object(widget_wo)

        self.world_object.local.scale_x *= -1

        self.linear_region.selection.add_event_handler(
            self._set_vmin_vmax
        )

    def _add_plot_area_hook(self, plot_area):
        self._plot_area = plot_area
        self.linear_region._add_plot_area_hook(plot_area)
        self.line._add_plot_area_hook(plot_area)

    def _calculate_histogram(self, data):
        if data.ndim > 2:
            # subsample to max of 500 x 100 x 100,
            # np.histogram takes ~30ms with this size on a 8 core Ryzen laptop
            # dim0 is usually time, allow max of 500 timepoints
            ss0 = int(data.shape[0] / 500)
            # allow max of 100 for x and y if ndim > 2
            ss1 = int(data.shape[1] / 100)
            ss2 = int(data.shape[2] / 100)

            hist, edges = np.histogram(data[::ss0, ::ss1, ::ss2], bins=self.nbins)

        else:
            # allow max of 1000 x 1000
            # this takes ~4ms on a 8 core Ryzen laptop
            ss0 = int(data.shape[0] / 1_000)
            ss1 = int(data.shape[1] / 1_000)

            hist, edges = np.histogram(data[::ss0, ::ss1], bins=self.nbins)

        bin_width = edges[1] - edges[0]

        flank_nbins = int(self.nbins / 3)
        flank_size = flank_nbins * bin_width

        flank_left = np.arange(edges[0] - flank_size, edges[0], bin_width)
        flank_right = np.arange(edges[-1] + bin_width, edges[-1] + flank_size, bin_width)

        edges_flanked = np.concatenate((flank_left, edges, flank_right))
        np.unique(np.diff(edges_flanked))

        hist_flanked = np.concatenate((np.zeros(flank_nbins), hist, np.zeros(flank_nbins)))

        # scale 0-100 to make it easier to see
        # float32 data can produce unnecessarily high values
        hist_scaled = hist_flanked / (hist_flanked.max() / 100)

        return hist, edges, hist_scaled, edges_flanked

    def _set_vmin_vmax(self, ev):
        selected = self.linear_region.get_selected_data(self.line)[:, 1]
        self.image_graphic.cmap.vmin = selected[0]
        self.image_graphic.cmap.vmax = selected[-1]

    def set_data(self, data):
        hist, edges, hist_scaled, edges_flanked = self._calculate_histogram(data)

        line_data = np.column_stack([hist_scaled, edges_flanked])

        self.line.data = line_data

        bounds = (edges[0], edges[-1])
        limits = (edges_flanked[0], edges_flanked[-11])
        origin = (hist_scaled.max() / 2, 0)

        self.linear_region.limits = limits
        self.linear_region.selection = bounds
        # self.linear_region.fill.world.position = (*origin, -2)

    # def nbins(self):

    @property
    def image_graphic(self) -> ImageGraphic:
        return self._image_graphic

    @image_graphic.setter
    def image_graphic(self, graphic):
        if not isinstance(graphic, ImageGraphic):
            raise TypeError(
                f"HistogramLUT can only use ImageGraphic types, you have passed: {type(graphic)}"
            )

        self._image_graphic = graphic
