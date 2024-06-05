"""
Heatmap change cmap
===================
Change the cmap of a heatmap
"""

# test_example = true
# sphinx_gallery_pygfx_docs = 'screenshot'

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

# set canvas variable for sphinx_gallery to properly generate examples
# NOT required for users
canvas = fig.canvas

fig.canvas.set_logical_size(1500, 1500)

fig[0, 0].auto_scale()

heatmap_graphic.cmap = "viridis"

# NOTE: `if __name__ == "__main__"` is NOT how to use fastplotlib interactively
# please see our docs for using fastplotlib interactively in ipython and jupyter
if __name__ == "__main__":
    print(__doc__)
    fpl.run()
