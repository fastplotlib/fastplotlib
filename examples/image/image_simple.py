"""
Simple Image
============

Example showing the simple plot creation with Standard imageio image.
"""

# test_example = true
# sphinx_gallery_pygfx_docs = 'screenshot'

import fastplotlib as fpl
import imageio.v3 as iio

figure = fpl.Figure(size=(700, 560))

data = iio.imread("imageio:camera.png")

# plot the image data
image_graphic = figure[0, 0].add_image(data=data, name="iio camera")

figure.show()

# NOTE: `if __name__ == "__main__"` is NOT how to use fastplotlib interactively
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
