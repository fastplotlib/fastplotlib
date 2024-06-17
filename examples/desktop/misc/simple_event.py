"""
Simple Event
============

Example showing how to add a simple callback event.
"""

# test_example = false
# sphinx_gallery_pygfx_docs = 'screenshot'

import fastplotlib as fpl
import numpy as np

# generate some date
# linspace, create 100 evenly spaced x values from -10 to 10
xs = np.linspace(-10, 10, 100)
# sine wave
ys = np.sin(xs)
sine = np.column_stack([xs, ys])

# cosine wave
ys = np.cos(xs) + 5
cosine = np.column_stack([xs, ys])

# sinc function
a = 0.5
ys = np.sinc(xs) * 3 + 8
sinc = np.column_stack([xs, ys])

# Create a figure
figure = fpl.Figure()

# we will add all the lines to the same subplot
subplot = figure[0, 0]

# plot sine wave, use a single color
sine_graphic = subplot.add_line(data=sine, thickness=5, colors="magenta")

# you can also use colormaps for lines!
cosine_graphic = subplot.add_line(data=cosine, thickness=12, cmap="autumn")

# or a list of colors for each datapoint
colors = ["r"] * 25 + ["purple"] * 25 + ["y"] * 25 + ["b"] * 25
sinc_graphic = subplot.add_line(data=sinc, thickness=5, colors=colors)

# show the plot
figure.show()

subplot.auto_scale(maintain_aspect=True)


def callback_func(event_data):
    print(event_data)


# Will print event data when the color changes
cosine_graphic.colors.add_event_handler(callback_func)

# more complex indexing of colors
# from point 15 - 30, set every 3rd point as "cyan"
cosine_graphic.colors[15:50:3] = "cyan"

figure.canvas.set_logical_size(700, 560)

# NOTE: `if __name__ == "__main__"` is NOT how to use fastplotlib interactively
# please see our docs for using fastplotlib interactively in ipython and jupyter
if __name__ == "__main__":
    print(__doc__)
    fpl.run()
