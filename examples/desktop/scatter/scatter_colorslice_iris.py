"""
Iris Scatter Plot Color Slicing
===============================

Example showing color slice for scatter plot.
"""

# test_example = true
# sphinx_gallery_pygfx_docs = 'screenshot'

import fastplotlib as fpl
from sklearn import datasets


figure = fpl.Figure()

data = datasets.load_iris()["data"]

n_points = 50
colors = ["yellow"] * n_points + ["cyan"] * n_points + ["magenta"] * n_points

scatter_graphic = figure[0, 0].add_scatter(
    data=data[:, :-1],
    sizes=6,
    alpha=0.7,
    colors=colors  # use colors from the list of strings
)

figure.show()

figure.canvas.set_logical_size(700, 560)

figure[0, 0].auto_scale()

scatter_graphic.colors[0:75] = "red"
scatter_graphic.colors[75:150] = "white"
scatter_graphic.colors[::2] = "blue"


if __name__ == "__main__":
    print(__doc__)
    fpl.run()
