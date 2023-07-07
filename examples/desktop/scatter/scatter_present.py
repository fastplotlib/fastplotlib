"""
Scatter Plot Present
====================
Example showing present feature for scatter plot.
"""

# test_example = true
# sphinx_gallery_fastplotlib_render = True

import fastplotlib as fpl
import numpy as np
from pathlib import Path


plot = fpl.Plot()

data_path = Path(__file__).parent.parent.joinpath("data", "iris.npy")
data = np.load(data_path)

n_points = 50
colors = ["yellow"] * n_points + ["cyan"] * n_points + ["magenta"] * n_points

scatter_graphic = plot.add_scatter(data=data[:, :-1], sizes=6, alpha=0.7, colors=colors)

colors = ["red"] * n_points + ["white"] * n_points + ["blue"] * n_points
scatter_graphic2 = plot.add_scatter(data=data[:, 1:], sizes=6, alpha=0.7, colors=colors)

plot.show()

plot.canvas.set_logical_size(800, 800)

plot.auto_scale()

scatter_graphic.present = False

img = np.asarray(plot.renderer.target.draw())

if __name__ == "__main__":
    print(__doc__)
    fpl.run()
