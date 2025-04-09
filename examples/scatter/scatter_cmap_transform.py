"""
Scatter custom cmap
===================

Use a cmap_transform to define how to map colors to scatter points from a custom defined cmap.
This is also valid for line graphics.

This is identical to the scatter.py example but the cmap_transform is sometimes a better way to define the colors.
It may also be more performant if millions of strings for each point do not have to be parsed into colors.
"""

# test_example = true
# sphinx_gallery_pygfx_docs = 'screenshot'

import fastplotlib as fpl
import numpy as np

figure = fpl.Figure(size=(700, 560))

# create a random distribution of 15,000 xyz coordinates
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

# we have 3 clouds, create a 1D array where the value indicates cloud membership
# this will be used to map the colors from the cmap onto the corresponding point
cmap_transform = np.empty(cloud.shape[0])

# first cloud is given a value of 0
cmap_transform[:n_points] = 0

# second cloud is given a value of 1
cmap_transform[n_points: 2 * n_points] = 1

# 3rd cloud given a value of 2
cmap_transform[2 * n_points:] = 2


figure[0, 0].add_scatter(
    data=cloud,
    sizes=3,
    cmap=["green", "purple", "blue"],  # custom cmap
    cmap_transform=cmap_transform,  # each element of the cmap_transform maps to the corresponding datapoint
    alpha=0.6
)

figure.show()


# NOTE: `if __name__ == "__main__"` is NOT how to use fastplotlib interactively
# please see our docs for using fastplotlib interactively in ipython and jupyter
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
