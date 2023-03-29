"""
Simple Plot
============

Example showing cmap change with 512 x 512 pre-saved random image.
"""
# test_example = true

from fastplotlib import Plot
import numpy as np

from wgpu.gui.offscreen import WgpuCanvas
from pygfx import WgpuRenderer

canvas = WgpuCanvas()
renderer = WgpuRenderer(canvas)

plot = Plot(canvas=canvas, renderer=renderer)

data = np.load("../data/2Drand.npy")

# plot the image data
image_graphic = plot.add_image(data=data, name="random-image")

plot.show()

image_graphic.cmap = "viridis"

img = np.asarray(plot.renderer.target.draw())

np.save("/home/caitlin/repos/fastplotlib/examples/screenshots/2Dcmap.npy", img)

if __name__ == "__main__":
    print(__doc__)