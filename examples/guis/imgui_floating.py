"""
ImGUI floating windows
======================

You can add floating and fixed-extent imgui windows that are overlaid on the Figure.
"""

# test_example = true
# sphinx_gallery_pygfx_docs = 'screenshot'

import numpy as np
import fastplotlib as fpl
from imgui_bundle import imgui

figure = fpl.Figure(size=(700, 560))
figure[0, 0].add_image(np.random.rand(128, 128), name="image")


# a floating window is auto-sized by imgui and can be dragged by the user
@figure.add_imgui_window(location="floating", title="floating", window_flags=imgui.WindowFlags_.none)
def floating_gui(fig):
    if imgui.button("randomize"):
        fig[0, 0]["image"].data = np.random.rand(128, 128)


# a window fixed to a fractional extent (xmin, xmax, ymin, ymax) of the canvas
@figure.add_imgui_window(extent=(0.6, 0.98, 0.05, 0.25), title="fixed")
def fixed_gui():
    imgui.text("fixed to a\nfractional extent")


figure.show()


# NOTE: fpl.loop.run() should not be used for interactive sessions
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
