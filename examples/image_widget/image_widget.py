"""
Image widget
============

Example showing the image widget in action.

Every image in an `ImageWidget` is associated with an interactive Histogram LUT tool and colorbar. Right-click the
colorbar to pick colormaps.
"""

# test_example = true
# sphinx_gallery_pygfx_docs = 'screenshot'

import fastplotlib as fpl
import imageio.v3 as iio  # not a fastplotlib dependency, only used for examples

a = iio.imread("imageio:camera.png")
iw = fpl.ImageWidget(data=a, cmap="viridis", figure_kwargs={"size": (700, 560)})
iw.show()

# Access ImageGraphics managed by the image widget
iw.figure[0, 0]["image_widget_managed"].data[:50, :50] = 0
iw.figure[0, 0]["image_widget_managed"].cmap = "gnuplot2"

# another way to access the image widget managed ImageGraphics
iw.managed_graphics[0].data[450:, 450:] = 255

figure = iw.figure

# NOTE: `if __name__ == "__main__"` is NOT how to use fastplotlib interactively
# please see our docs for using fastplotlib interactively in ipython and jupyter
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
