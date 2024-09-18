"""
Image widget grid
=================

Example showing how to view multiple images in an ImageWidget
"""

import numpy as np
import fastplotlib as fpl
import imageio.v3 as iio


img1 = iio.imread("imageio:camera.png")
img2 = iio.imread("imageio:astronaut.png")
img3 = iio.imread("imageio:chelsea.png")
img4 = iio.imread("imageio:wikkie.png")

iw = fpl.ImageWidget([img1, img2, img3, img4], rgb=[True, False, True, True])
iw.show()

figure = iw.figure


# NOTE: `if __name__ == "__main__"` is NOT how to use fastplotlib interactively
# please see our docs for using fastplotlib interactively in ipython and jupyter
if __name__ == "__main__":
    print(__doc__)
    fpl.run()
