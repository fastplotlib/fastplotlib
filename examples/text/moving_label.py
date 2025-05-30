"""
Moving TextGraphic label
========================

A TextGraphic that labels a point on a line and another TextGraphic that moves along the line on every draw.
"""

# test_example = false
# sphinx_gallery_pygfx_docs = 'animate 10s'

import numpy as np
import fastplotlib as fpl

# create a sinc wave
xs = np.linspace(-2 * np.pi, 2 * np.pi, 200)
ys = np.sinc(xs)

data = np.column_stack([xs, ys])

# create a figure
figure = fpl.Figure(size=(700, 450))

# sinc wave
line = figure[0, 0].add_line(data, thickness=2)

# position for the text label on the peak
pos = (0, max(ys), 0)

# create label for the peak
text_peak = figure[0, 0].add_text(
    f"peak  ",
    font_size=20,
    anchor="bottom-right",
    offset=pos
)

# add a point on the peak
point_peak = figure[0, 0].add_scatter(np.asarray([pos]), sizes=10, colors="r")

# create a text that will move along the line
text_moving = figure[0, 0].add_text(
    f"({xs[0]:.2f}, {ys[0]:.2f})  ",
    font_size=16,
    outline_color="k",
    outline_thickness=1,
    anchor="top-center",
    offset=(*data[0], 0)
)
# a point that will move on the line
point_moving = figure[0, 0].add_scatter(np.asarray([data[0]]), sizes=10, colors="magenta")


index = 0
def update():
    # moves the text and point before every draw
    global index
    # get the new position
    new_pos = (*data[index], 0)

    # move the text and point to the new position
    text_moving.offset = new_pos
    point_moving.data[0] = new_pos

    # set the text to the new position
    text_moving.text = f"({new_pos[0]:.2f}, {new_pos[1]:.2f})"

    # increment index
    index += 1
    if index == data.shape[0]:
        index = 0


# add update as an animation functions
figure.add_animations(update)

figure[0, 0].axes.visible = False
figure.show(maintain_aspect=False)


# NOTE: `if __name__ == "__main__"` is NOT how to use fastplotlib interactively
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
