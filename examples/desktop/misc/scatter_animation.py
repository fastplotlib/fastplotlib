"""
Scatter Animation
=================

Example showing animation with a scatter plot.
"""

# test_example = false
# sphinx_gallery_pygfx_docs = 'animate'

import fastplotlib as fpl
import numpy as np

# create a random distribution of 10,000 xyz coordinates
n_points = 10_000

# dimensions always have to be [n_points, xyz]
dims = (n_points, 3)

clouds_offset = 15

# create some random clouds
normal = np.random.normal(size=dims, scale=5)
# stack the data into a single array
cloud = np.vstack(
    [
        normal - clouds_offset,
        normal,
        normal + clouds_offset,
    ]
)

# color each of them separately
colors = ["yellow"] * n_points + ["cyan"] * n_points + ["magenta"] * n_points

# create plot
fig_scatter = fpl.Figure()
subplot_scatter = fig_scatter[0, 0]
# use an alpha value since this will be a lot of points
scatter_graphic = subplot_scatter.add_scatter(data=cloud, sizes=3, colors=colors, alpha=0.6)


def update_points(subplot):
    # move every point by a small amount
    deltas = np.random.normal(size=scatter_graphic.data().shape, loc=0, scale=0.15)
    scatter_graphic.data = scatter_graphic.data() + deltas


subplot_scatter.add_animations(update_points)

fig_scatter.show()

# set canvas variable for sphinx_gallery to properly generate examples
# NOT required for users
canvas = fig_scatter.canvas

fig_scatter.canvas.set_logical_size(800, 800)

# NOTE: `if __name__ == "__main__"` is NOT how to use fastplotlib interactively
# please see our docs for using fastplotlib interactively in ipython and jupyter
if __name__ == "__main__":
    print(__doc__)
    fpl.run()