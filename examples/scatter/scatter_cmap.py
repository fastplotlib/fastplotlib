"""
Scatter Plot
============
Example showing cmap change for scatter plot.
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

plot.center_scene()

scatter_graphic.cmap = "viridis"

img = np.asarray(plot.renderer.target.draw())

if __name__ == "__main__":
    print(__doc__)
