"""
Scatter Plot Size
=================

Example that shows how to set scatter sizes in two different ways.

One subplot uses a single scaler value for every point, and another subplot uses an array that defines the size for
each individual scatter point.
"""

# test_example = true
# sphinx_gallery_pygfx_docs = 'screenshot'

import numpy as np
import fastplotlib as fpl

# figure with 2 rows and 3 columns
shape = (2, 1)

# you can give string names for each subplot within the figure
names = [["scalar_size"], ["array_size"]]

# Create the figure
figure = fpl.Figure(shape=shape, names=names, size=(700, 560))

# get y_values using sin function
angles = np.arange(0, 20 * np.pi + 0.001, np.pi / 20)
y_values = 30 * np.sin(angles)  # 1 thousand points
x_values = np.array([x for x in range(len(y_values))], dtype=np.float32)

data = np.column_stack([x_values, y_values])

figure["scalar_size"].add_scatter(
    data=data, sizes=5, colors="blue"
)  # add a set of scalar sizes

non_scalar_sizes = np.abs((y_values / np.pi))  # ensure minimum size of 5
figure["array_size"].add_scatter(data=data, sizes=non_scalar_sizes, colors="red")

for graph in figure:
    graph.auto_scale(maintain_aspect=True)

figure.show()


# NOTE: `if __name__ == "__main__"` is NOT how to use fastplotlib interactively
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
