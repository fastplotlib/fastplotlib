"""
Many UIs surrounding the render area
====================================

Mostly a test example with imgui windows on every edge of the Figure.
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
ys = np.sin(xs) + np.random.normal(scale=0.5, size=100)
data = np.column_stack([xs, ys])


# make a figure
figure = fpl.Figure(shape=(3, 2), size=(700, 560))

for subplot in figure:
    subplot.add_line(data, thickness=1, colors="r", name="sine-wave", uniform_color=True)


class Window1(EdgeWindow):
    def __init__(self, figure, size, location, title):
        super().__init__(figure=figure, size=size, location=location, title=title)
        self._title = title

    def update(self):
        if imgui.button("reset data"):
            for subplot in self._figure:
                subplot["sine-wave"].data[:, 1] = np.sin(xs) + np.random.normal(scale=0.5, size=100)


for i, location in enumerate(["left", "right", "top", "bottom"]):
    gui = Window1(figure, 100, location, f"ui-{i}")
    figure.add_gui(gui)

figure.show()

fpl.loop.run()
