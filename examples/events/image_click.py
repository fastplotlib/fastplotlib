"""
Image click event
=================

Example showing how to use a click event on an image.
"""

# test_example = false
# sphinx_gallery_pygfx_docs = 'screenshot'

import fastplotlib as fpl
import pygfx
import imageio.v3 as iio

data = iio.imread("imageio:camera.png")

# Create a figure
figure = fpl.Figure(size=(700, 560))

# create image graphic
image_graphic = figure[0, 0].add_image(data=data)

# show the plot
figure.show()


# adding a click event, we can also use decorators to add event handlers
@image_graphic.add_event_handler("click")
def click_event(ev: pygfx.PointerEvent):
    # get the click location in screen coordinates
    xy = (ev.x, ev.y)

    # map the screen coordinates to world coordinates
    xy = figure[0, 0].map_screen_to_world(xy)[:-1]

    # print the click location
    print(xy)


# NOTE: `if __name__ == "__main__"` is NOT how to use fastplotlib interactively
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
