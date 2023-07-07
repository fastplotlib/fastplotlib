"""
Line Plot Cmap
==============
Example showing cosine, sine, sinc lines.
"""

# test_example = true
# sphinx_gallery_fastplotlib_render = True

import fastplotlib as fpl
import numpy as np


plot = fpl.Plot()
# to force a specific framework such as glfw:
# plot = fpl.Plot(canvas="glfw")

xs = np.linspace(-10, 10, 100)
# sine wave
ys = np.sin(xs)
sine = np.dstack([xs, ys])[0]

# cosine wave
ys = np.cos(xs) - 5
cosine = np.dstack([xs, ys])[0]

# cmap_values from an array, so the colors on the sine line will be based on the sine y-values
sine_graphic = plot.add_line(
    data=sine,
    thickness=10,
    cmap="plasma",
    cmap_values=sine[:, 1]
)

# qualitative colormaps, useful for cluster labels or other types of categorical labels
cmap_values = [0] * 25 + [5] * 10 + [1] * 35 + [2] * 30
cosine_graphic = plot.add_line(
    data=cosine,
    thickness=10,
    cmap="tab10",
    cmap_values=cmap_values
)

plot.show()

plot.canvas.set_logical_size(800, 800)

if __name__ == "__main__":
    print(__doc__)
    fpl.run()
