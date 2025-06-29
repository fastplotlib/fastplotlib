"""
ImGUI Decorator
===============

Create imgui UIs quickly using a decorator!

See the imgui docs for extensive examples on how to create all UI elements: https://pyimgui.readthedocs.io/en/latest/reference/imgui.core.html#imgui.core.begin_combo
"""

# test_example = true
# sphinx_gallery_pygfx_docs = 'screenshot'


import numpy as np
import imageio.v3 as iio
import fastplotlib as fpl
from imgui_bundle import imgui

img_data = iio.imread(f"imageio:camera.png").astype(np.float32)

xs = np.linspace(0, 2 * np.pi, 100)
ys = np.sin(xs)
line_data = np.column_stack([xs, ys])

figure = fpl.Figure(shape=(2, 1), size=(700, 660))
figure[0, 0].add_image(img_data, name="image")
figure[1, 0].add_line(line_data, name="sine")

noise_sigma = 0.0

img_options = ["camera.png", "astronaut.png", "chelsea.png"]
img_index = 0
@figure.add_gui(location="right", title="window", size=300)
def gui(fig_local):  # figure is the only argument, so you can use it within the local scope of the GUI function
    global img_data
    global img_index

    global noise_sigma


    clicked, img_index = imgui.combo("image", img_index, img_options)
    if clicked:
        fig_local[0, 0].delete_graphic(fig_local[0, 0]["image"])
        img_data = iio.imread(f"imageio:{img_options[img_index]}")
        fig_local[0, 0].add_image(img_data, name="image")

    change, noise_sigma = imgui.slider_float("noise sigma", v=noise_sigma, v_min=0.0, v_max=100)
    if change or clicked:
        fig_local[0, 0]["image"].data = img_data + np.random.normal(
            loc=0.0,
            scale=noise_sigma,
            size=img_data.size
        ).reshape(img_data.shape)


# You can put all the GUI elements within on GUI function
# or split them across multiple functions and use the `append_gui` decorator
freq = 1.0
@figure.append_gui(location="right")
def gui2(fig_local):
    global freq
    change, freq = imgui.slider_float("freq", v=freq, v_min=0.1, v_max=10)
    if change:
        ys = np.sin(xs * freq)
        fig_local[1, 0]["sine"].data[:, 1] = ys


figure.show()
figure[1, 0].camera.maintain_aspect = False

# NOTE: fpl.loop.run() should not be used for interactive sessions
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
