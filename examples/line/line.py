"""
Simple Line Plot
================

Example showing cosine, sine, sinc lines.
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

figure[0, 0].axes.grids.xy.visible = True
figure.show()


# NOTE: fpl.loop.run() should not be used for interactive sessions
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()