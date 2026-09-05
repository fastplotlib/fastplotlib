"""
NDWidget Timeseries cmaps
=========================

NDWidget timeseries example with colormaps and transforms, can be useful for things like ethograms.
"""

# test_example = true
# sphinx_gallery_pygfx_docs = 'screenshot'

import numpy as np
import fastplotlib as fpl
from itertools import cycle

# generate some toy timeseries data
n_datapoints = 100_000  # number of datapoints per line
n_lines = 8

xs = np.linspace(0, 1000 * np.pi, n_datapoints)
ys = np.sin(xs)
data = np.column_stack([xs, ys])
n_data = np.stack([data] * n_lines)

# must define a reference range, this would often be your time dimension and corresponds to your x-dimension
ref = {
    "angle": (0, xs[-1], 0.1),
}

ndw = fpl.NDWidget(ref_ranges=ref, size=(700, 560))

nd_lines = ndw[0, 0].add_nd_timeseries(
    n_data,
    ("n_lines", "angle", "d"),
    ("n_lines", "angle", "d"),
    slider_dim_transforms={
        "angle": xs,
    },
    # some alternating colormaps per-line
    cmap=cycle(["jet", "viridis", "winter"]),
    # a transform from which we map the colormap colors
    # with just a linespace, it means that low x-values get early colors in the colormap
    # high x-values in the FULL data get the later colors in the colormap
    cmap_transform=np.broadcast_to(np.linspace(0, 1, n_datapoints), (n_lines, n_datapoints)),
    x_range_mode="auto",
    display_window=np.pi * 10,
)

ndw.show(maintain_aspect=False)
figure = ndw.figure

# NOTE: fpl.loop.run() should not be used for interactive sessions
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
