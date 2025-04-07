"""
Events line data thickness
==========================

Simple example of adding event handlers for line data and thickness.
"""

# test_example = false
# sphinx_gallery_pygfx_docs = 'screenshot'

import fastplotlib as fpl
from fastplotlib.graphics.features import GraphicFeatureEvent
import numpy as np

figure = fpl.Figure(size=(700, 560))

xs = np.linspace(0, 4 * np.pi, 100)
# sine wave
ys = np.sin(xs)
sine = np.column_stack([xs, ys])

# cosine wave
ys = np.cos(xs)
cosine = np.column_stack([xs, ys])

# create line graphics
sine_graphic = figure[0, 0].add_line(data=sine)
cosine_graphic = figure[0, 0].add_line(data=cosine, offset=(0, 4, 0))

# make a list of the line graphics for convenience
lines = [sine_graphic, cosine_graphic]


def change_thickness(ev: GraphicFeatureEvent):
    # sets thickness of all the lines
    new_value = ev.info["value"]

    for g in lines:
        g.thickness = new_value


def change_data(ev: GraphicFeatureEvent):
    # sets data of all the lines using the given event and value from the event

    # the user's slice/index
    # This can be a single int index, a slice,
    # or even a numpy array of int or bool for fancy indexing!
    indices = ev.info["key"]

    # the new values to set at the given indices
    new_values = ev.info["value"]

    # set the data for all the lines
    for g in lines:
        g.data[indices] = new_values


# add the event handlers to the line graphics
for g in lines:
    g.add_event_handler(change_thickness, "thickness")
    g.add_event_handler(change_data, "data")


figure.show()
figure[0, 0].axes.intersection = (0, 0, 0)

# set the y-value of the middle 40 points of the sine graphic to 1
# after the sine_graphic sets its data, the event handlers will be called
# and therefore the cosine graphic will also set its data using the event data
sine_graphic.data[30:70, 1] = np.ones(40)

# set the thickness of the cosine graphic, this will trigger an event
# that causes the sine graphic's thickness to also be set from this value
cosine_graphic.thickness = 10

# NOTE: `if __name__ == "__main__"` is NOT how to use fastplotlib interactively
# please see our docs for using fastplotlib interactively in ipython and jupyter
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
