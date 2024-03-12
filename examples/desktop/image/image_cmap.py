"""
Simple Plot
============
Example showing simple plot creation and subsequent cmap change with Standard image from imageio.
"""

# test_example = true

import fastplotlib as fpl
import imageio.v3 as iio


plot = fpl.Plot()
# to force a specific framework such as glfw:
# plot = fpl.Plot(canvas="glfw")

im = iio.imread("imageio:camera.png")

# plot the image data
image_graphic = plot.add_image(data=im, name="random-image")

plot.show()

plot.canvas.set_logical_size(800, 800)

plot.auto_scale()

image_graphic.cmap = "viridis"

if __name__ == "__main__":
    print(__doc__)
    fpl.run()
