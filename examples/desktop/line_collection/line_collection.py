"""
Line Plot
============
Example showing how to plot line collections
"""

# test_example = true

from itertools import product
import numpy as np
import fastplotlib as fpl


def make_circle(center, radius: float, n_points: int = 75) -> np.ndarray:
    theta = np.linspace(0, 2 * np.pi, n_points)
    xs = radius * np.sin(theta)
    ys = radius * np.cos(theta)

    return np.column_stack([xs, ys]) + center


spatial_dims = (100, 100)

circles = list()
for center in product(range(0, spatial_dims[0], 15), range(0, spatial_dims[1], 15)):
    circles.append(make_circle(center, 5, n_points=75))

pos_xy = np.vstack(circles)

fig = fpl.Figure()

fig[0, 0].add_line_collection(circles, cmap="jet", thickness=5)

fig.show()

fig.canvas.set_logical_size(800, 800)

if __name__ == "__main__":
    print(__doc__)
    fpl.run()
