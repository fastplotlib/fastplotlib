"""
Lines more colormapping
=======================

Example showing more on colormapping with lines
"""

# test_example = true
# sphinx_gallery_pygfx_docs = 'screenshot'

import numpy as np
import fastplotlib as fpl

xs = np.linspace(0, 10 * np.pi, 100)
# sine wave
ys = np.sin(xs)
sine = np.column_stack([xs, ys])

# cosine wave
ys = np.cos(xs)
cosine = np.column_stack([xs, ys])

figure = fpl.Figure(size=(700, 560))

# basic white line
line0 = figure[0, 0].add_line(sine, thickness=10)

# set colormap along line datapoints, use an offset to place it above the previous line
line1 = figure[0, 0].add_line(sine, thickness=10, cmap="jet", offset=(0, 2, 0))

# set colormap by mapping data using a transform
# here we map the color using the y-values of the sine data
# i.e., the color is a function of sine(x)
line2 = figure[0, 0].add_line(sine, thickness=10, cmap="jet", cmap_transform=sine[:, 1], offset=(0, 4, 0))

# make a line and change the cmap afterward, here we are using the cosine instead fot the transform
line3 = figure[0, 0].add_line(sine, thickness=10, cmap="jet", cmap_transform=cosine[:, 1], offset=(0, 6, 0))
# change the cmap
line3.cmap = "bwr"

# use quantitative colormaps with categorical cmap_transforms
labels = [0] * 25 + [1] * 5 + [2] * 50 + [3] * 20
line4 = figure[0, 0].add_line(sine, thickness=10, cmap="tab10", cmap_transform=labels, offset=(0, 8, 0))

# some text labels
for i in range(5):
    figure[0, 0].add_text(f"line{i}", font_size=20, offset=(1, (i * 2) + 1.5, 0))

figure.show(maintain_aspect=False)


# NOTE: `if __name__ == "__main__"` is NOT how to use fastplotlib interactively
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
