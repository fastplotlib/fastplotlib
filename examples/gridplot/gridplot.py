"""
GridPlot Simple
============
Example showing simple 2x2 GridPlot with Standard images from imageio.
"""

# test_example = true

from fastplotlib import GridPlot
import numpy as np
import imageio.v3 as iio

from wgpu.gui.offscreen import WgpuCanvas
from pygfx import WgpuRenderer

canvas = WgpuCanvas()
renderer = WgpuRenderer(canvas)

plot = GridPlot(shape=(2,2), canvas=canvas, renderer=renderer)

im = iio.imread("imageio:clock.png")
im2 = iio.imread("imageio:astronaut.png")
im3 = iio.imread("imageio:coffee.png")
im4 = iio.imread("imageio:hubble_deep_field.png")

plot[0, 0].add_image(data=im)
plot[0, 1].add_image(data=im2)
plot[1, 0].add_image(data=im3)
plot[1, 1].add_image(data=im4)

plot.show()

for subplot in plot:
    subplot.center_scene()

img = np.asarray(plot.renderer.target.draw())

if __name__ == "__main__":
    print(__doc__)
