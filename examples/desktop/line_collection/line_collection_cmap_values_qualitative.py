"""
Line collections qualitative cmaps
==================================
Example showing a line collection with a qualitative cmap
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

# qualitative colormap used for mapping 16 cmap values for each line
# for example, these could be cluster labels
cmap_values = [
    0, 1, 1, 2,
    0, 0, 1, 1,
    2, 2, 3, 3,
    1, 1, 1, 5
]

fig = fpl.Figure()

fig[0, 0].add_line_collection(
    circles,
    cmap="tab10",
    cmap_transform=cmap_values,
    thickness=10
)

fig.show()

fig.canvas.set_logical_size(800, 800)

if __name__ == "__main__":
    print(__doc__)
    fpl.run()
