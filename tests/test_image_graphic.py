import numpy as np
from numpy import testing as npt
import imageio.v3 as iio

import pygfx

import fastplotlib as fpl
from fastplotlib.graphics._features import FeatureEvent
from fastplotlib.utils import make_colors

GRAY_IMAGE = iio.imread("imageio:camera.png")
RGB_IMAGE = iio.imread("imageio:astronaut.png")


COFFEE_IMAGE = iio.imread("imageio:coffee.png")

# image cmap, vmin, vmax, interpolations
# new screenshot tests too for these when in graphics


EVENT_RETURN_VALUE: FeatureEvent = None


def event_handler(ev):
    global EVENT_RETURN_VALUE
    EVENT_RETURN_VALUE = ev


def check_event(graphic, feature, value):
    global EVENT_RETURN_VALUE
    assert isinstance(EVENT_RETURN_VALUE, FeatureEvent)
    assert EVENT_RETURN_VALUE.type == feature
    assert EVENT_RETURN_VALUE.graphic == graphic
    assert EVENT_RETURN_VALUE.target == graphic.world_object
    if isinstance(EVENT_RETURN_VALUE.info["value"], float):
        # floating point error
        npt.assert_almost_equal(EVENT_RETURN_VALUE.info["value"], value)
    else:
        assert EVENT_RETURN_VALUE.info["value"] == value


def check_set_slice(
    data: np.ndarray,
    image_graphic: fpl.ImageGraphic,
    row_slice: slice,
    col_slice: slice,
):
    image_graphic.data[row_slice, col_slice] = 1
    data_values = image_graphic.data.value
    npt.assert_almost_equal(data_values[row_slice, col_slice], 1)

    # make sure other vals unchanged
    npt.assert_almost_equal(data_values[: row_slice.start], data[: row_slice.start])
    npt.assert_almost_equal(data_values[row_slice.stop :], data[row_slice.stop :])
    npt.assert_almost_equal(
        data_values[:, : col_slice.start], data[:, : col_slice.start]
    )
    npt.assert_almost_equal(data_values[:, col_slice.stop :], data[:, col_slice.stop :])

    global EVENT_RETURN_VALUE
    assert isinstance(EVENT_RETURN_VALUE, FeatureEvent)
    assert EVENT_RETURN_VALUE.type == "data"
    assert EVENT_RETURN_VALUE.graphic == image_graphic
    assert EVENT_RETURN_VALUE.target == image_graphic.world_object
    assert EVENT_RETURN_VALUE.info["key"] == (row_slice, col_slice)
    npt.assert_almost_equal(EVENT_RETURN_VALUE.info["value"], 1)


