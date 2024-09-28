"""
Linear Selectors Image
======================

Example showing how to use a `LinearSelector` to selector rows or columns of an image. The subplot on the right
displays the data for the selector row and column.
"""

# test_example = false
# sphinx_gallery_pygfx_docs = 'screenshot'

import fastplotlib as fpl
import numpy as np


# create some data
xs = np.linspace(0, 10 * np.pi, 100)
sine = np.column_stack([xs, np.sin(xs)])
cosine = np.column_stack([xs, np.cos(xs)])

# a varying sine-cosine quilted pattern
image_xs, image_ys = np.meshgrid(xs, xs)
multiplier = np.linspace(0, 10, 100)
image_data = multiplier * np.sin(image_xs) + multiplier * np.cos(image_ys)

figure = fpl.Figure((1, 2), size=(700, 560), names=[["image", "selected row and column data"]])

# create an image
image = figure[0, 0].add_image(image_data)

# add a row selector
image_row_selector = image.add_linear_selector(axis="y")

# add column selector
image_col_selector = image.add_linear_selector()

# make a line to indicate row data
line_image_row = figure[0, 1].add_line(image.data[0])

# make a line to indicate column data
line_image_col_data = np.column_stack([image.data[:, 0], np.arange(100)])
line_image_col = figure[0, 1].add_line(line_image_col_data)


# callbacks to change the line data in subplot [0, 1]
# to display selected row and selected column data
def image_row_selector_changed(ev):
    ix = ev.get_selected_index()
    new_data = image.data[ix]
    # set y values of line
    line_image_row.data[:, 1] = new_data


def image_col_selector_changed(ev):
    ix = ev.get_selected_index()
    new_data = image.data[:, ix]
    # set x values of line
    line_image_col.data[:, 0] = new_data


# add event handlers, you can also use a decorator
image_row_selector.add_event_handler(image_row_selector_changed, "selection")
image_col_selector.add_event_handler(image_col_selector_changed, "selection")


figure.show()

for subplot in figure:
    subplot.camera.zoom = 0.5


# NOTE: `if __name__ == "__main__"` is NOT how to use fastplotlib interactively
# please see our docs for using fastplotlib interactively in ipython and jupyter
if __name__ == "__main__":
    print(__doc__)
    fpl.run()
