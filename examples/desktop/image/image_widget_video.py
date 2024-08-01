"""
Image widget
============

Example showing how to scroll through one or more videos using the ImageWidget
"""

# test_example = true
# sphinx_gallery_pygfx_docs = 'screenshot'

import fastplotlib as fpl
import imageio.v3 as iio
import numpy as np


# load the standard cockatoo video
cockatoo = iio.imread("imageio:cockatoo.mp4")

# make a random grayscale video, shape is [t, x, y]
random_data = np.random.rand(*cockatoo.shape[:-1])

iw = fpl.ImageWidget(
[random_data, cockatoo],
    rgb=[False, True],
    figure_kwargs={"size": (700, 560)}
)
iw.show()

figure = iw.figure

if __name__ == "__main__":
    fpl.run()
