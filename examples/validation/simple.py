# test_example = true

from fastplotlib import Plot
import numpy as np

from wgpu.gui.offscreen import WgpuCanvas
from pygfx import Scene, WgpuRenderer

canvas = WgpuCanvas()
renderer = WgpuRenderer(canvas)

plot = Plot(canvas=canvas, renderer=renderer)

# make some random 2D image data
data = np.random.rand(512, 512)

# plot the image data
image_graphic = plot.add_image(data=data, name="random-image")

plot.show()

img = np.asarray(plot.renderer.target.draw())

np.save("/home/caitlin/bah.npy", img)


