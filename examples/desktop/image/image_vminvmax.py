"""
Image Vmin/Vmax
===============

Example showing the simple plot creation followed by changing the vmin/vmax with Standard imageio image.
"""

# test_example = true
# sphinx_gallery_pygfx_docs = 'screenshot'

import fastplotlib as fpl
import imageio.v3 as iio

fig = fpl.Figure()

data = iio.imread("imageio:astronaut.png")

# plot the image data
image_graphic = fig[0, 0].add_image(data=data, name="iio astronaut")

fig.show()

# set canvas variable for sphinx_gallery to properly generate examples
# NOT required for users
canvas = fig.canvas

fig.canvas.set_logical_size(800, 800)

fig[0, 0].auto_scale()

image_graphic.cmap.vmin = 0.5
image_graphic.cmap.vmax = 0.75

# NOTE: `if __name__ == "__main__"` is NOT how to use fastplotlib interactively
# please see our docs for using fastplotlib interactively in ipython and jupyter
if __name__ == "__main__":
    print(__doc__)
    fpl.run()
