"""
Iris Scatter Plot Color Slicing
===============================

Example showing color slice for scatter plot.
"""

# test_example = true
# sphinx_gallery_pygfx_docs = 'screenshot'

import fastplotlib as fpl
from sklearn import datasets


figure = fpl.Figure(size=(700, 560))

data = datasets.load_iris()["data"]

n_points = 50
colors = ["yellow"] * n_points + ["cyan"] * n_points + ["magenta"] * n_points

scatter = figure[0, 0].add_scatter(
    data=data[:, :-1],
    sizes=6,
    alpha=0.7,
    alpha_mode="weighted_blend",  # blend overlapping dots
    colors=colors,  # use colors from the list of strings
)

figure.show()

scatter.colors[0:75] = "red"
scatter.colors[75:150] = "white"
scatter.colors[::2] = "blue"


if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
