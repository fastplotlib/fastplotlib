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
from fastplotlib.utils.imgui import ChangeFlag
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
        super().__init__(figure=figure, size=size, location=location, title=title)
        # this UI will modify the line
        self._line = self._figure[0, 0]["sine-wave"]

        # set the default values
        # wave amplitude
        self._amplitude = 1

        # sigma for gaussian noise
        self._sigma = 0.0

        # a flag that once True, always remains True
        self._color_changed = ChangeFlag(False)
        self._data_changed = ChangeFlag(False)


    def update(self):
        # force flag values to reset
        self._color_changed.force_value(False)
        self._data_changed.force_value(False)

        # get the current line RGB values
        rgb_color = self._line.colors[:-1]
        # make color picker
        self._color_changed.value, rgb = imgui.color_picker3("color", col=rgb_color)

        # get current line color alpha value
        alpha = self._line.colors[-1]
        # make float slider
        self._color_changed.value, new_alpha = imgui.slider_float("alpha", v=alpha, v_min=0.0, v_max=1.0)

        # if RGB or alpha flag indicates a change
        if self._color_changed:
            # set new color along with alpha
            self._line.colors = [*rgb, new_alpha]

        # slider for thickness
        changed, thickness = imgui.slider_float("thickness", v=self._line.thickness, v_max=50.0, v_min=2.0)
        if changed:
            self._line.thickness = thickness

        # example of a slider, you can also use input_float
        self._data_changed.value, self._amplitude = imgui.slider_float("amplitude", v=self._amplitude, v_max=10, v_min=0.1)

        # slider for gaussian noise
        self._data_changed.value, self._sigma = imgui.slider_float("noise-sigma", v=self._sigma, v_max=1.0, v_min=0.0)

        # data flag indicates change
        if self._data_changed:
            self._set_data()

        # reset button
        if imgui.button("reset"):
            # reset line properties
            self._line.colors = (1, 0, 0, 1)
            self._line.thickness = 3

            # reset the data params
            self._amplitude = 1.0
            self._sigma = 0.0

            # reset the data values for the line
            self._set_data()

    def _set_data(self):
        self._line.data[:, 1] = (np.sin(xs) * self._amplitude) + np.random.normal(scale=self._sigma, size=100)


# make GUI instance
gui = ImguiExample(
    figure,  # the figure this GUI instance should live inside
    size=275,  # width or height of the GUI window within the figure
    location="right",  # the edge to place this window at
    title="Imgui Window",  # window title
)

# add it to the figure
figure.add_gui(gui)

figure.show()


# NOTE: `if __name__ == "__main__"` is NOT how to use fastplotlib interactively
# please see our docs for using fastplotlib interactively in ipython and jupyter
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