def test_gray():
    fig = fpl.Figure()
    ig = fig[0, 0].add_image(GRAY_IMAGE)
    assert isinstance(ig, fpl.ImageGraphic)

    ig.add_event_handler(
        event_handler,
        "data",
        "cmap",
        "vmin",
        "vmax",
        "interpolation",
        "cmap_interpolation",
    )

    # make sure entire data is the same
    npt.assert_almost_equal(ig.data.value, GRAY_IMAGE)

    # since this entire image is under the wgpu max texture limit,
    # the entire image should be in the single Texture buffer
    npt.assert_almost_equal(ig.data.buffer[0, 0].data, GRAY_IMAGE)

    assert isinstance(ig._material, pygfx.ImageBasicMaterial)
    assert isinstance(ig._material.map, pygfx.TextureMap)
    assert isinstance(ig._material.map.texture, pygfx.Texture)

    ig.cmap = "viridis"
    assert ig.cmap == "viridis"
    check_event(graphic=ig, feature="cmap", value="viridis")

    new_colors = make_colors(256, "viridis")
    for child in ig.world_object.children:
        npt.assert_almost_equal(child.material.map.texture.data, new_colors)

    ig.cmap = "jet"
    assert ig.cmap == "jet"

    new_colors = make_colors(256, "jet")
    for child in ig.world_object.children:
        npt.assert_almost_equal(child.material.map.texture.data, new_colors)

    assert ig.interpolation == "nearest"
    for child in ig.world_object.children:
        assert child.material.interpolation == "nearest"

    ig.interpolation = "linear"
    assert ig.interpolation == "linear"
    for child in ig.world_object.children:
        assert child.material.interpolation == "linear"
    check_event(graphic=ig, feature="interpolation", value="linear")

    assert ig.cmap_interpolation == "linear"
    for child in ig.world_object.children:
        assert child.material.map.min_filter == "linear"
        assert child.material.map.mag_filter == "linear"

    ig.cmap_interpolation = "nearest"
    assert ig.cmap_interpolation == "nearest"
    for child in ig.world_object.children:
        assert child.material.map.min_filter == "nearest"
        assert child.material.map.mag_filter == "nearest"

    check_event(graphic=ig, feature="cmap_interpolation", value="nearest")

    npt.assert_almost_equal(ig.vmin, GRAY_IMAGE.min())
    npt.assert_almost_equal(ig.vmax, GRAY_IMAGE.max())

    ig.vmin = 50
    assert ig.vmin == 50
    for child in ig.world_object.children:
        assert child.material.clim == (50, ig.vmax)
    check_event(graphic=ig, feature="vmin", value=50)

    ig.vmax = 100
    assert ig.vmax == 100
    for child in ig.world_object.children:
        assert child.material.clim == (ig.vmin, 100)
    check_event(graphic=ig, feature="vmax", value=100)

    # test reset
    ig.reset_vmin_vmax()
    npt.assert_almost_equal(ig.vmin, GRAY_IMAGE.min())
    npt.assert_almost_equal(ig.vmax, GRAY_IMAGE.max())

    check_set_slice(GRAY_IMAGE, ig, slice(100, 200), slice(200, 300))

    # test setting all values
    ig.data = 1
    npt.assert_almost_equal(ig.data.value, 1)


def test_rgb():
    fig = fpl.Figure()
    ig = fig[0, 0].add_image(RGB_IMAGE)
    assert isinstance(ig, fpl.ImageGraphic)

    ig.add_event_handler(event_handler, "data")

    npt.assert_almost_equal(ig.data.value, RGB_IMAGE)

    assert ig.interpolation == "nearest"
    for child in ig.world_object.children:
        assert child.material.interpolation == "nearest"

    ig.interpolation = "linear"
    assert ig.interpolation == "linear"
    for child in ig.world_object.children:
        assert child.material.interpolation == "linear"

    npt.assert_almost_equal(ig.vmin, RGB_IMAGE.min())
    npt.assert_almost_equal(ig.vmax, RGB_IMAGE.max())

    ig.vmin = 50
    assert ig.vmin == 50
    for child in ig.world_object.children:
        assert child.material.clim == (50, ig.vmax)

    ig.vmax = 100
    assert ig.vmax == 100
    for child in ig.world_object.children:
        assert child.material.clim == (ig.vmin, 100)

    # test reset
    ig.reset_vmin_vmax()
    npt.assert_almost_equal(ig.vmin, RGB_IMAGE.min())
    npt.assert_almost_equal(ig.vmax, RGB_IMAGE.max())

    check_set_slice(RGB_IMAGE, ig, slice(100, 200), slice(200, 300))


def test_rgba():
    rgba = np.zeros(shape=(*COFFEE_IMAGE.shape[:2], 4), dtype=np.float32)

    fig = fpl.Figure()
    ig = fig[0, 0].add_image(rgba)
    assert isinstance(ig, fpl.ImageGraphic)

    npt.assert_almost_equal(ig.data.value, rgba)

    # fancy indexing
    # set the blue values of some pixels with an alpha > 1
    ig.data[COFFEE_IMAGE[:, :, -1] > 200] = np.array([0.0, 0.0, 1.0, 0.6]).astype(
        np.float32
    )

    rgba[COFFEE_IMAGE[:, :, -1] > 200] = np.array([0.0, 0.0, 1.0, 0.6]).astype(
        np.float32
    )

    # check that fancy indexing works
    npt.assert_almost_equal(ig.data.value, rgba)
