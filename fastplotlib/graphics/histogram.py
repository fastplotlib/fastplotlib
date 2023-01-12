from warnings import warn
from typing import Union, Dict

import numpy as np
import pygfx

from ._base import Graphic


class _HistogramBin(pygfx.Mesh):
    def __int__(self, *args, **kwargs):
        super(_HistogramBin, self).__init__(*args, **kwargs)
        self.bin_center: float = None
        self.frequency: Union[int, float] = None


class HistogramGraphic(Graphic):
    def __init__(
            self,
            data: np.ndarray = None,
            bins: Union[int, str] = 'auto',
            pre_computed: Dict[str, np.ndarray] = None,
            colors: np.ndarray = "w",
            draw_scale_factor: float = 100.0,
            draw_bin_width_scale: float = 1.0,
            **kwargs
    ):
        """
        Create a Histogram Graphic

        Parameters
        ----------
        data: np.ndarray or None, optional
            data to create a histogram from, can be ``None`` if pre-computed values are provided to ``pre_computed``

        bins: int or str, default is "auto", optional
            this is directly just passed to ``numpy.histogram``

        pre_computed: dict in the form {"hist": vals, "bin_edges" : vals}, optional
            pre-computed histogram values

        colors: np.ndarray, optional

        draw_scale_factor: float, default ``100.0``, optional
            scale the drawing of the entire Graphic

        draw_bin_width_scale: float, default ``1.0``
            scale the drawing of the bin widths

        kwargs
            passed to Graphic
        """

        if pre_computed is None:
            self.hist, self.bin_edges = np.histogram(data, bins)
        else:
            if not set(pre_computed.keys()) == {'hist', 'bin_edges'}:
                raise ValueError("argument to `pre_computed` must be a `dict` with keys 'hist' and 'bin_edges'")
            if not all(isinstance(v, np.ndarray) for v in pre_computed.values()):
                raise ValueError("argument to `pre_computed` must be a `dict` where the values are numpy.ndarray")
            self.hist, self.bin_edges = pre_computed["hist"], pre_computed["bin_edges"]

        self.bin_interval = (self.bin_edges[1] - self.bin_edges[0]) / 2
        self.bin_centers = (self.bin_edges + self.bin_interval)[:-1]

        # scale between 0 - draw_scale_factor
        scaled_bin_edges = ((self.bin_edges - self.bin_edges.min()) / (np.ptp(self.bin_edges))) * draw_scale_factor

        bin_interval_scaled = scaled_bin_edges[1] / 2
        # get the centers of the bins from the edges
        x_positions_bins = (scaled_bin_edges + bin_interval_scaled)[:-1].astype(np.float32)

        n_bins = x_positions_bins.shape[0]
        bin_width = (draw_scale_factor / n_bins) * draw_bin_width_scale

        self.hist = self.hist.astype(np.float32)

        for bad_val in [np.nan, np.inf, -np.inf]:
            if bad_val in self.hist:
                warn(f"Problematic value <{bad_val}> found in histogram, replacing with zero")
                self.hist[self.hist == bad_val] = 0

        data = np.vstack([x_positions_bins, self.hist])

        super(HistogramGraphic, self).__init__(data=data, colors=colors, n_colors=n_bins, **kwargs)

        self._world_object: pygfx.Group = pygfx.Group()

        for x_val, y_val, bin_center in zip(x_positions_bins, self.hist, self.bin_centers):
            geometry = pygfx.plane_geometry(
                width=bin_width,
                height=y_val,
            )

            material = pygfx.MeshBasicMaterial()
            hist_bin_graphic = _HistogramBin(geometry, material)
            hist_bin_graphic.position.set(x_val, (y_val) / 2, 0)
            hist_bin_graphic.bin_center = bin_center
            hist_bin_graphic.frequency = y_val

            self.world_object.add(hist_bin_graphic)

