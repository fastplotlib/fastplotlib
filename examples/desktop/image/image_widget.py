"""
Image widget
============

Example showing the image widget in action.
"""

# test_example = true
# sphinx_gallery_pygfx_docs = 'screenshot'

import fastplotlib as fpl
import imageio.v3 as iio  # not a fastplotlib dependency, only used for examples

a = iio.imread("imageio:camera.png")
iw = fpl.ImageWidget(data=a, cmap="viridis", figure_kwargs={"size": (700, 560)})
iw.show()

figure = iw.figure

# NOTE: `if __name__ == "__main__"` is NOT how to use fastplotlib interactively
# please see our docs for using fastplotlib interactively in ipython and jupyter
if __name__ == "__main__":
    print(__doc__)
    fpl.run()
