"""
Simple Plot
============
Example showing the simple plot creation followed by changing the vmin/vmax with Standard imageio image.
"""
# test_example = true

from fastplotlib import Plot
import numpy as np
from pathlib import Path
import imageio.v3 as iio

from wgpu.gui.offscreen import WgpuCanvas
from pygfx import WgpuRenderer

canvas = WgpuCanvas()
renderer = WgpuRenderer(canvas)

plot = Plot(canvas=canvas, renderer=renderer)

data = iio.imread("imageio:astronaut.png")

# plot the image data
image_graphic = plot.add_image(data=data, name="iio astronaut")

plot.show()

plot.canvas.set_logical_size(800, 800)

plot.auto_scale()

image_graphic.cmap.vmin = 0.5
image_graphic.cmap.vmax = 0.75

img = np.asarray(plot.renderer.target.draw())

if __name__ == "__main__":
    print(__doc__)
