"""
Image Vmin/Vmax
===============

Example showing the simple plot creation followed by changing the vmin/vmax with Standard imageio image.
"""

# test_example = true
# sphinx_gallery_pygfx_docs = 'screenshot'

import fastplotlib as fpl
import imageio.v3 as iio

figure = fpl.Figure(size=(700, 560))

data = iio.imread("imageio:astronaut.png")

# plot the image data
image_graphic = figure[0, 0].add_image(data=data, name="iio astronaut")

figure.show()

image_graphic.vmin = 0.5
image_graphic.vmax = 0.75

# NOTE: `if __name__ == "__main__"` is NOT how to use fastplotlib interactively
# please see our docs for using fastplotlib interactively in ipython and jupyter
if __name__ == "__main__":
    print(__doc__)
    fpl.run()
