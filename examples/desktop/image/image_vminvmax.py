"""
Simple Image Vmin Vmax
======================
Example showing the simple plot creation followed by changing the vmin/vmax with Standard imageio image.
"""
# test_example = true
# sphinx_gallery_fastplotlib_render = True

import fastplotlib as fpl
import imageio.v3 as iio


plot = fpl.Plot()
# to force a specific framework such as glfw:
# plot = fpl.Plot(canvas="glfw")

data = iio.imread("imageio:astronaut.png")

# plot the image data
image_graphic = plot.add_image(data=data, name="iio astronaut")

plot.show()

plot.canvas.set_logical_size(800, 800)

plot.auto_scale()

image_graphic.cmap.vmin = 0.5
image_graphic.cmap.vmax = 0.75


if __name__ == "__main__":
    print(__doc__)
    fpl.run()
