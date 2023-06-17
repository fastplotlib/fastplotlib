"""
Line Plot
============
Example showing cosine, sine, sinc lines.
"""

# test_example = true

from fastplotlib import Plot, run
import numpy as np


plot = Plot()

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

# cmap_values from an array, so the colors on the sine line will be based on the sine y-values
sine_graphic = plot.add_line(data=sine, thickness=10, cmap="plasma", cmap_values=sine[:, 1])

# qualitative colormaps, useful for cluster labels for example
cmap_values = [0] * 25 + [5] * 25 + [1] * 25 + [2] * 25
cosine_graphic = plot.add_line(data=cosine, thickness=10, cmap="tab10", cmap_values=cmap_values)

plot.show()

plot.canvas.set_logical_size(800, 800)
