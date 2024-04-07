"""
Simple Heatmap
==============
Example showing how to plot a heatmap
"""

# test_example = true

import fastplotlib as fpl
import numpy as np


fig = fpl.Figure()

xs = np.linspace(0, 1_000, 10_000)

sine = np.sin(xs)
cosine = np.cos(xs)

# alternating sines and cosines
data = np.zeros((10_000, 10_000), dtype=np.float32)
data[::2] = sine
data[1::2] = cosine

# plot the image data
heatmap_graphic = fig[0, 0].add_heatmap(data=data, name="heatmap")

fig.show()

fig.canvas.set_logical_size(1500, 1500)

fig[0, 0].auto_scale()

if __name__ == "__main__":
    print(__doc__)
    fpl.run()
