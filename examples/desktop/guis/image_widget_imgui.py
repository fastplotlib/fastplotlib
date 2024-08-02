"""
ImGUI with Image widget
=======================

Example showing how to write a custom GUI with imgui and use it with ImageWidget
"""

# test_example = true
# sphinx_gallery_pygfx_docs = 'screenshot'

# some simple image processing functions
from scipy.ndimage import gaussian_filter
import imageio.v3 as iio

import fastplotlib as fpl

# subclass from EdgeWindow to make a custom ImGUI Window to place inside the figure!
from fastplotlib.ui import EdgeWindow
from imgui_bundle import imgui

a = iio.imread("imageio:camera.png")
iw = fpl.ImageWidget(data=a, cmap="viridis", figure_kwargs={"size": (700, 560)})
iw.show()


# GUI for some basic image processing
class ImageProcessingWindow(EdgeWindow):
    def __init__(self, figure, size):
        super().__init__(figure=figure, size=size)

        self.sigma = 0.0
        self.order_x, self.order_y = 0, 0

    def update(self):
        # implement the GUI within the update function
        # you do not need to call imgui.new_frame(), this is handled by Figure

        width_canvas, height_canvas = self._figure.canvas.get_logical_size()

        # we will put this GUI on the right side of the canvas
        x_position = width_canvas - self.size
        pos = (x_position, 0)

        if self._figure.guis["bottom"]:
            height_canvas -= self._figure.guis["bottom"].size

        imgui.set_next_window_size((self.size, height_canvas))
        imgui.set_next_window_pos(pos)
        flags = imgui.WindowFlags_.no_collapse

        # make the GUI, nothing special here, just regular imgui
        imgui.begin("Image processing controls", p_open=None, flags=flags)

        imgui.push_id(
            self._id_counter
        )  # push ID to prevent conflict between multiple figs with same UI

        something_changed = False

        # slider for gaussian filter sigma value
        changed, value = imgui.slider_float(label="sigma", v=self.sigma, v_min=0.0, v_max=20.0)
        if changed:
            self.sigma = value
            something_changed = True

        # int entries for gaussian filter order
        for axis in ["x", "y"]:
            changed, value = imgui.input_int(f"order {axis}", v=getattr(self, f"order_{axis}"))
            if changed:
                if value < 0:
                    value = 0
                setattr(self, f"order_{axis}", value)
                something_changed = True

        if something_changed:
            self.process_image()

        imgui.pop_id()

        # end any windows/popups
        imgui.end()

        # do not call imgui.end_frame(), this is handled by Figure

    def process_image(self):
        processed = gaussian_filter(a, sigma=self.sigma, order=(self.order_y, self.order_x))
        iw.set_data(processed)


gui = ImageProcessingWindow(iw.figure, size=200)


iw.figure.set_gui(edge="right", gui=gui)

figure = iw.figure


# NOTE: `if __name__ == "__main__"` is NOT how to use fastplotlib interactively
# please see our docs for using fastplotlib interactively in ipython and jupyter
if __name__ == "__main__":
    print(__doc__)
    fpl.run()
