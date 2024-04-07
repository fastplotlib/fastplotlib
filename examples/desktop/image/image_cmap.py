"""
Simple Plot
============
Example showing simple plot creation and subsequent cmap change with Standard image from imageio.
"""

# test_example = true

import fastplotlib as fpl
import imageio.v3 as iio

im = iio.imread("imageio:camera.png")

fig = fpl.Figure()

# plot the image data
image_graphic = fig[0, 0].add_image(data=im, name="random-image")

fig.show()

fig.canvas.set_logical_size(800, 800)

fig[0, 0].auto_scale()

image_graphic.cmap = "viridis"

if __name__ == "__main__":
    print(__doc__)
    fpl.run()
