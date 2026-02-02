"""
Line Plot Data Slicing
======================

Example showing data slicing with cosine, sine, sinc lines.
"""

# test_example = true
# sphinx_gallery_pygfx_docs = 'screenshot'

import fastplotlib as fpl
import numpy as np

figure = fpl.Figure(size=(700, 560))

xs = np.linspace(-10, 10, 100)
# sine wave
ys = np.sin(xs)
sine_data = np.column_stack([xs, ys])

# cosine wave
ys = np.cos(xs) + 5
cosine_data = np.column_stack([xs, ys])

# sinc function
a = 0.5
ys = np.sinc(xs) * 3 + 8
sinc_data = np.column_stack([xs, ys])

sine = figure[0, 0].add_line(data=sine_data, thickness=5, colors="magenta")

# you can also use colormaps for lines!
cosine = figure[0, 0].add_line(data=cosine_data, thickness=12, cmap="autumn")

# or a list of colors for each datapoint
colors = ["r"] * 25 + ["purple"] * 25 + ["y"] * 25 + ["b"] * 25
sinc = figure[0, 0].add_line(data=sinc_data, thickness=5, colors=colors)

figure.show()

cosine.data[10:50:5, :2] = sine_data[10:50:5]
cosine.data[90:, 1] = 7
cosine.data[0] = np.array([[-10, 0, 0]])

# additional fancy indexing with boolean array
bool_key = [True, True, True, False, False] * 20
sinc.data[bool_key, 1] = 7  # y vals to 1


# NOTE: fpl.loop.run() should not be used for interactive sessions
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
