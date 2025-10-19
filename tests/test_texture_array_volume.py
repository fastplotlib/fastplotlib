import numpy as np
from numpy import testing as npt
import pytest

import pygfx

import fastplotlib as fpl
from fastplotlib.graphics.features import TextureArrayVolume
from fastplotlib.graphics.image_volume import _VolumeTile


MAX_TEXTURE_SIZE_3D = 128


def make_data(z: int, n_rows: int, n_cols: int) -> np.ndarray:
    """
    Makes a 2D array where the amplitude of the sine wave
    is increasing along the y-direction (along rows), and
    the wavelength is increasing along the x-axis (columns)
    """
    xs = np.linspace(0, 100, n_cols)

    sine = np.sin(np.sqrt(xs))

    data = np.dstack(
        [
            np.column_stack([sine * i for i in range(n_rows)]).astype(np.float32) * j
            for j in range(z)
        ]
    )

    return data.T


def check_texture_array(
    data: np.ndarray,
    ta: TextureArrayVolume,
    buffer_size: int,
    buffer_shape: tuple[int, int, int],
    zdim_indices_size: int,
    row_indices_size: int,
    col_indices_size: int,
    zdim_indices_values: np.ndarray,
    row_indices_values: np.ndarray,
    col_indices_values: np.ndarray,
):

    npt.assert_almost_equal(ta.value, data)

    assert ta.buffer.size == buffer_size
    assert ta.buffer.shape == buffer_shape

    assert all([isinstance(texture, pygfx.Texture) for texture in ta.buffer.ravel()])

    assert ta.zdim_indices.size == zdim_indices_size
    assert ta.row_indices.size == row_indices_size
    assert ta.col_indices.size == col_indices_size

    npt.assert_array_equal(ta.zdim_indices, zdim_indices_values)
    npt.assert_array_equal(ta.row_indices, row_indices_values)
    npt.assert_array_equal(ta.col_indices, col_indices_values)

    # make sure chunking is correct
    for texture, chunk_index, data_slice in ta:
        assert ta.buffer[chunk_index] is texture
        chunk_z, chunk_row, chunk_col = chunk_index

        data_z_start_index = chunk_z * MAX_TEXTURE_SIZE_3D
        data_row_start_index = chunk_row * MAX_TEXTURE_SIZE_3D
        data_col_start_index = chunk_col * MAX_TEXTURE_SIZE_3D

        data_z_stop_index = min(data.shape[0], data_z_start_index + MAX_TEXTURE_SIZE_3D)

        data_row_stop_index = min(
            data.shape[1], data_row_start_index + MAX_TEXTURE_SIZE_3D
        )
        data_col_stop_index = min(
            data.shape[2], data_col_start_index + MAX_TEXTURE_SIZE_3D
        )

        zdim_slice = slice(data_z_start_index, data_z_stop_index)
        row_slice = slice(data_row_start_index, data_row_stop_index)
        col_slice = slice(data_col_start_index, data_col_stop_index)

        assert data_slice == (zdim_slice, row_slice, col_slice)


def check_set_slice(data, ta, zdim_slice, row_slice, col_slice):
    ta[zdim_slice, row_slice, col_slice] = 1
    npt.assert_almost_equal(ta[zdim_slice, row_slice, col_slice], 1)

    # make sure other vals unchanged
    npt.assert_almost_equal(ta[: zdim_slice.start], data[: zdim_slice.start])
    npt.assert_almost_equal(ta[zdim_slice.stop :], data[zdim_slice.stop :])

    npt.assert_almost_equal(ta[:, : row_slice.start], data[:, : row_slice.start])
    npt.assert_almost_equal(ta[:, row_slice.stop :], data[:, row_slice.stop :])

    npt.assert_almost_equal(ta[:, :, : col_slice.start], data[:, :, : col_slice.start])
    npt.assert_almost_equal(ta[:, :, col_slice.stop :], data[:, :, col_slice.stop :])


def make_image_volume_graphic(data) -> fpl.ImageVolumeGraphic:
    fig = fpl.Figure(cameras="3d")
    return fig[0, 0].add_image_volume(data, offset=(0, 0, 0))


def check_image_graphic(texture_array, graphic):
    # make sure each ImageTile has the right texture
    for (texture, chunk_index, data_slice), img in zip(
        texture_array, graphic.world_object.children
    ):
        assert isinstance(img, _VolumeTile)
        assert img.geometry.grid is texture
        assert img.world.z == data_slice[0].start
        assert img.world.x == data_slice[2].start
        assert img.world.y == data_slice[1].start


@pytest.mark.parametrize("test_graphic", [False, True])
def test_small_texture(test_graphic):
    # tests TextureArray with dims that requires only 1 texture
    data = make_data(32, 64, 64)

    if test_graphic:
        graphic = make_image_volume_graphic(data)
        ta = graphic.data
    else:
        ta = TextureArrayVolume(data)

    check_texture_array(
        data=data,
        ta=ta,
        buffer_size=1,
        buffer_shape=(1, 1, 1),
        zdim_indices_size=1,
        row_indices_size=1,
        col_indices_size=1,
        zdim_indices_values=np.array([0]),
        row_indices_values=np.array([0]),
        col_indices_values=np.array([0]),
    )

    if test_graphic:
        check_image_graphic(ta, graphic)

    check_set_slice(data, ta, slice(5, 20), slice(10, 40), slice(20, 50))


@pytest.mark.parametrize("test_graphic", [False, True])
def test_texture_at_limit(test_graphic):
    # tests TextureArray with data that is 512 x 512 x 512
    data = make_data(MAX_TEXTURE_SIZE_3D, MAX_TEXTURE_SIZE_3D, MAX_TEXTURE_SIZE_3D)

    if test_graphic:
        graphic = make_image_volume_graphic(data)
        ta = graphic.data
    else:
        ta = TextureArrayVolume(data)

    check_texture_array(
        data=data,
        ta=ta,
        buffer_size=1,
        buffer_shape=(1, 1, 1),
        zdim_indices_size=1,
        row_indices_size=1,
        col_indices_size=1,
        zdim_indices_values=np.array([0]),
        row_indices_values=np.array([0]),
        col_indices_values=np.array([0]),
    )

    if test_graphic:
        check_image_graphic(ta, graphic)

    check_set_slice(data, ta, slice(5, 40), slice(10, 100), slice(20, 110))


@pytest.mark.parametrize("test_graphic", [False, True])
def test_high_cols(test_graphic):
    data = make_data(10, 100, 300)

    if test_graphic:
        graphic = make_image_volume_graphic(data)
        ta = graphic.data
    else:
        ta = TextureArrayVolume(data)

    check_texture_array(
        data,
        ta=ta,
        buffer_size=3,
        buffer_shape=(1, 1, 3),
        zdim_indices_size=1,
        row_indices_size=1,
        col_indices_size=3,
        zdim_indices_values=np.array([0]),
        row_indices_values=np.array([0]),
        col_indices_values=np.array([0, MAX_TEXTURE_SIZE_3D, 2 * MAX_TEXTURE_SIZE_3D]),
    )

    if test_graphic:
        check_image_graphic(ta, graphic)

    check_set_slice(data, ta, slice(2, 7), slice(60, 90), slice(100, 180))
