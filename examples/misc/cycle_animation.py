"""
Scatter Animation Colors
========================

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


i = 0.05
def cycle_colors(subplot):
    global i
    # cycle the red values
    scatter_graphic.colors[n_points * 2:, 0] = np.abs(np.sin(i))
    scatter_graphic.colors[n_points * 2:, 1] = np.abs(np.sin(i + (np.pi / 4)))
    scatter_graphic.colors[n_points * 2:, 2] = np.abs(np.cos(i))
    i += 0.05

subplot_scatter.add_animations(cycle_colors)

figure.show()


# NOTE: `if __name__ == "__main__"` is NOT how to use fastplotlib interactively
# please see our docs for using fastplotlib interactively in ipython and jupyter
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
