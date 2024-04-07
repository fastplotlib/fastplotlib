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


spatial_dims = (50, 50)

circles = list()
for center in product(range(0, spatial_dims[0], 15), range(0, spatial_dims[1], 15)):
    circles.append(make_circle(center, 5, n_points=75))

pos_xy = np.vstack(circles)

# this makes 16 circles, so we can create 16 cmap values, so it will use these values to set the
# color of the line based by using the cmap as a LUT with the corresponding cmap_value

# highest values, lowest values, mid-high values, mid values
cmap_values = [10] * 4 + [0] * 4 + [7] * 4 + [5] * 4

fig = fpl.Figure()

fig[0, 0].add_line_collection(
    circles,
    cmap="bwr",
    cmap_values=cmap_values,
    thickness=10
)

fig.show()

fig.canvas.set_logical_size(800, 800)

if __name__ == "__main__":
    print(__doc__)
    fpl.run()
