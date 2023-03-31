"""
Simple Plot
============

Example showing the simple plot creation with 512 x 512 pre-saved random image.
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

img = np.asarray(plot.renderer.target.draw())

np.save("../screenshots/simple.npy", img)

if __name__ == "__main__":
    print(__doc__)
