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
n_datapoints = 50_000  # number of datapoints per line
xs = np.linspace(0, 1000 * np.pi, n_datapoints)

lines = list()
for i in range(1, 11):
    l = np.column_stack(
        [
            xs,
            np.sin(xs * i)
        ]
    )
    lines.append(l)

# timeseries data of shape [n_lines, n_datapoint, 2]
data = np.stack(lines)

# must define a reference range, this would often be your time dimension and corresponds to your x-dimension
ref = [(0, xs[-1], 0.1, "angle")]

ndw = fpl.NDWidget(ref_ranges=ref, size=(700, 560))

ndw[0, 0].add_nd_timeseries(data, index_mappings=(lambda xval: xs.searchsorted(xval),), x_range_mode="view-range")

ndw.show(maintain_aspect=False)
fpl.loop.run()
