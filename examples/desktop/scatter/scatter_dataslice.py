"""
Scatter Plot Data Slicing
=========================

Example showing data slice for scatter plot.
"""

# test_example = true
# sphinx_gallery_pygfx_docs = 'screenshot'

import fastplotlib as fpl
import numpy as np


fig = fpl.Figure()

# create a gaussian cloud of 5_000 points
n_points = 1_000

mean = [0, 0]  # mean of the Gaussian distribution
covariance = [[1, 0], [0, 1]]  # covariance matrix

gaussian_cloud = np.random.multivariate_normal(mean, covariance, n_points)
gaussian_cloud2 = np.random.multivariate_normal(mean, covariance, n_points)

# create plot
fig = fpl.Figure()

# use an alpha value since this will be a lot of points
scatter1 = fig[0,0].add_scatter(data=gaussian_cloud, sizes=3)
scatter2 = fig[0,0].add_scatter(data=gaussian_cloud2, colors="r", sizes=3)

# set canvas variable for sphinx_gallery to properly generate examples
# NOT required for users
canvas = fig.canvas

fig.show()

fig.canvas.set_logical_size(700, 560)

fig[0, 0].auto_scale()

scatter1.data[:500] = np.array([0 , 0, 0])
scatter2.data[500:] = np.array([0 , 0, 0])

# NOTE: `if __name__ == "__main__"` is NOT how to use fastplotlib interactively
# please see our docs for using fastplotlib interactively in ipython and jupyter
if __name__ == "__main__":
    print(__doc__)
    fpl.run()
