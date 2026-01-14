"""
Line Plot Colormap
==================

Example showing basic colormapping with lines
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
ys = np.cos(xs) - 5
cosine_data = np.column_stack([xs, ys])

# cmap_transform from an array, so the colors on the sine line will be based on the sine y-values
sine = figure[0, 0].add_line(
    data=sine_data,
    thickness=10,
    cmap="plasma",
    cmap_transform=sine_data[:, 1],
    uniform_color=False,
)

# qualitative colormaps, useful for cluster labels or other types of categorical labels
labels = [0] * 25 + [5] * 10 + [1] * 35 + [2] * 30
cosine = figure[0, 0].add_line(
    data=cosine_data,
    thickness=10,
    cmap="tab10",
    cmap_transform=labels,
    uniform_color=False,
)

figure.show()


# NOTE: fpl.loop.run() should not be used for interactive sessions
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
