"""
GridPlot
============

Example showing cmap changes in simple 2x3 GridPlot with pre-saved 512x512 random images.
"""

# test_example = true

from fastplotlib import GridPlot
import numpy as np

from wgpu.gui.offscreen import WgpuCanvas
from pygfx import WgpuRenderer

canvas = WgpuCanvas()
renderer = WgpuRenderer(canvas)

plot = GridPlot(shape=(2,3), canvas=canvas, renderer=renderer)

data = np.load("../data/random.npy")

for subplot in plot:
    subplot.add_image(data=data)

plot.show()

for subplot in plot:
    subplot.center_scene()

plot[0, 0].graphics[0].cmap = "gray"
plot[0, 2].graphics[0].cmap = "plasma"
plot[1, 2].graphics[0].cmap = "viridis"

img = np.asarray(plot.renderer.target.draw())

#np.save('../screenshots/gridplot_cmap.npy', img)

if __name__ == "__main__":
    print(__doc__)