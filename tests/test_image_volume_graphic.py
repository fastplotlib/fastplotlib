import numpy as np
from numpy import testing as npt
import imageio.v3 as iio

import pygfx

import fastplotlib as fpl
from fastplotlib.graphics.features import GraphicFeatureEvent
from fastplotlib.utils import make_colors


# load only first 128 planes because we set a limit for the tests
SIMPLE_IMAGE = iio.imread("imageio:stent.npz")[:128]

EVENT_RETURN_VALUE: GraphicFeatureEvent = None


def event_handler(ev):
    global EVENT_RETURN_VALUE
    EVENT_RETURN_VALUE = ev


def check_event(graphic, feature, value):
    global EVENT_RETURN_VALUE
    assert isinstance(EVENT_RETURN_VALUE, GraphicFeatureEvent)
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
    zpl_slice: slice,
):
    image_graphic.data[row_slice, col_slice, zpl_slice] = 1
    data_values = image_graphic.data.value
    npt.assert_almost_equal(data_values[row_slice, col_slice, zpl_slice], 1)

    # make sure other vals unchanged
    npt.assert_almost_equal(data_values[: row_slice.start], data[: row_slice.start])
    npt.assert_almost_equal(data_values[row_slice.stop :], data[row_slice.stop :])
    npt.assert_almost_equal(
        data_values[:, : col_slice.start], data[:, : col_slice.start]
    )
    npt.assert_almost_equal(data_values[:, col_slice.stop :], data[:, col_slice.stop :])
    npt.assert_almost_equal(data_values[:, :, : zpl_slice.start], data[:, :, : zpl_slice.start])
    npt.assert_almost_equal(data_values[:, :, zpl_slice.stop :], data[:, :, zpl_slice.stop :])

    global EVENT_RETURN_VALUE
    assert isinstance(EVENT_RETURN_VALUE, GraphicFeatureEvent)
    assert EVENT_RETURN_VALUE.type == "data"
    assert EVENT_RETURN_VALUE.graphic == image_graphic
    assert EVENT_RETURN_VALUE.target == image_graphic.world_object
    assert EVENT_RETURN_VALUE.info["key"] == (row_slice, col_slice, zpl_slice)
    npt.assert_almost_equal(EVENT_RETURN_VALUE.info["value"], 1)


def test_gray():
    fig = fpl.Figure()
    ig = fig[0, 0].add_image_volume(SIMPLE_IMAGE)
    assert isinstance(ig, fpl.ImageVolumeGraphic)

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
    npt.assert_almost_equal(ig.data.value, SIMPLE_IMAGE)

    # since this entire image is under the wgpu max texture limit,
    # the entire image should be in the single Texture buffer
    npt.assert_almost_equal(ig.data.buffer[0, 0, 0].data, SIMPLE_IMAGE)

    assert isinstance(ig._material, pygfx.VolumeMipMaterial)
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

    assert ig.interpolation == "linear"
    for child in ig.world_object.children:
        assert child.material.interpolation == "linear"

    ig.interpolation = "nearest"
    assert ig.interpolation == "nearest"
    for child in ig.world_object.children:
        assert child.material.interpolation == "nearest"
    check_event(graphic=ig, feature="interpolation", value="nearest")

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

    # make sure they all use the same material
    for child in ig.world_object.children:
        assert ig._material is child.material

    # render modes
    ig.mode = "mip"
    assert isinstance(ig._material, pygfx.VolumeMipMaterial)
    for child in ig.world_object.children:
        assert ig._material is child.material
    ig.mode = "minip"
    assert isinstance(ig._material, pygfx.VolumeMinipMaterial)
    for child in ig.world_object.children:
        assert ig._material is child.material
    ig.mode = "iso"
    assert isinstance(ig._material, pygfx.VolumeIsoMaterial)
    for child in ig.world_object.children:
        assert ig._material is child.material

    ig.threshold = 50
    assert ig._material.threshold == 50
    ig.emissive = (1, 0, 0, 1)
    assert tuple(ig._material.emissive) == (1.0, 0.0, 0.0, 1.0)
    ig.shininess = 40
    assert ig._material.shininess == 40

    ig.mode = "slice"
    assert isinstance(ig._material, pygfx.VolumeSliceMaterial)
    for child in ig.world_object.children:
        assert ig._material is child.material
    ig.plane = (0, 0.5, 0.5, -100)
    npt.assert_almost_equal(ig._material.plane, np.array([0.0, 0.5, 0.5, -100.0]))

    npt.assert_almost_equal(ig.vmin, SIMPLE_IMAGE.min())
    npt.assert_almost_equal(ig.vmax, SIMPLE_IMAGE.max())

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
    npt.assert_almost_equal(ig.vmin, SIMPLE_IMAGE.min())
    npt.assert_almost_equal(ig.vmax, SIMPLE_IMAGE.max())

    check_set_slice(SIMPLE_IMAGE, ig, slice(50, 60), slice(20, 30), slice(80, 100))

    # test setting all values
    ig.data = 1
    npt.assert_almost_equal(ig.data.value, 1)
