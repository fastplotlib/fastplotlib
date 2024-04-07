"""
Line Plot
============
Example showing color slicing with cosine, sine, sinc lines.
"""

# test_example = true

import fastplotlib as fpl
import numpy as np


fig = fpl.Figure()

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

sine_graphic = fig[0, 0].add_line(data=sine, thickness=5, colors="magenta")

# you can also use colormaps for lines!
cosine_graphic = fig[0, 0].add_line(data=cosine, thickness=12, cmap="autumn")

# or a list of colors for each datapoint
colors = ["r"] * 25 + ["purple"] * 25 + ["y"] * 25 + ["b"] * 25
sinc_graphic = fig[0, 0].add_line(data=sinc, thickness=5, colors=colors)

fig.show()

# indexing of colors
cosine_graphic.colors[:15] = "magenta"
cosine_graphic.colors[90:] = "red"
cosine_graphic.colors[60] = "w"

# indexing to assign colormaps to entire lines or segments
sinc_graphic.cmap[10:50] = "gray"
sine_graphic.cmap = "seismic"

# more complex indexing, set the blue value directly from an array
cosine_graphic.colors[65:90, 0] = np.linspace(0, 1, 90-65)

# additional fancy indexing using numpy
key = np.array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 67, 19])
sinc_graphic.colors[key] = "Red"

key2 = np.array([True, False, True, False, True, True, True, True])
cosine_graphic.colors[key2] = "Green"

fig.canvas.set_logical_size(800, 800)

fig[0, 0].auto_scale()


if __name__ == "__main__":
    print(__doc__)
    fpl.run()
