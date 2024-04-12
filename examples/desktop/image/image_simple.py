"""
Simple Plot
============
Example showing the simple plot creation with Standard imageio image.
"""

# test_example = true

import fastplotlib as fpl
import imageio.v3 as iio


fig = fpl.Figure()

data = iio.imread("imageio:camera.png")

# plot the image data
image_graphic = fig[0, 0].add_image(data=data, name="iio camera")

fig.show()

fig.canvas.set_logical_size(800, 800)

fig[0, 0].auto_scale()

if __name__ == "__main__":
    print(__doc__)
    fpl.run()
