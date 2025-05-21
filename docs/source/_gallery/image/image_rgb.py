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

figure = fpl.Figure(size=(700, 560))

# plot the image data
image_graphic = figure[0, 0].add_image(data=im, name="iio astronaut")

figure.show()


# NOTE: `if __name__ == "__main__"` is NOT how to use fastplotlib interactively
# please see our docs for using fastplotlib interactively in ipython and jupyter
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
