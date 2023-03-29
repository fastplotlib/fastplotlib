"""
Simple Plot
============

Example showing the simple plot creation with 512 x 512 2D RGB image.
"""
# test_example = true

from fastplotlib import Plot
import numpy as np
import imageio.v3 as iio

from wgpu.gui.offscreen import WgpuCanvas
from pygfx import WgpuRenderer

canvas = WgpuCanvas()
renderer = WgpuRenderer(canvas)

plot = Plot(canvas=canvas, renderer=renderer)

im = iio.imread("imageio:astronaut.png")

# plot the image data
image_graphic = plot.add_image(data=im, name="iio astronaut")

plot.show()

img = np.asarray(plot.renderer.target.draw())

if __name__ == "__main__":
    print(__doc__)
