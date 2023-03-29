"""
Line Plot
============

Example showing data slicing with cosine, sine, sinc lines.
"""

# test_example = true

from fastplotlib import Plot
import numpy as np

from wgpu.gui.offscreen import WgpuCanvas
from pygfx import WgpuRenderer

canvas = WgpuCanvas()
renderer = WgpuRenderer(canvas)

plot = Plot(canvas=canvas, renderer=renderer)

# linspace, create 100 evenly spaced x values from -10 to 10
xs = np.linspace(-10, 10, 100)
# sine wave
ys = np.sin(xs)
sine = np.dstack([xs, ys])[0]

# cosine wave
ys = np.cos(xs) + 5
cosine = np.dstack([xs, ys])[0]

# sinc function
a = 0.5
ys = np.sinc(xs) * 3 + 8
sinc = np.dstack([xs, ys])[0]

# plot sine wave, use a single color
sine_graphic = plot.add_line(data=sine, thickness=5, colors="magenta")

# you can also use colormaps for lines!
cosine_graphic = plot.add_line(data=cosine, thickness=12, cmap="autumn")

# or a list of colors for each datapoint
colors = ["r"] * 25 + ["purple"] * 25 + ["y"] * 25 + ["b"] * 25
sinc_graphic = plot.add_line(data=sinc, thickness=5, colors=colors)

plot.show()

cosine_graphic.data[10:50:5, :2] = sine[10:50:5]
cosine_graphic.data[90:, 1] = 7
cosine_graphic.data[0] = np.array([[-10, 0, 0]])

plot.center_scene()

img = np.asarray(plot.renderer.target.draw())

if __name__ == "__main__":
    print(__doc__)
