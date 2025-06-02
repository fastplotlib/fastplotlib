"""
ImGUI Decorator
===============

Create imgui UIs quickly using a decorator!

See the imgui docs for extensive examples on how to create all UI elements: https://pyimgui.readthedocs.io/en/latest/reference/imgui.core.html#imgui.core.begin_combo
"""

# test_example = true
# sphinx_gallery_pygfx_docs = 'screenshot'


import numpy as np
import fastplotlib as fpl
from imgui_bundle import imgui

figure = fpl.Figure(size=(700, 560))
figure[0, 0].add_line(np.random.rand(100))


@figure.add_gui(location="right", title="window", size=200)
def gui(fig_local):  # figure is the only argument, so you can use it within the local scope of the GUI function
    if imgui.button("reset data"):
        fig_local[0, 0].graphics[0].data[:, 1] = np.random.rand(100)


figure.show(maintain_aspect=False)

# NOTE: fpl.loop.run() should not be used for interactive sessions
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
