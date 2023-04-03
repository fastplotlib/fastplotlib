"""
Scatter Plot
============

Example showing scatter plot.
"""

# test_example = true

from fastplotlib import Plot
import numpy as np

from wgpu.gui.offscreen import WgpuCanvas
from pygfx import WgpuRenderer

canvas = WgpuCanvas()
renderer = WgpuRenderer(canvas)

plot = Plot(canvas=canvas, renderer=renderer)

# create a random distribution of 10,000 xyz coordinates
n_points = 10_000

# if you have a good GPU go for 1.5 million points :D
# this is multiplied by 3
n_points = 500_000

# dimensions always have to be [n_points, xyz]
dims = (n_points, 3)

# color each of them separately
colors = ["yellow"] * n_points + ["cyan"] * n_points + ["magenta"] * n_points

data = np.load("../data/scatterclouds.npy")

# use an alpha value since this will be a lot of points
scatter_graphic = plot.add_scatter(data=data, sizes=3, colors=colors, alpha=0.7)

plot.show()

plot.center_scene()

img = np.asarray(plot.renderer.target.draw())

#np.save("../screenshots/scatter.npy", img)

if __name__ == "__main__":
    print(__doc__)

