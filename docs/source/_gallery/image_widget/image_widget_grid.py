"""
Image widget grid
=================

Example showing how to view multiple images in an ImageWidget
"""

import fastplotlib as fpl
import imageio.v3 as iio

# test_example = true
# sphinx_gallery_pygfx_docs = 'screenshot'

img1 = iio.imread("imageio:camera.png")
img2 = iio.imread("imageio:astronaut.png")
img3 = iio.imread("imageio:chelsea.png")
img4 = iio.imread("imageio:wikkie.png")

iw = fpl.ImageWidget(
    data=[img1, img2, img3, img4],
    rgb=[False, True, True, True], # mix of grayscale and RGB images
    names=["cameraman", "astronaut", "chelsea", "Almar's cat"],
    # ImageWidget will sync controllers by default
    # by setting `controller_ids=None` we can have independent controllers for each subplot
    # this is useful when the images have different dimensions
    figure_kwargs={"size": (700, 560), "controller_ids": None},
)
iw.show()

figure = iw.figure

for subplot in figure:
    # sometimes the toolbar adds clutter
    subplot.toolbar = False


# NOTE: `if __name__ == "__main__"` is NOT how to use fastplotlib interactively
# please see our docs for using fastplotlib interactively in ipython and jupyter
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
