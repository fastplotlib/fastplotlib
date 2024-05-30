"""
Image widget
============

Example showing the image widget in action.
When run in a notebook, or with the Qt GUI backend, sliders are also shown.
"""

# sphinx_gallery_pygfx_docs = 'hidden'

import fastplotlib as fpl
import imageio.v3 as iio  # not a fastplotlib dependency, only used for examples

a = iio.imread("imageio:camera.png")
iw = fpl.ImageWidget(data=a, cmap="viridis")
iw.show()

# set canvas variable for sphinx_gallery to properly generate examples
canvas = iw.figure.canvas


if __name__ == "__main__":
    print(__doc__)
    fpl.run()
