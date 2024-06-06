import numpy as np
from numpy import testing as npt
import imageio.v3 as iio

import fastplotlib as fpl
from fastplotlib.utils import make_colors

GRAY_IMAGE = iio.imread("imageio:camera.png")
RGB_IMAGE = iio.imread("imageio:astronaut.png")


COFFEE_IMAGE = iio.imread("imageio:coffee.png")

# image cmap, vmin, vmax, interpolations
# new screenshot tests too for these when in graphics


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
    npt.assert_almost_equal(data_values[:row_slice.start], data[:row_slice.start])
    npt.assert_almost_equal(data_values[row_slice.stop:], data[row_slice.stop:])
    npt.assert_almost_equal(data_values[:, :col_slice.start], data[:, :col_slice.start])
    npt.assert_almost_equal(data_values[:, col_slice.stop:], data[:, col_slice.stop:])


def test_gray():
    fig = fpl.Figure()
    ig = fig[0, 0].add_image(GRAY_IMAGE)
    assert isinstance(ig, fpl.ImageGraphic)

    npt.assert_almost_equal(ig.data.value, GRAY_IMAGE)

    ig.cmap = "viridis"
    assert ig.cmap == "viridis"

    new_colors = make_colors(256, "viridis")
    for child in ig.world_object.children:
        npt.assert_almost_equal(child.material.map.data, new_colors)

    ig.cmap = "jet"
    assert ig.cmap == "jet"

    new_colors = make_colors(256, "jet")
    for child in ig.world_object.children:
        npt.assert_almost_equal(child.material.map.data, new_colors)

    assert ig.interpolation == "nearest"
    for child in ig.world_object.children:
        assert child.material.interpolation == "nearest"

    ig.interpolation = "linear"
    assert ig.interpolation == "linear"
    for child in ig.world_object.children:
        assert child.material.interpolation == "linear"

    assert ig.cmap_interpolation == "linear"
    for child in ig.world_object.children:
        assert child.material.map_interpolation == "linear"

    ig.cmap_interpolation = "nearest"
    assert ig.cmap_interpolation == "nearest"
    for child in ig.world_object.children:
        assert child.material.map_interpolation == "nearest"

    npt.assert_almost_equal(ig.vmin, GRAY_IMAGE.min())
    npt.assert_almost_equal(ig.vmax, GRAY_IMAGE.max())

    ig.vmin = 50
    assert ig.vmin == 50
    for child in ig.world_object.children:
        assert child.material.clim == (50, ig.vmax)

    ig.vmax = 100
    assert ig.vmax == 100
    for child in ig.world_object.children:
        assert child.material.clim == (ig.vmin, 100)

    check_set_slice(GRAY_IMAGE, ig, slice(100, 200), slice(200, 300))

    # test setting all values
    ig.data = 1
    npt.assert_almost_equal(ig.data.value, 1)


def test_rgb():
    fig = fpl.Figure()
    ig = fig[0, 0].add_image(RGB_IMAGE)
    assert isinstance(ig, fpl.ImageGraphic)

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

    check_set_slice(RGB_IMAGE, ig, slice(100, 200), slice(200, 300))


def test_rgba():
    rgba = np.zeros(shape=(*COFFEE_IMAGE.shape[:2], 4), dtype=np.float32)

    fig = fpl.Figure()
    ig = fig[0, 0].add_image(rgba)
    assert isinstance(ig, fpl.ImageGraphic)

    npt.assert_almost_equal(ig.data.value, rgba)

    # fancy indexing
    # set the blue values of some pixels with an alpha > 1
    ig.data[COFFEE_IMAGE[:, :, -1] > 200] = np.array([0.0, 0.0, 1.0, 0.6]).astype(np.float32)

    rgba[COFFEE_IMAGE[:, :, -1] > 200] = np.array([0.0, 0.0, 1.0, 0.6]).astype(np.float32)

    # check that fancy indexing works
    npt.assert_almost_equal(ig.data.value, rgba)
