"""
Collapsible GUI
===============

Demonstrates adding a keybind to toggle GUI visibility.

Press spacebar to toggle the GUI panel visibility.
"""

# test_example = true
# sphinx_gallery_pygfx_docs = 'screenshot'

import numpy as np
import fastplotlib as fpl

from fastplotlib.ui import EdgeWindow
from imgui_bundle import imgui


# make some data
xs = np.linspace(0, np.pi * 10, 100)
ys = np.sin(xs)
data = np.column_stack([xs, ys])

figure = fpl.Figure(size=(700, 560))

line = figure[0, 0].add_line(data, thickness=3, colors="magenta", name="sine-wave")


class SimpleGUI(EdgeWindow):
    def __init__(self, figure, size, location, title):
        super().__init__(figure=figure, size=size, location=location, title=title)
        self._line = self._figure[0, 0]["sine-wave"]
        self._amplitude = 1.0

    def update(self):
        imgui.text("press spacebar to collapse")
        imgui.separator()

        changed, amplitude = imgui.slider_float(
            "amplitude", v=self._amplitude, v_min=0.1, v_max=5.0
        )
        if changed:
            self._amplitude = amplitude
            self._line.data[:, 1] = np.sin(xs) * self._amplitude

        changed, thickness = imgui.slider_float(
            "thickness", v=self._line.thickness, v_min=1.0, v_max=20.0
        )
        if changed:
            self._line.thickness = thickness


gui = SimpleGUI(
    figure,
    size=200,
    location="right",
    title="Controls",
)

figure.add_gui(gui)


# keybind: spacebar to toggle collapse
@figure.renderer.add_event_handler("key_down")
def toggle_collapse(ev):
    if ev.key == " ":
        right_gui = figure.guis["right"]
        if right_gui is not None:
            right_gui.collapsed = not right_gui.collapsed
            figure._fpl_reset_layout()


figure.show()

if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
