"""
Heatmap change cmap
===================
Change the cmap of a heatmap
"""

# test_example = true
# sphinx_gallery_pygfx_docs = 'screenshot'

import fastplotlib as fpl
import numpy as np
from wgpu.gui.offscreen import WgpuCanvas

canvas = WgpuCanvas()

fig = fpl.Figure(canvas=canvas)

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

heatmap_graphic.cmap = "viridis"

if __name__ == "__main__":
    print(__doc__)
    fpl.run()
