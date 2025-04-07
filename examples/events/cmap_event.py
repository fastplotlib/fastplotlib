"""
cmap event
==========

Add a cmap event handler to multiple graphics. When any one graphic changes the cmap, the cmap of all other graphics
is also changed.

This also shows how bidirectional events are supported.
"""

# test_example = false
# sphinx_gallery_pygfx_docs = 'screenshot'

import numpy as np
import fastplotlib as fpl
import imageio.v3 as iio

# load images
img1 = iio.imread("imageio:camera.png")
img2 = iio.imread("imageio:moon.png")

# Create a figure
figure = fpl.Figure(
    shape=(2, 2),
    size=(700, 560),
    names=["camera", "moon", "sine", "cloud"],
)

# create graphics
figure["camera"].add_image(img1)
figure["moon"].add_image(img2)

# sine wave
xs = np.linspace(0, 4 * np.pi, 100)
ys = np.sin(xs)

figure["sine"].add_line(np.column_stack([xs, ys]))

# make a 2D gaussian cloud
cloud_data = np.random.normal(0, scale=3, size=1000).reshape(500, 2)
figure["cloud"].add_scatter(
    cloud_data,
    sizes=3,
    cmap="plasma",
    cmap_transform=np.linalg.norm(cloud_data, axis=1)  # cmap transform using distance from origin
)
figure["cloud"].axes.intersection = (0, 0, 0)

# show the plot
figure.show()


# event handler to change the cmap of all graphics when the cmap of any one graphic changes
def cmap_changed(ev: fpl.GraphicFeatureEvent):
    # get the new cmap
    new_cmap = ev.info["value"]

    # set cmap of the graphics in the other subplots
    for subplot in figure:
        subplot.graphics[0].cmap = new_cmap


for subplot in figure:
    # add event handler to the graphic added to each subplot
    subplot.graphics[0].add_event_handler(cmap_changed, "cmap")


# change the cmap of graphic image, triggers all other graphics to set the cmap
figure["camera"].graphics[0].cmap = "jet"

# NOTE: `if __name__ == "__main__"` is NOT how to use fastplotlib interactively
# please see our docs for using fastplotlib interactively in ipython and jupyter
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
