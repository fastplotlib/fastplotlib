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
sine = np.dstack([xs, ys])[0]

# cosine wave
ys = np.cos(xs) - 5
cosine = np.dstack([xs, ys])[0]

# cmap_transform from an array, so the colors on the sine line will be based on the sine y-values
sine_graphic = figure[0, 0].add_line(
    data=sine,
    thickness=10,
    cmap="plasma",
    cmap_transform=sine[:, 1]
)

# qualitative colormaps, useful for cluster labels or other types of categorical labels
labels = [0] * 25 + [5] * 10 + [1] * 35 + [2] * 30
cosine_graphic = figure[0, 0].add_line(
    data=cosine,
    thickness=10,
    cmap="tab10",
    cmap_transform=labels
)

figure.show()


# NOTE: `if __name__ == "__main__"` is NOT how to use fastplotlib interactively
# please see our docs for using fastplotlib interactively in ipython and jupyter
if __name__ == "__main__":
    print(__doc__)
    fpl.run()
