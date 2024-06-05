"""
Scatter Colormap
================

Example showing cmap change for scatter plot.
"""

# test_example = true
# sphinx_gallery_pygfx_docs = 'screenshot'

import fastplotlib as fpl
import numpy as np

fig = fpl.Figure()

# create a random distribution of 10,000 xyz coordinates
n_points = 5_000

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
fig = fpl.Figure()

# use an alpha value since this will be a lot of points
fig[0,0].add_scatter(data=cloud, sizes=3, colors=colors, alpha=0.6)

# set canvas variable for sphinx_gallery to properly generate examples
# NOT required for users
canvas = fig.canvas

fig.show()

fig[0,0].graphics[0].cmap = "viridis"

fig.canvas.set_logical_size(700, 560)

fig[0, 0].auto_scale()

# NOTE: `if __name__ == "__main__"` is NOT how to use fastplotlib interactively
# please see our docs for using fastplotlib interactively in ipython and jupyter
if __name__ == "__main__":
    print(__doc__)
    fpl.run()
