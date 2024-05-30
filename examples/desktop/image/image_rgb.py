"""
RGB Image
=========

Example showing the simple plot creation with 512 x 512 2D RGB image.
"""

# test_example = true
# sphinx_gallery_pygfx_docs = 'screenshot'

import fastplotlib as fpl
import imageio.v3 as iio

im = iio.imread("imageio:astronaut.png")

fig = fpl.Figure()

# plot the image data
image_graphic = fig[0, 0].add_image(data=im, name="iio astronaut")

fig.show()

# set canvas variable for sphinx_gallery to properly generate examples
canvas = fig.canvas

fig.canvas.set_logical_size(800, 800)

fig[0, 0].auto_scale()


if __name__ == "__main__":
    print(__doc__)
    fpl.run()
