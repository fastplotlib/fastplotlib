"""
Line Plot
============

Example showing cosine, sine, sinc lines.
"""

# test_example = true

from fastplotlib import Plot
import numpy as np

from wgpu.gui.offscreen import WgpuCanvas
from pygfx import WgpuRenderer

canvas = WgpuCanvas()
renderer = WgpuRenderer(canvas)

plot = Plot(canvas=canvas, renderer=renderer)

sine = np.load("../data/sine.npy")
cosine = np.load("../data/cosine.npy")
sinc = np.load("../data/sinc.npy")

# plot sine wave, use a single color
sine_graphic = plot.add_line(data=sine, thickness=5, colors="magenta")

# you can also use colormaps for lines!
cosine_graphic = plot.add_line(data=cosine, thickness=12, cmap="autumn")

# or a list of colors for each datapoint
colors = ["r"] * 25 + ["purple"] * 25 + ["y"] * 25 + ["b"] * 25
sinc_graphic = plot.add_line(data=sinc, thickness=5, colors=colors)

plot.show()

plot.center_scene()

img = np.asarray(plot.renderer.target.draw())

#np.save('../screenshots/line.npy', img)

if __name__ == "__main__":
    print(__doc__)
