"""
Scatter Plot
============
Example showing data slice for scatter plot.
"""

# test_example = true

import fastplotlib as fpl
import numpy as np
from pathlib import Path


plot = fpl.Plot()
# to force a specific framework such as glfw:
# plot = fpl.Plot(canvas="glfw")

data_path = Path(__file__).parent.parent.joinpath("data", "iris.npy")
data = np.load(data_path)

n_points = 50
colors = ["yellow"] * n_points + ["cyan"] * n_points + ["magenta"] * n_points

scatter_graphic = plot.add_scatter(data=data[:, :-1], sizes=6, alpha=0.7, colors=colors)

plot.show()

plot.canvas.set_logical_size(800, 800)

plot.auto_scale()

scatter_graphic.data[0] = np.array([[5, 3, 1.5]])
scatter_graphic.data[1] = np.array([[4.3, 3.2, 1.3]])
scatter_graphic.data[2] = np.array([[5.2, 2.7, 1.7]])

scatter_graphic.data[10:15] = scatter_graphic.data[0:5] + np.array([1, 1, 1])
scatter_graphic.data[50:100:2] = scatter_graphic.data[100:150:2] + np.array([1,1,0])


if __name__ == "__main__":
    print(__doc__)
    fpl.run()
