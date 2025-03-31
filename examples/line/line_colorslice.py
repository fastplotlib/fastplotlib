"""
Line Plot Color Slicing
=======================

Example showing color slicing with cosine, sine, sinc lines.
"""

# test_example = true
# sphinx_gallery_pygfx_docs = 'screenshot'

import fastplotlib as fpl
import numpy as np

figure = fpl.Figure(size=(700, 560))

xs = np.linspace(-10, 10, 100)
# sine wave
ys = np.sin(xs)
sine = np.column_stack([xs, ys])

# cosine wave
ys = np.cos(xs)
cosine = np.column_stack([xs, ys])

# sinc function
a = 0.5
ys = np.sinc(xs) * 3
sinc = np.column_stack([xs, ys])

sine_graphic = figure[0, 0].add_line(data=sine, thickness=5, colors="magenta")

# you can also use colormaps for lines!
cosine_graphic = figure[0, 0].add_line(
    data=cosine,
    thickness=12,
    cmap="autumn",
    offset=(
        0,
        3,
        0,
    ),  # places the graphic at a y-axis offset of 3, offsets don't affect data
)

# or a list of colors for each datapoint
colors = ["r"] * 25 + ["purple"] * 25 + ["y"] * 25 + ["b"] * 25
sinc_graphic = figure[0, 0].add_line(
    data=sinc, thickness=5, colors=colors, offset=(0, 6, 0)
)

zeros = np.zeros(xs.size)
zeros_data = np.column_stack([xs, zeros])
zeros_graphic = figure[0, 0].add_line(
    data=zeros_data, thickness=8, colors="w", offset=(0, 10, 0)
)

figure.show()

# indexing of colors
cosine_graphic.colors[:15] = "magenta"
cosine_graphic.colors[90:] = "red"
cosine_graphic.colors[60] = "w"

# more complex indexing, set the blue value directly from an array
cosine_graphic.colors[65:90, 0] = np.linspace(0, 1, 90 - 65)

# additional fancy indexing using numpy
key = np.array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 67, 19])
sinc_graphic.colors[key] = "Red"

# boolean fancy indexing
zeros_graphic.colors[xs < -5] = "green"

# assign colormap to an entire line
sine_graphic.cmap = "seismic"
# or to segments of a line
zeros_graphic.cmap[50:75] = "jet"
zeros_graphic.cmap[75:] = "viridis"


# NOTE: `if __name__ == "__main__"` is NOT how to use fastplotlib interactively
# please see our docs for using fastplotlib interactively in ipython and jupyter
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
