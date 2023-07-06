"""
Line Plot
=========
Example showing cosine, sine, sinc lines.
"""

# test_example = true

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
ys = np.cos(xs) + 5
cosine = np.dstack([xs, ys])[0]

# sinc function
a = 0.5
ys = np.sinc(xs) * 3 + 8
sinc = np.dstack([xs, ys])[0]

sine_graphic = plot.add_line(data=sine, thickness=5, colors="magenta")

# you can also use colormaps for lines!
cosine_graphic = plot.add_line(data=cosine, thickness=12, cmap="autumn")

# or a list of colors for each datapoint
colors = ["r"] * 25 + ["purple"] * 25 + ["y"] * 25 + ["b"] * 25
sinc_graphic = plot.add_line(data=sinc, thickness=5, colors=colors)

plot.show()

plot.canvas.set_logical_size(800, 800)

plot.auto_scale()


if __name__ == "__main__":
    print(__doc__)
    fpl.run()
