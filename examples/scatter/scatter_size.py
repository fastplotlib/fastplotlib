"""
Scatter Plot Size
=================

Example showing point size change for scatter plot.
"""

# test_example = true
# sphinx_gallery_pygfx_docs = 'screenshot'

import numpy as np
import fastplotlib as fpl

# figure with 2 rows and 3 columns
shape = (2, 1)

# you can give string names for each subplot within the gridplot
names = [["scalar_size"], ["array_size"]]

# Create the grid plot
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
# please see our docs for using fastplotlib interactively in ipython and jupyter
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
