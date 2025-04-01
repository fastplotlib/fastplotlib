"""
ipwidgets modify an ImageGraphic
================================

Use ipywidgets to modify some features of an ImageGraphic. Run in jupyterlab.
"""

# test_example = false
# sphinx_gallery_pygfx_docs = 'code'

import fastplotlib as fpl
from scipy.ndimage import gaussian_filter
import imageio.v3 as iio
from ipywidgets import FloatRangeSlider, FloatSlider, Select, VBox

data = iio.imread("imageio:moon.png")

iw = fpl.ImageWidget(data, figure_kwargs={"size": (700, 560)})

# get the ImageGraphic from the image widget
image = iw.managed_graphics[0]

min_v, max_v = fpl.utils.quick_min_max(data)

# slider to adjust vmin, vmax of the image
vmin_vmax_slider = FloatRangeSlider(value=(image.vmin, image.vmax), min=min_v, max=max_v, description="vmin, vmax:")

# slider to adjust sigma of a gaussian kernel used to filter the image (i.e. gaussian blur)
slider_sigma = FloatSlider(min=0.0, max=10.0, value=0.0, description="σ: ")

# select box to choose the sample image shown in the ImageWidget
select_image = Select(options=["moon.png", "camera.png", "checkerboard.png"], description="image: ")


def update_vmin_vmax(change):
    vmin, vmax = change["new"]

    image = iw.managed_graphics[0]
    image.vmin, image.vmax = vmin, vmax


def update_sigma(change):
    sigma = change["new"]

    # set a "frame apply" dict onto the ImageWidget
    # this maps {image_index: function}
    # the function is applied to the image data at the image index given by the key
    iw.frame_apply = {0: lambda image_data: gaussian_filter(image_data, sigma=sigma)}


def update_image(change):
    filename = change["new"]
    data = iio.imread(f"imageio:{filename}")

    iw.set_data(data)

    # set vmin, vmax sliders w.r.t. this new image
    image = iw.managed_graphics[0]
    vmin_vmax_slider.value = image.vmin, image.vmax
    vmin_vmax_slider.min, vmin_vmax_slider.max = fpl.utils.quick_min_max(data)


# connect the ipywidgets to the handler functions
vmin_vmax_slider.observe(update_vmin_vmax, "value")
slider_sigma.observe(update_sigma, "value")
select_image.observe(update_image, "value")

# display in a vbox
VBox([iw.show(), vmin_vmax_slider, slider_sigma, select_image])
