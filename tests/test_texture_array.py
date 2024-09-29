import numpy as np
from numpy import testing as npt
import pytest

import pygfx

import fastplotlib as fpl
from fastplotlib.graphics._features import TextureArray
from fastplotlib.graphics.image import _ImageTile


MAX_TEXTURE_SIZE = 1024


def make_data(n_rows: int, n_cols: int) -> np.ndarray:
    """
    Makes a 2D array where the amplitude of the sine wave
    is increasing along the y-direction (along rows), and
    the wavelength is increasing along the x-axis (columns)
    """
    xs = np.linspace(0, 1_000, n_cols)

    sine = np.sin(np.sqrt(xs))

    return np.vstack([sine * i for i in range(n_rows)]).astype(np.float32)


def check_texture_array(
    data: np.ndarray,
    ta: TextureArray,
    buffer_size: int,
    buffer_shape: tuple[int, int],
    row_indices_size: int,
    col_indices_size: int,
    row_indices_values: np.ndarray,
    col_indices_values: np.ndarray,
):

    npt.assert_almost_equal(ta.value, data)

    assert ta.buffer.size == buffer_size
    assert ta.buffer.shape == buffer_shape

    assert all([isinstance(texture, pygfx.Texture) for texture in ta.buffer.ravel()])

    assert ta.row_indices.size == row_indices_size
    assert ta.col_indices.size == col_indices_size
    npt.assert_array_equal(ta.row_indices, row_indices_values)
    npt.assert_array_equal(ta.col_indices, col_indices_values)

    # make sure chunking is correct
    for texture, chunk_index, data_slice in ta:
        assert ta.buffer[chunk_index] is texture
        chunk_row, chunk_col = chunk_index

        data_row_start_index = chunk_row * MAX_TEXTURE_SIZE
        data_col_start_index = chunk_col * MAX_TEXTURE_SIZE

        data_row_stop_index = min(
            data.shape[0], data_row_start_index + MAX_TEXTURE_SIZE
        )
        data_col_stop_index = min(
            data.shape[1], data_col_start_index + MAX_TEXTURE_SIZE
        )

        row_slice = slice(data_row_start_index, data_row_stop_index)
        col_slice = slice(data_col_start_index, data_col_stop_index)

        assert data_slice == (row_slice, col_slice)


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


def check_image_graphic(texture_array, graphic):
    # make sure each ImageTile has the right texture
    for (texture, chunk_index, data_slice), img in zip(
        texture_array, graphic.world_object.children
    ):
        assert isinstance(img, _ImageTile)
        assert img.geometry.grid is texture
        assert img.world.x == data_slice[1].start
        assert img.world.y == data_slice[0].start


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

    check_texture_array(
        data,
        ta=ta,
        buffer_size=6,
        buffer_shape=(2, 3),
        row_indices_size=2,
        col_indices_size=3,
        row_indices_values=np.array([0, MAX_TEXTURE_SIZE]),
        col_indices_values=np.array([0, MAX_TEXTURE_SIZE, 2 * MAX_TEXTURE_SIZE]),
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

    check_texture_array(
        data,
        ta=ta,
        buffer_size=6,
        buffer_shape=(3, 2),
        row_indices_size=3,
        col_indices_size=2,
        row_indices_values=np.array([0, MAX_TEXTURE_SIZE, 2 * MAX_TEXTURE_SIZE]),
        col_indices_values=np.array([0, MAX_TEXTURE_SIZE]),
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

    check_texture_array(
        data,
        ta=ta,
        buffer_size=9,
        buffer_shape=(3, 3),
        row_indices_size=3,
        col_indices_size=3,
        row_indices_values=np.array([0, MAX_TEXTURE_SIZE, 2 * MAX_TEXTURE_SIZE]),
        col_indices_values=np.array([0, MAX_TEXTURE_SIZE, 2 * MAX_TEXTURE_SIZE]),
    )

    if test_graphic:
        check_image_graphic(ta, graphic)

    check_set_slice(data, ta, slice(100, 2_100), slice(100, 2_100))
