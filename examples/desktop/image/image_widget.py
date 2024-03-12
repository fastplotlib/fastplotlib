"""
Image widget
============
Example showing the image widget in action.
When run in a notebook, or with the Qt GUI backend, sliders are also shown.
"""

import numpy as np
import fastplotlib as fpl
import imageio.v3 as iio  # not a fastplotlib dependency, only used for examples


a = iio.imread("imageio:camera.png")
iw = fpl.widgets.ImageWidget(data=a, cmap="viridis")
iw.show()


if __name__ == "__main__":
    print(__doc__)
    fpl.run()
