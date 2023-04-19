"""
GridPlot Simple
============
Example showing simple 2x3 GridPlot with pre-saved 512x512 random images.
"""

# test_example = true

from fastplotlib import GridPlot
import numpy as np
from pathlib import Path

from wgpu.gui.offscreen import WgpuCanvas
from pygfx import WgpuRenderer

canvas = WgpuCanvas()
renderer = WgpuRenderer(canvas)

plot = GridPlot(shape=(2,3), canvas=canvas, renderer=renderer)

data_path = Path(__file__).parent.parent.joinpath("data", "random.npy")
data = np.load(data_path)

for subplot in plot:
    subplot.add_image(data=data)

plot.show()

for subplot in plot:
    subplot.center_scene()

img = np.asarray(plot.renderer.target.draw())

if __name__ == "__main__":
    print(__doc__)
