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

data_path = Path(__file__).parent.parent.joinpath("data", "scatter.npy")
data = np.load(data_path)

scatter_graphic = plot.add_scatter(data=data, sizes=3, alpha=0.7)

plot.show()

plot.center_scene()

scatter_graphic.data[0] = np.array([[35, -20, -5]])
scatter_graphic.data[1] = np.array([[30, -20, -5]])
scatter_graphic.data[2] = np.array([[40, -20, -5]])
scatter_graphic.data[3] = np.array([[25, -20, -5]])

img = np.asarray(plot.renderer.target.draw())

if __name__ == "__main__":
    print(__doc__)
    