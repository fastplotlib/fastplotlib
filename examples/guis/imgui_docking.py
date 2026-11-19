"""
ImGUI docking
=============

Dock the Figure edge windows: drag a window by its tab to another edge, onto another window to tab them
together, or away from the edges to float it. The plots fill the space the windows leave.
"""

# test_example = false
# sphinx_gallery_pygfx_docs = 'screenshot'

import numpy as np
import fastplotlib as fpl
from imgui_bundle import imgui

figure = fpl.Figure(shape=(1, 2), size=(1000, 700))
figure[0, 0].add_image(np.random.rand(128, 128), cmap="viridis", name="image")
figure[0, 1].add_line(np.sin(np.linspace(0, 4 * np.pi, 100)), colors="magenta", name="line")

# turn docking on before adding the windows, a window added to an edge that already has one docks as a tab
figure.imgui_docking = True


# left edge: pick the image colormap
@figure.add_imgui_window(location="left", size=130, title="cmap")
def cmap_gui():
    image = figure[0, 0]["image"]
    for name in ["bids:viridis", "bids:plasma", "matlab:gray", "bids:magma", "google:turbo"]:
        if imgui.radio_button(name, image.cmap.name == name):
            image.cmap = name


# right edge: image contrast
@figure.add_imgui_window(location="right", size=260, title="contrast")
def contrast_gui():
    image = figure[0, 0]["image"]
    _, image.gamma = imgui.slider_float("gamma", image.gamma, 0.1, 5.0)
    changed, vals = imgui.slider_float2("vmin / vmax", (image.vmin, image.vmax), 0.0, 1.0)
    if changed:
        image.vmin, image.vmax = vals[0], vals[1]


# right edge again: docks as a second tab beside "contrast"
@figure.add_imgui_window(location="right", size=260, title="line")
def line_gui():
    line = figure[0, 1]["line"]
    _, line.thickness = imgui.slider_float("thickness", line.thickness, 1.0, 20.0)
    changed, color = imgui.color_edit3("color", tuple(float(c) for c in line.colors)[:3])
    if changed:
        line.colors = (*color, 1.0)
    if imgui.button("randomize"):
        line.data[:, 1] = np.random.rand(100)


# bottom edge: a live preview of the line data
@figure.add_imgui_window(location="bottom", size=100, title="preview")
def preview_gui():
    ys = np.ascontiguousarray(figure[0, 1]["line"].data[:, 1], dtype=np.float32)
    imgui.plot_lines("##preview", ys, graph_size=imgui.ImVec2(0, 50))


figure.show()


# NOTE: fpl.loop.run() should not be used for interactive sessions
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
