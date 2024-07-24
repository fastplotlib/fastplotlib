"""
Simple Line Plot
================

Example showing how to use a `LinearSelector` with lines, line collections, and images
"""

# test_example = true
# sphinx_gallery_pygfx_docs = 'screenshot'

import fastplotlib as fpl
import numpy as np

xs = np.linspace(0, 10 * np.pi, 100)
sine = np.column_stack([xs, np.sin(xs)])
cosine = np.column_stack([xs, np.cos(xs)])

image_xs, image_ys = np.meshgrid(xs, xs)
multiplier = np.linspace(0, 10, 100)
image_data = multiplier * np.sin(image_xs) + multiplier * np.cos(image_ys)

figure = fpl.Figure(
    shape=(2, 2),
    size=(700, 560)
)

line = figure[0, 0].add_line(sine, cmap="jet")
line_selector = line.add_linear_selector()

line_selector_text = (f"x value: {line_selector.selection / np.pi:.2f}π\n"
                      f"y value: {line.data[0, 1]:.2f}\n"
                      f"index: {line_selector.get_selected_index()}")

line_selection_label = figure[0, 0].add_text(
    line_selector_text,
    offset=(0., 1.75, 0.),
    anchor="middle-left",
    font_size=22,
    face_color=line.colors[0],
    outline_color="w",
    outline_thickness=0.1,
)


@line_selector.add_event_handler("selection")
def line_selector_changed(ev):
    selection = ev.info["value"]
    index = ev.get_selected_index()

    line_selection_label.text = \
        (f"x value: {selection / np.pi:.2f}π\n"
         f"y value: {line.data[index, 1]:.2f}\n"
         f"index: {index}")

    line_selection_label.face_color = line.colors[index]


line_stack = figure[0, 1].add_line_stack([sine, cosine], colors=["magenta", "cyan"], separation=1)
line_stack_selector = line_stack.add_linear_selector()

line_stack_selector_text = (f"x value: {line_stack_selector.selection / np.pi:.2f}π\n"
                            f"index: {line_selector.get_selected_index()}\n"
                            f"sine y value: {line_stack[0].data[0, 1]:.2f}\n"
                            f"cosine y value: {line_stack[1].data[0, 1]:.2f}\n")

line_stack_selector_label = figure[0, 1].add_text(
    line_stack_selector_text,
    offset=(0., 7.0, 0.),
    anchor="middle-left",
    font_size=18,
    face_color="w",
)


@line_stack_selector.add_event_handler("selection")
def line_stack_selector_changed(ev):
    selection = ev.info["value"]

    # linear selectors on line collections return a
    # list of indices for each graphic in the collection
    index = ev.get_selected_index()[0]

    line_stack_selector_label.text = \
        (f"x value: {selection / np.pi:.2f}π\n"
         f"index: {index}\n"
         f"sine y value: {line_stack[0].data[index, 1]:.2f}\n"
         f"cosine y value: {line_stack[1].data[index, 1]:.2f}\n")


image = figure[1, 0].add_image(image_data)
image_row_selector = image.add_linear_selector(axis="y")
image_col_selector = image.add_linear_selector()

line_image_row = figure[1, 1].add_line(image.data[0])

line_image_col_data = np.column_stack([image.data[:, 0], np.arange(100)])
line_image_col = figure[1, 1].add_line(line_image_col_data)


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


image_row_selector.add_event_handler(image_row_selector_changed, "selection")
image_col_selector.add_event_handler(image_col_selector_changed, "selection")

figure.show(maintain_aspect=False)

for subplot in [figure[0, 0], figure[0, 1]]:
    subplot.axes.auto_grid = False
    subplot.axes.grids.xy.major_step = (np.pi, 1)
    subplot.axes.grids.xy.minor_step = (0, 0)
    subplot.camera.zoom = 0.6

figure[1, 1].camera.zoom = 0.5

if __name__ == "__main__":
    fpl.run()
