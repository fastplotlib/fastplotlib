import numpy as np
import pygfx
from numpy import testing as npt

from fastplotlib.graphics.features import TextureArray
from fastplotlib.graphics.image import _ImageTile


MAX_TEXTURE_SIZE = 1024


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


def check_image_graphic(texture_array, graphic):
    # make sure each ImageTile has the right texture
    for (texture, chunk_index, data_slice), img in zip(
        texture_array, graphic.world_object.children
    ):
        assert isinstance(img, _ImageTile)
        assert img.geometry.grid is texture
        assert img.world.x == data_slice[1].start
        assert img.world.y == data_slice[0].start
