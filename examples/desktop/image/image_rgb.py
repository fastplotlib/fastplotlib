"""
Simple Plot
============
Example showing the simple plot creation with 512 x 512 2D RGB image.
"""
# test_example = true

import fastplotlib as fpl
import imageio.v3 as iio


plot = fpl.Plot()
# to force a specific framework such as glfw:
# plot = fpl.Plot(canvas="glfw")

im = iio.imread("imageio:astronaut.png")

# plot the image data
image_graphic = plot.add_image(data=im, name="iio astronaut")

plot.show()

plot.canvas.set_logical_size(800, 800)

plot.auto_scale()


if __name__ == "__main__":
    print(__doc__)
    fpl.run()
