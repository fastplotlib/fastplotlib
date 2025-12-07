"""
Cursor transform
================

Create a cursor and add them to subplots with a transform function. An example usecase is image registration.
"""

# test_example = False
# sphinx_gallery_pygfx_docs = 'screenshot'

import numpy as np
import fastplotlib as fpl
import imageio.v3 as iio


# get an image
img1 = iio.imread("imageio:camera.png")

# create another image, but it is offset
img2 = np.zeros(img1.shape)
img2[50:, 20:] = img1[:-50, :-20]

figure = fpl.Figure((1, 2), size=(700, 500))

# add images
figure[0, 0].add_image(img1)
figure[0, 1].add_image(img2)

# create cursor
cursor = fpl.Cursor("crosshair")

# add first subplot to cursor
cursor.add_subplot(figure[0, 0])

# a transform function for subplot 2 to indicate that the data is shifted
def transform_func(pos):
    return (pos[0] + 20, pos[1] + 50)

# add second subplot with a transform
cursor.add_subplot(figure[0, 1], transform=transform_func)

figure.show()

# you can hide the canvas cursor
figure.canvas.set_cursor("none")

# NOTE: fpl.loop.run() should not be used for interactive sessions
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
