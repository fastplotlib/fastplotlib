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

figure = fpl.Figure()
figure[0, 0].add_line(np.random.rand(100))


@figure.add_gui(location="right", title="yay", size=100)
def gui():
    if imgui.button("reset data"):
        figure[0, 0].graphics[0].data[:, 1] = np.random.rand(100)


figure.show(maintain_aspect=False)

fpl.loop.run()
