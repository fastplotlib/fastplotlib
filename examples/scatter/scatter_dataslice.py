"""
Scatter Plot
============
Example showing data slice for scatter plot.
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

scatter_graphic.data[0] = np.array([[5, 3, 1.5]])
scatter_graphic.data[1] = np.array([[4.3, 3.2, 1.3]])
scatter_graphic.data[2] = np.array([[5.2, 2.7, 1.7]])

scatter_graphic.data[10:15] = scatter_graphic.data[0:5] + np.array([1, 1, 1])
scatter_graphic.data[50:100:2] = scatter_graphic.data[100:150:2] + np.array([1,1,0])

img = np.asarray(plot.renderer.target.draw())

if __name__ == "__main__":
    print(__doc__)
    