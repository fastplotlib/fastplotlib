import numpy as np
from numpy import testing as npt
import pytest

import pygfx

import fastplotlib as fpl
from fastplotlib.graphics._features import TextureArray, WGPU_MAX_TEXTURE_SIZE
from fastplotlib.graphics.image import _ImageTile


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

        data_row_start_index = chunk_row * WGPU_MAX_TEXTURE_SIZE
        data_col_start_index = chunk_col * WGPU_MAX_TEXTURE_SIZE

        data_row_stop_index = min(
            data.shape[0] - 1, data_row_start_index + WGPU_MAX_TEXTURE_SIZE
        )
        data_col_stop_index = min(
            data.shape[1] - 1, data_col_start_index + WGPU_MAX_TEXTURE_SIZE
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
    for (texture, chunk_index, data_slice), img in zip(texture_array, graphic.world_object.children):
        assert isinstance(img, _ImageTile)
        assert img.geometry.grid is texture
        assert img.world.x == data_slice[1].start
        assert img.world.y == data_slice[0].start


@pytest.mark.parametrize("test_graphic", [False, True])
def test_small_texture(test_graphic):
    # tests TextureArray with dims that requires only 1 texture
    data = make_data(1_000, 1_000)

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

    check_set_slice(data, ta, slice(50, 200), slice(600, 800))


@pytest.mark.parametrize("test_graphic", [False, True])
def test_texture_at_limit(test_graphic):
    # tests TextureArray with data that is 8192 x 8192
    data = make_data(WGPU_MAX_TEXTURE_SIZE, WGPU_MAX_TEXTURE_SIZE)

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

    check_set_slice(data, ta, slice(5000, 8000), slice(2000, 3000))


@pytest.mark.parametrize("test_graphic", [False, True])
def test_wide(test_graphic):
    data = make_data(10_000, 20_000)

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
        row_indices_values=np.array([0, 8192]),
        col_indices_values=np.array([0, 8192, 16384]),
    )

    if test_graphic:
        check_image_graphic(ta, graphic)

    check_set_slice(data, ta, slice(6_000, 9_000), slice(12_000, 18_000))


@pytest.mark.parametrize("test_graphic", [False, True])
def test_tall(test_graphic):
    data = make_data(20_000, 10_000)

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
        row_indices_values=np.array([0, 8192, 16384]),
        col_indices_values=np.array([0, 8192]),
    )

    if test_graphic:
        check_image_graphic(ta, graphic)

    check_set_slice(data, ta, slice(12_000, 18_000), slice(6_000, 9_000))


@pytest.mark.parametrize("test_graphic", [False, True])
def test_square(test_graphic):
    data = make_data(20_000, 20_000)

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
        row_indices_values=np.array([0, 8192, 16384]),
        col_indices_values=np.array([0, 8192, 16384]),
    )

    if test_graphic:
        check_image_graphic(ta, graphic)

    check_set_slice(data, ta, slice(12_000, 18_000), slice(16_000, 19_000))
