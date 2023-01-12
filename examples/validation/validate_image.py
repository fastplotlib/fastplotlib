"""
Simple Image
============

Example showing a simple random image.
"""

# test_example = true
# sphinx_gallery_pygfx_render = True

from fastplotlib import plot
import numpy as np

# create a `Plot` instance
plot = Plot()

# make some random 2D image data
data = np.random.rand(512, 512)

# plot the image data
image_graphic = plot.add_image(data=data, name="random-image")

if __name__ == "__main__":
    print(__doc__)