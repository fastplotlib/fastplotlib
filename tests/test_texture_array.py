import numpy as np
from numpy import testing as npt
import pytest

import fastplotlib as fpl
from fastplotlib.graphics.features import TextureArray
from .utils_textures import MAX_TEXTURE_SIZE, check_texture_array, check_image_graphic


def make_data(n_rows: int, n_cols: int) -> np.ndarray:
    """
    Makes a 2D array where the amplitude of the sine wave
    is increasing along the y-direction (along rows), and
    the wavelength is increasing along the x-axis (columns)
    """
    xs = np.linspace(0, 1_000, n_cols)

    sine = np.sin(np.sqrt(xs))

    return np.vstack([sine * i for i in range(n_rows)]).astype(np.float32)


def check_set_slice(data, ta, row_slice, col_slice):
    ta[row_slice, col_slice] = 1
    npt.assert_almost_equal(ta[row_slice, col_slice], 1)

    # make sure other vals unchanged
    npt.assert_almost_equal(ta[: row_slice.start], data[: row_slice.start])
    npt.assert_almost_equal(ta[row_slice.stop :], data[row_slice.stop :])
    npt.assert_almost_equal(ta[:, : col_slice.start], data[:, : col_slice.start])
    npt.assert_almost_equal(ta[:, col_slice.stop :], data[:, col_slice.stop :])


def make_image_graphic(data) -> fpl.ImageGraphic:
    fig = fpl.Figure()
    return fig[0, 0].add_image(data)


@pytest.mark.parametrize("test_graphic", [False, True])
def test_small_texture(test_graphic):
    # tests TextureArray with dims that requires only 1 texture
    data = make_data(500, 500)

    if test_graphic:
        graphic = make_image_graphic(data)
        ta = graphic.data
    else:
        ta = TextureArray(data)

    check_texture_array(
        data=data,
        ta=ta,
        buffer_size=1,
        buffer_shape=(1, 1),
        row_indices_size=1,
        col_indices_size=1,
        row_indices_values=np.array([0]),
        col_indices_values=np.array([0]),
    )

    if test_graphic:
        check_image_graphic(ta, graphic)

    check_set_slice(data, ta, slice(50, 200), slice(200, 400))


@pytest.mark.parametrize("test_graphic", [False, True])
def test_texture_at_limit(test_graphic):
    # tests TextureArray with data that is 1024 x 1024
    data = make_data(MAX_TEXTURE_SIZE, MAX_TEXTURE_SIZE)

    if test_graphic:
        graphic = make_image_graphic(data)
        ta = graphic.data
    else:
        ta = TextureArray(data)

    check_texture_array(
        data,
        ta=ta,
        buffer_size=1,
        buffer_shape=(1, 1),
        row_indices_size=1,
        col_indices_size=1,
        row_indices_values=np.array([0]),
        col_indices_values=np.array([0]),
    )

    if test_graphic:
        check_image_graphic(ta, graphic)

    check_set_slice(data, ta, slice(500, 800), slice(200, 300))


@pytest.mark.parametrize("test_graphic", [False, True])
def test_wide(test_graphic):
    data = make_data(1_200, 2_200)

    if test_graphic:
        graphic = make_image_graphic(data)
        ta = graphic.data
    else:
        ta = TextureArray(data)

    ta_shape = (2, 3)

    check_texture_array(
        data,
        ta=ta,
        buffer_size=np.prod(ta_shape),
        buffer_shape=ta_shape,
        row_indices_size=ta_shape[0],
        col_indices_size=ta_shape[1],
        row_indices_values=np.array(
            [
                i * MAX_TEXTURE_SIZE
                for i in range(0, 1 + (data.shape[0] - 1) // MAX_TEXTURE_SIZE)
            ]
        ),
        col_indices_values=np.array(
            [
                i * MAX_TEXTURE_SIZE
                for i in range(0, 1 + (data.shape[1] - 1) // MAX_TEXTURE_SIZE)
            ]
        ),
    )

    if test_graphic:
        check_image_graphic(ta, graphic)

    check_set_slice(data, ta, slice(600, 1_100), slice(100, 2_100))


@pytest.mark.parametrize("test_graphic", [False, True])
def test_tall(test_graphic):
    data = make_data(2_200, 1_200)

    if test_graphic:
        graphic = make_image_graphic(data)
        ta = graphic.data
    else:
        ta = TextureArray(data)

    ta_shape = (3, 2)

    check_texture_array(
        data,
        ta=ta,
        buffer_size=np.prod(ta_shape),
        buffer_shape=ta_shape,
        row_indices_size=ta_shape[0],
        col_indices_size=ta_shape[1],
        row_indices_values=np.array(
            [
                i * MAX_TEXTURE_SIZE
                for i in range(0, 1 + (data.shape[0] - 1) // MAX_TEXTURE_SIZE)
            ]
        ),
        col_indices_values=np.array(
            [
                i * MAX_TEXTURE_SIZE
                for i in range(0, 1 + (data.shape[1] - 1) // MAX_TEXTURE_SIZE)
            ]
        ),
    )

    if test_graphic:
        check_image_graphic(ta, graphic)

    check_set_slice(data, ta, slice(100, 2_100), slice(600, 1_100))


@pytest.mark.parametrize("test_graphic", [False, True])
def test_square(test_graphic):
    data = make_data(2_200, 2_200)

    if test_graphic:
        graphic = make_image_graphic(data)
        ta = graphic.data
    else:
        ta = TextureArray(data)

    ta_shape = (3, 3)

    check_texture_array(
        data,
        ta=ta,
        buffer_size=np.prod(ta_shape),
        buffer_shape=ta_shape,
        row_indices_size=ta_shape[0],
        col_indices_size=ta_shape[1],
        row_indices_values=np.array(
            [
                i * MAX_TEXTURE_SIZE
                for i in range(0, 1 + (data.shape[0] - 1) // MAX_TEXTURE_SIZE)
            ]
        ),
        col_indices_values=np.array(
            [
                i * MAX_TEXTURE_SIZE
                for i in range(0, 1 + (data.shape[1] - 1) // MAX_TEXTURE_SIZE)
            ]
        ),
    )

    if test_graphic:
        check_image_graphic(ta, graphic)

    check_set_slice(data, ta, slice(100, 2_100), slice(100, 2_100))
