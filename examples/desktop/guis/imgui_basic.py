"""
ImGUI Basics
============

Basic examples demonstrating how to use imgui in fastplotlib.

See the imgui docs for extensive examples on how to create all UI elements: https://pyimgui.readthedocs.io/en/latest/reference/imgui.core.html#imgui.core.begin_combo
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
ys = np.sin(xs) + np.random.normal(scale=0.1, size=100)
data = np.column_stack([xs, ys])


figure = fpl.Figure(size=(700, 560))

# make some scatter points at every 10th point
figure[0, 0].add_scatter(data[::10], colors="cyan", sizes=15, name="sine-scatter", uniform_color=True)

# place a line above the scatter
figure[0, 0].add_line(data, colors="r", name="sine-wave", uniform_color=True)


class ImguiExample(EdgeWindow):
    def __init__(self, figure, size, location, title):
        super().__init__(figure=figure, size=size, location=location, title=title)

        # wave amplitude
        self._amplitude = 1

        # sigma for gaussian noise
        self._sigma = 0.1

    def update(self):
        line = figure[0, 0]["sine-wave"]
        # get the current line RGB values
        rgb_color = line.colors[:-1]

        # make color picker
        changed_color, rgb = imgui.color_picker3("color", col=rgb_color)

        # get current line color alpha value
        alpha = line.colors[-1]
        changed_alpha, new_alpha = imgui.slider_float("alpha", v=alpha, v_min=0.0, v_max=1.0)

        if changed_color | changed_alpha:
            # set new color along with alpha
            line.colors = [*rgb, new_alpha]

        # example with a slider, you can also use input_float
        changed, amplitude = imgui.slider_float("amplitude", v=self._amplitude, v_max=10, v_min=0.1)
        if changed:
            # set y values
            self._amplitude = amplitude
            line.data[:, 1] = np.sin(xs) * self._amplitude

        changed, thickness = imgui.slider_float("thickness", v=line.thickness, v_max=50.0, v_min=2.0)
        if changed:
            line.thickness = thickness

        changed, sigma = imgui.slider_float("noise-sigma", v=self._sigma, v_max=1.0, v_min=0.0)
        if changed:
            self._sigma = sigma
            line.data[:, 1] = (np.sin(xs) * self._amplitude) + np.random.normal(scale=self._sigma, size=100)


gui = ImguiExample(figure, size=250, location="right", title="Imgui Window")

figure.add_gui(gui)

figure.show()


# NOTE: `if __name__ == "__main__"` is NOT how to use fastplotlib interactively
# please see our docs for using fastplotlib interactively in ipython and jupyter
if __name__ == "__main__":
    print(__doc__)
    fpl.run()
