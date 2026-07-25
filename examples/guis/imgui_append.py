"""
ImGUI append to windows
=======================

You can append imgui elements to an existing window, including the subplot toolbar.
"""

# test_example = false
# sphinx_gallery_pygfx_docs = 'screenshot'

import numpy as np
import fastplotlib as fpl
from imgui_bundle import imgui, icons_fontawesome_6 as fa

figure = fpl.Figure(size=(700, 560))
figure[0, 0].add_line(np.random.rand(100), colors="r", name="line")


# create an edge window
@figure.add_imgui_window(location="right", size=200, title="controls")
def gui(fig):
    if imgui.button("randomize"):
        fig[0, 0]["line"].data[:, 1] = np.random.rand(100)


# append more elements to the same window
@figure.append_imgui_window(location="right")
def more(fig):
    line = fig[0, 0]["line"]
    _, line.thickness = imgui.slider_float("thickness", v=line.thickness, v_min=2.0, v_max=50.0)


# append a button to the subplot toolbar that toggles axes visibility
@figure[0, 0].append_imgui_window(location="toolbar")
def toolbar_extra(subplot):
    imgui.same_line()
    _, subplot.axes.visible = imgui.checkbox(fa.ICON_FA_RULER_COMBINED, subplot.axes.visible)
    if imgui.is_item_hovered(0):
        imgui.set_tooltip("Axes visibility")


figure.show(maintain_aspect=False)


# NOTE: fpl.loop.run() should not be used for interactive sessions
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
