"""
Scatter Animation Data
======================

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
figure = fpl.Figure(size=(700, 560))
subplot_scatter = figure[0, 0]
# use an alpha value since this will be a lot of points
scatter_graphic = subplot_scatter.add_scatter(data=cloud, sizes=3, colors=colors, alpha=0.6)


def update_points(subplot):
    # move every point by a small amount
    deltas = np.random.normal(size=scatter_graphic.data.value.shape, loc=0, scale=0.15)
    scatter_graphic.data = scatter_graphic.data.value + deltas


subplot_scatter.add_animations(update_points)

figure.show()


# NOTE: fpl.loop.run() should not be used for interactive sessions
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
