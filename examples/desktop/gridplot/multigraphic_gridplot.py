"""
Multi-Graphic GridPlot
======================

Example showing a Figure with multiple subplots and multiple graphic types.
"""

# test_example = false
# sphinx_gallery_pygfx_docs = 'screenshot'

import fastplotlib as fpl
import numpy as np
import imageio.v3 as iio
from itertools import product

# define figure
figure = fpl.Figure(shape=(2, 2), names=[["image-overlay", "circles"], ["line-stack", "scatter"]])

img = iio.imread("imageio:coffee.png")

# add image to subplot
figure["image-overlay"].add_image(data=img)

# generate overlay

# empty array for overlay, shape is [nrows, ncols, RGBA]
overlay = np.zeros(shape=(*img.shape[:2], 4), dtype=np.float32)

# set the blue values of some pixels with an alpha > 1
overlay[img[:, :, -1] > 200] = np.array([0.0, 0.0, 1.0, 0.6]).astype(np.float32)

# add overlay to image
figure["image-overlay"].add_image(data=overlay)

# generate some circles
def make_circle(center, radius: float, n_points: int = 75) -> np.ndarray:
    theta = np.linspace(0, 2 * np.pi, n_points)
    xs = radius * np.sin(theta)
    ys = radius * np.cos(theta)

    return np.column_stack([xs, ys]) + center


spatial_dims = (50, 50)

# this makes 16 circles, so we can create 16 cmap values, so it will use these values to set the
# color of the line based by using the cmap as a LUT with the corresponding cmap_transform
circles = list()
for center in product(range(0, spatial_dims[0], 15), range(0, spatial_dims[1], 15)):
    circles.append(make_circle(center, 5, n_points=75))

# things like class labels, cluster labels, etc.
cmap_transform = [
    0, 1, 1, 2,
    0, 0, 1, 1,
    2, 2, 8, 3,
    1, 9, 1, 5
]

# add an image to overlay the circles on
img2 = iio.imread("imageio:coins.png")[10::5, 5::5]

figure["circles"].add_image(data=img2, cmap="gray")

# add the circles to the figure
figure["circles"].add_line_collection(
    circles,
    cmap="tab10",
    cmap_transform=cmap_transform,
    thickness=3,
    alpha=0.5,
    name="circles-graphic"
)

# move the circles graphic so that it is centered over the image
figure["circles"]["circles-graphic"].offset = np.array([7, 7, 2])

# generate some sine data
# linspace, create 100 evenly spaced x values from -10 to 10
xs = np.linspace(-10, 10, 100)
# sine wave
ys = np.sin(xs)
sine = np.dstack([xs, ys])[0]

# make 10 identical waves
sine_waves = 10 * [sine]

# add the line stack to the figure
figure["line-stack"].add_line_stack(data=sine_waves, cmap="Wistia", separation=1)

figure["line-stack"].auto_scale(maintain_aspect=True)

# generate some scatter data
# create a gaussian cloud of 500 points
n_points = 500

mean = [0, 0]  # mean of the Gaussian distribution
covariance = [[1, 0], [0, 1]]  # covariance matrix

gaussian_cloud = np.random.multivariate_normal(mean, covariance, n_points)
gaussian_cloud2 = np.random.multivariate_normal(mean, covariance, n_points)

# add the scatter graphics to the figure
figure["scatter"].add_scatter(data=gaussian_cloud, sizes=2, cmap="jet")
figure["scatter"].add_scatter(data=gaussian_cloud2, colors="r", sizes=2)

figure.show()

figure.canvas.set_logical_size(700, 560)

# NOTE: `if __name__ == "__main__"` is NOT how to use fastplotlib interactively
# please see our docs for using fastplotlib interactively in ipython and jupyter
if __name__ == "__main__":
    print(__doc__)
    fpl.run()

