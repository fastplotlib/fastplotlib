"""
Extent Layout
=============

Create subplots using given extents in absolute pixels. This example plots two images and their histograms in
separate subplots

"""

import numpy as np
import imageio.v3 as iio
import fastplotlib as fpl

# load images
img1 = iio.imread("imageio:astronaut.png")
img2 = iio.imread("imageio:wikkie.png")

# calculate histograms
hist_1, edges_1 = np.histogram(img1)
centers_1 = edges_1[:-1] + np.diff(edges_1) / 2

hist_2, edges_2 = np.histogram(img2)
centers_2 = edges_2[:-1] + np.diff(edges_2) / 2

# figure size in pixels
size = (700, 560)

# extent is (xmin, xmax, ymin, ymax)
# here it is defined in absolute pixels
extents = [
    (0, 200, 0, 280),  # for image1
    (0, 200, 280, 560),  # for image2
    (200, 700, 0, 280),  # for image1 histogram
    (200, 700, 280, 560),  # for image2 histogram
]

# create a figure using the rects and size
# also give each subplot a name
figure = fpl.Figure(
    extents=extents,
    names=["astronaut image", "wikkie image", "astronaut histogram", "wikkie histogram"],
    size=size
)

# add image to the corresponding subplots
figure["astronaut image"].add_image(img1)
figure["wikkie image"].add_image(img2)

# add histogram to the corresponding subplots
figure["astronaut histogram"].add_line(np.column_stack([centers_1, hist_1]))
figure["wikkie histogram"].add_line(np.column_stack([centers_2, hist_2]))


for subplot in figure:
    if "image" in subplot.name:
        # remove axes from image subplots to reduce clutter
        subplot.axes.visible = False
        continue

    # don't maintain aspect ratio for the histogram subplots
    subplot.camera.maintain_aspect = False


figure.show()


# NOTE: `if __name__ == "__main__"` is NOT how to use fastplotlib interactively
# please see our docs for using fastplotlib interactively in ipython and jupyter
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
