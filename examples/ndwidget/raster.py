"""
NDWidget Spike Raster
=====================

Browse a spike raster with an ``NDWidget``. The array is ``[raster, spike, xy]``, where the value dim holds the
spike time in seconds and the raster index of each spike, so each of the 20 rasters is a separate scatter in the
collection.

The datapoints dim is time, so the one slider scrubs along it and ``display_window`` sets how many seconds of
spikes are rendered at a time. That window is what keeps a long recording viewable, only the spikes in view are
read and uploaded.

``x_range_mode="auto"`` couples the camera to that window in both directions: the x-range follows the slider,
and panning or zooming sets the display window to the new width and the index to the new center. The linear
selector marks the current time.
"""

# test_example = false
# sphinx_gallery_pygfx_docs = 'animate 6s 20fps'

import numpy as np
import fastplotlib as fpl

n_rasters = 10
n_spikes = 2_000  # spikes per raster
duration = 120.0  # seconds

rng = np.random.default_rng(0)

# a shared sequence of population events, each raster fires near every event with its own jitter
events = np.sort(rng.uniform(0, duration, n_spikes))

# [raster, spike, xy], the value dim holds the spike time in seconds and the raster index
data = np.empty((n_rasters, n_spikes, 2), dtype=np.float32)
data[:, :, 0] = events + rng.normal(0, 0.05, (n_rasters, n_spikes))
data[:, :, 1] = np.arange(n_rasters)[:, None]

data2 = np.empty((n_rasters, n_spikes, 2), dtype=np.float32)
data2[:, :, 0] = events + rng.normal(0, 0.05, (n_rasters, n_spikes))
data2[:, :, 1] = np.arange(n_rasters)[:, None]


# reference space is seconds, one step per 60 Hz frame
ranges = {"time": (0, duration, 1 / 60)}

ndw = fpl.NDWidget(ranges=ranges, size=(700, 700), shape=(2, 1))

ndw[0, 0].add_nd_timeseries(
    data,
    dims=("raster", "time", "xy"),
    display_dims=("raster", "time", "xy"),
    graphic_type=fpl.ScatterCollection,
    slider_maps={"time": events},  # seconds -> index into the spike list
    display_window=5.0,  # seconds of spikes to render
    max_display_datapoints=1_000_000,  # spikes are cheap points, never decimate them
    x_range_mode="auto",
    cmap="viridis",  # one color per raster
    sizes=4,
    name="raster",
)

ndw[1, 0].add_nd_timeseries(
    data2,
    dims=("raster", "time", "xy"),
    display_dims=("raster", "time", "xy"),
    graphic_type=fpl.ScatterCollection,
    slider_maps={"time": events},  # seconds -> index into the spike list
    display_window=5.0,  # seconds of spikes to render
    max_display_datapoints=1_000_000,  # spikes are cheap points, never decimate them
    x_range_mode="auto",
    cmap="viridis",  # one color per raster
    sizes=4,
    name="raster",
)

subplot = ndw.figure[0, 0]

ndw.show(maintain_aspect=False)

figure = ndw.figure


# NOTE: fpl.loop.run() should not be used for interactive sessions
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
