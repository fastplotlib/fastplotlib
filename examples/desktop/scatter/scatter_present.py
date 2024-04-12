"""
Scatter Plot
============
Example showing present feature for scatter plot.
"""

# test_example = true

import fastplotlib as fpl
import numpy as np
from pathlib import Path


fig = fpl.Figure()

data_path = Path(__file__).parent.parent.joinpath("data", "iris.npy")
data = np.load(data_path)

n_points = 50
colors = ["yellow"] * n_points + ["cyan"] * n_points + ["magenta"] * n_points

scatter_graphic = fig[0, 0].add_scatter(data=data[:, :-1], sizes=6, alpha=0.7, colors=colors)

colors = ["red"] * n_points + ["white"] * n_points + ["blue"] * n_points
scatter_graphic2 = fig[0, 0].add_scatter(data=data[:, 1:], sizes=6, alpha=0.7, colors=colors)

fig.show()

fig.canvas.set_logical_size(800, 800)

fig[0, 0].auto_scale()

scatter_graphic.present = False


if __name__ == "__main__":
    print(__doc__)
    fpl.run()
