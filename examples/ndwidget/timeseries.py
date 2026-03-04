"""
NDWidget Timeseries
===================

NDWidget timeseries example
"""

# test_example = true
# sphinx_gallery_pygfx_docs = 'screenshot'

import numpy as np
import fastplotlib as fpl

# generate some toy timeseries data
n_datapoints = 100_000  # number of datapoints per line
n_freqs = 20  # number of frequencies
n_ampls = 15  # number of amplitudes
n_lines = 8

xs = np.linspace(0, 1000 * np.pi, n_datapoints)

data = np.zeros(shape=(n_freqs, n_ampls, n_lines, n_datapoints, 2), dtype=np.float32)

for freq in range(data.shape[0]):
    for ampl in range(data.shape[1]):
        ys = np.sin(xs * (freq + 1)) * (ampl + 1) + np.random.normal(
            0, 0.1, size=n_datapoints
        )
        line = np.column_stack([xs, ys])
        data[freq, ampl] = np.stack([line] * n_lines)


# must define a reference range, this would often be your time dimension and corresponds to your x-dimension
ref = {
    "freq": (1, n_freqs + 1, 1),
    "ampl": (1, n_ampls + 1, 1),
    "angle": (0, xs[-1], 0.1),
}

ndw = fpl.NDWidget(ref_ranges=ref, size=(700, 560))

nd_lines = ndw[0, 0].add_nd_timeseries(
    data,
    ("freq", "ampl", "n_lines", "angle", "d"),
    ("n_lines", "angle", "d"),
    index_mappings={
        "angle": xs,
        "ampl": lambda x: int(x + 1),
        "freq": lambda x: int(x + 1),
    },
    x_range_mode="view-range",
)

nd_lines.graphic.cmap = "tab10"

subplot = ndw.figure[0, 0]
subplot.controller.add_camera(subplot.camera, include_state={"x", "width"})

ndw.show(maintain_aspect=False)
fpl.loop.run()
