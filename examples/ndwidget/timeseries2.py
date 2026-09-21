"""
NDWidget Timeseries cmaps
=========================

NDWidget timeseries example with colormaps and transforms, can be useful for things like ethograms.
"""

# test_example = true
# sphinx_gallery_pygfx_docs = 'animate 6s 20fps'

import numpy as np
import fastplotlib as fpl

# generate some toy timeseries data
n_datapoints = 100_000  # number of datapoints per line
n_lines = 8

xs = np.linspace(0, 1000 * np.pi, n_datapoints)
ys = np.random.rand(n_datapoints)
data = np.column_stack([xs, ys])
n_data = np.stack([data] * n_lines)
n_data2 = np.stack([data] * n_lines)
n_data3 = np.stack([data] * n_lines)

n_data2[..., 1] *= 2
n_data3[..., 1] *= 0.5

# must define a reference range, this would often be your time dimension and corresponds to your x-dimension
ref = {
    "angle": (0, xs[-1], 0.1),
}

ndw = fpl.NDWidget(ranges=ref, size=(700, 560), shape=(3, 1))

nd_lines = ndw[0, 0].add_nd_timeseries(
    n_data,
    ("n_lines", "angle", "d"),
    ("n_lines", "angle", "d"),
    slider_maps={
        "angle": xs,
    },
    x_range_mode="auto",
    display_window=np.pi * 10,
)

nd_lines2 = ndw[1, 0].add_nd_timeseries(
    n_data2,
    ("n_lines", "angle", "d"),
    ("n_lines", "angle", "d"),
    slider_maps={
        "angle": xs,
    },
    x_range_mode="auto",
    display_window=np.pi * 10,
)

nd_lines3 = ndw[2, 0].add_nd_timeseries(
    n_data3,
    ("n_lines", "angle", "d"),
    ("n_lines", "angle", "d"),
    slider_maps={
        "angle": xs,
    },
    x_range_mode="auto",
    display_window=np.pi * 10,
)

ndw.show(maintain_aspect=False)
figure = ndw.figure

subplot = ndw.figure[0, 0]
subplot2 = ndw.figure[1, 0]
subplot3 = ndw.figure[2, 0]

subplot.controller.add_camera(subplot2.camera, include_state={"x", "width"})
subplot.controller.add_camera(subplot3.camera, include_state={"x", "width"})

subplot2.controller.add_camera(subplot.camera, include_state={"x", "width"})
subplot2.controller.add_camera(subplot3.camera, include_state={"x", "width"})

subplot3.controller.add_camera(subplot2.camera, include_state={"x", "width"})
subplot3.controller.add_camera(subplot.camera, include_state={"x", "width"})

# NOTE: fpl.loop.run() should not be used for interactive sessions
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
