"""
Line Collection Colors
======================

Example showing how to plot line collections
"""

# test_example = true
# sphinx_gallery_pygfx_docs = 'screenshot'

from itertools import product
import numpy as np
import fastplotlib as fpl


def make_circle(center, radius: float, n_points: int = 75) -> np.ndarray:
    theta = np.linspace(0, 2 * np.pi, n_points)
    xs = radius * np.sin(theta)
    ys = radius * np.cos(theta)

    return np.column_stack([xs, ys]) + center


spatial_dims = (50, 50)

circles = list()
for center in product(range(0, spatial_dims[0], 15), range(0, spatial_dims[1], 15)):
    circles.append(make_circle(center, 5, n_points=75))

pos_xy = np.vstack(circles)

# set line collection colors manually
# this will produce 16 circles so we will define 16 colors
colors = ["blue"] * 4 + ["red"] * 4 + ["yellow"] * 4 + ["w"] * 4

fig = fpl.Figure()

# set canvas variable for sphinx_gallery to properly generate examples
# NOT required for users
canvas = fig.canvas

fig[0, 0].add_line_collection(circles, colors=colors, thickness=10)

fig.show()

fig.canvas.set_logical_size(700, 560)

# NOTE: `if __name__ == "__main__"` is NOT how to use fastplotlib interactively
# please see our docs for using fastplotlib interactively in ipython and jupyter
if __name__ == "__main__":
    print(__doc__)
    fpl.run()
