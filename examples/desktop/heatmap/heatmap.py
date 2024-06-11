"""
Simple Heatmap
==============
Example showing how to plot a heatmap
"""

# test_example = true

import fastplotlib as fpl
import numpy as np


fig = fpl.Figure()

xs = np.linspace(0, 1_000, 10_000, dtype=np.float32)

sine = np.sin(np.sqrt(xs))

data = np.vstack([sine * i for i in range(20_000)])

# plot the image data
img = fig[0, 0].add_image(data=data, name="heatmap")

fig.show()

fig.canvas.set_logical_size(1500, 1500)

fig[0, 0].auto_scale()

if __name__ == "__main__":
    print(__doc__)
    fpl.run()
