"""
Scatter Plot
============
Example showing color slice for scatter plot.
"""

# test_example = true

from fastplotlib import Plot
import numpy as np
from pathlib import Path

from wgpu.gui.offscreen import WgpuCanvas
from pygfx import WgpuRenderer

canvas = WgpuCanvas()
renderer = WgpuRenderer(canvas)

plot = Plot(canvas=canvas, renderer=renderer)

data_path = Path(__file__).parent.parent.joinpath("data", "iris.npy")
data = np.load(data_path)

n_points = 50
colors = ["yellow"] * n_points + ["cyan"] * n_points + ["magenta"] * n_points

scatter_graphic = plot.add_scatter(data=data[:, :-1], sizes=6, alpha=0.7, colors=colors)

plot.show()

plot.canvas.set_logical_size(800, 800)

plot.auto_scale()

scatter_graphic.colors[0:75] = "red"
scatter_graphic.colors[75:150] = "white"
scatter_graphic.colors[::2] = "blue"

img = np.asarray(plot.renderer.target.draw())

if __name__ == "__main__":
    print(__doc__)
