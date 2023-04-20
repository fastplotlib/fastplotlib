"""
Simple Plot
============
Example showing simple plot creation and subsequent cmap change with 512 x 512 pre-saved random image.
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

im = iio.imread("imageio:clock.png")

# plot the image data
image_graphic = plot.add_image(data=im, name="random-image")

plot.show()

image_graphic.cmap = "viridis"

img = np.asarray(plot.renderer.target.draw())

if __name__ == "__main__":
    print(__doc__)
