"""
ImGUI right-click popups
========================

You can set an imgui popup that is opened by a right-click on a Figure, Subplot or Graphic.
"""

# test_example = false
# sphinx_gallery_pygfx_docs = 'screenshot'

import numpy as np
import imageio.v3 as iio
from scipy.ndimage import gaussian_filter
import fastplotlib as fpl
from imgui_bundle import imgui

data1 = iio.imread("imageio:camera.png").astype(np.float32)
data2 = iio.imread("imageio:moon.png").astype(np.float32)

figure = fpl.Figure(shape=(1, 2), size=(900, 560), names=["images", "line"])

# the popup keeps its state in the graphic's metadata, so one function can be used for both images
state = {"noise": 0.0, "sigma": 1.0, "filter": False}

img1 = figure[0, 0].add_image(data1, name="img1", metadata=state.copy())
img2 = figure[0, 0].add_image(data2, name="img2", offset=(550, 0, 0), metadata=state.copy())

line = figure[0, 1].add_line(np.sin(np.linspace(0, 4 * np.pi, 100)), name="line")

raw = {img1: data1, img2: data2}


# append elements to the standard right-click menu
@figure.append_imgui_right_click()
def more_items(fig):
    imgui.separator()
    if imgui.menu_item("Autoscale all subplots", "", False)[0]:
        for subplot in fig:
            subplot.auto_scale()


# a popup set on a subplot replaces the standard menu within that subplot
@figure[0, 1].set_imgui_right_click()
def line_popup(subplot):
    imgui.text(f"subplot: {subplot.name}")
    imgui.separator()
    _, line.thickness = imgui.slider_float("thickness", line.thickness, 1.0, 20.0)
    changed, color = imgui.color_edit3("color", tuple(float(c) for c in line.colors)[:3])
    if changed:
        line.colors = (*color, 1.0)


# a popup can contain any imgui elements, it is not restricted to menu items
def image_processing(image):
    ui = image.metadata

    imgui.text(image.name)
    imgui.separator()

    changed_noise, ui["noise"] = imgui.slider_float("noise sigma", ui["noise"], 0.0, 100.0)
    changed_filter, ui["filter"] = imgui.checkbox("gaussian filter", ui["filter"])

    imgui.begin_disabled(not ui["filter"])
    changed_sigma, ui["sigma"] = imgui.slider_float("filter sigma", ui["sigma"], 0.1, 10.0)
    imgui.end_disabled()

    if imgui.button("reset"):
        ui.update(noise=0.0, sigma=1.0, filter=False)
        changed_noise = True

    if changed_noise or changed_filter or changed_sigma:
        data = raw[image] + np.random.normal(scale=ui["noise"], size=raw[image].shape)

        if ui["filter"]:
            data = gaussian_filter(data, sigma=ui["sigma"])

        image.data = data


# the same function on both images, each graphic gets its own popup and is passed to the function
img1.set_imgui_right_click(image_processing)
img2.set_imgui_right_click(image_processing)

figure.show()
figure[0, 1].camera.maintain_aspect = False

# NOTE: fpl.loop.run() should not be used for interactive sessions
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
