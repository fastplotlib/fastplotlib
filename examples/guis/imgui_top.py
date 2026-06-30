"""
ImGUI Header GUI
================

Basic examples demonstrating how to use create a header gui
"""

# test_example = true
# sphinx_gallery_pygfx_docs = 'screenshot'

import numpy as np
import fastplotlib as fpl

# subclass from EdgeWindow to make a custom ImGUI Window to place inside the figure!
from fastplotlib.ui import EdgeWindow
from imgui_bundle import imgui

# make some initial data
np.random.seed(0)

xs = np.linspace(0, np.pi * 10, 100)
ys = np.sin(xs) + np.random.normal(scale=0.0, size=100)
data = np.column_stack([xs, ys])


# make a figure
figure = fpl.Figure(size=(700, 560))

# make some scatter points at every 10th point
figure[0, 0].add_scatter(data[::10], colors="cyan", sizes=15, name="sine-scatter", uniform_color=True)

# place a line above the scatter
figure[0, 0].add_line(data, thickness=3, colors="r", name="sine-wave", uniform_color=True)


class ImguiExample(EdgeWindow):
    def __init__(self, figure, size, location, title):
        super().__init__(figure=figure, size=size, location=location, title=title, window_flags=imgui.WindowFlags_.no_title_bar | imgui.WindowFlags_.no_resize)

    def update(self):
        imgui.text("This is a top window")


# make GUI instance
gui = ImguiExample(
    figure,  # the figure this GUI instance should live inside
    size=30,  # width or height of the GUI window within the figure
    location="top",  # the edge to place this window at
    title=" ",  # window title
)

# add it to the figure
figure.add_gui(gui)

figure.show()

# NOTE: fpl.loop.run() should not be used for interactive sessions
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()