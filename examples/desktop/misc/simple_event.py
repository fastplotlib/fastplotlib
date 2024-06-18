"""
Simple Event
============

Example showing how to add a simple callback event.
"""

# test_example = false
# sphinx_gallery_pygfx_docs = 'screenshot'

import fastplotlib as fpl
import imageio.v3 as iio

data = iio.imread("imageio:camera.png")

# Create a figure
figure = fpl.Figure()

# plot sine wave, use a single color
image_graphic = figure[0,0].add_image(data=data)

# show the plot
figure.show()


# define callback function to print the event data
def callback_func(event_data):
    print(event_data.info)


# Will print event data when the color changes
image_graphic.add_event_handler(callback_func, "cmap")

image_graphic.cmap = "viridis"


# adding a click event
@image_graphic.add_event_handler("click")
def click_event(event_data):
    # get the click location in screen coordinates
    xy = (event_data.x, event_data.y)

    # map the screen coordinates to world coordinates
    xy = figure[0,0].map_screen_to_world(xy)[:-1]

    # print the click location
    print(xy)


figure.canvas.set_logical_size(700, 560)

# NOTE: `if __name__ == "__main__"` is NOT how to use fastplotlib interactively
# please see our docs for using fastplotlib interactively in ipython and jupyter
if __name__ == "__main__":
    print(__doc__)
    fpl.run()
