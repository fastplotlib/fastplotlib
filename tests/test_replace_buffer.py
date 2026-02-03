import gc
import weakref

import pytest
import numpy as np
from itertools import product

import fastplotlib as fpl
from .test_texture_array import (
    MAX_TEXTURE_SIZE,
)
from .utils_textures import MAX_TEXTURE_SIZE, check_texture_array, check_image_graphic


# These are only de-referencing tests for positions graphics, and ImageGraphic
# they do not test that VRAM gets free, for now this can only be checked manually
# with the tests in examples/misc/buffer_replace_gc.py


@pytest.mark.parametrize("graphic_type", ["line", "scatter"])
@pytest.mark.parametrize("new_buffer_size", [50, 150])
def test_replace_positions_buffer(graphic_type, new_buffer_size):
    fig = fpl.Figure()

    orig_datapoints = 100

    xs = np.linspace(0, 2 * np.pi, orig_datapoints)
    ys = np.sin(xs)
    zs = np.cos(xs)

    data = np.column_stack([xs, ys, zs])

    adder = getattr(fig[0, 0], f"add_{graphic_type}")

    if graphic_type == "scatter":
        kwargs = {
            "markers": np.random.choice(list("osD+x^v<>*"), size=orig_datapoints),
            "uniform_marker": False,
            "sizes": np.abs(ys),
            "uniform_size": False,
            "point_rotations": zs * 180,
            "point_rotation_mode": "vertex",
        }
    else:
        kwargs = dict()

    graphic = adder(data=data, colors=np.random.rand(orig_datapoints, 4), **kwargs)

    del data
    del xs
    del ys
    del zs
    del kwargs

    fig.show()

    orig_data_buffer = weakref.proxy(graphic.data.buffer)
    orig_colors_buffer = weakref.proxy(graphic.colors.buffer)

    buffers = [orig_data_buffer, orig_colors_buffer]

    if graphic_type == "scatter":
        for attr in ["markers", "sizes", "point_rotations"]:
            buffers.append(weakref.proxy(getattr(graphic, attr).buffer))

    # create some new data
    xs = np.linspace(0, 15 * np.pi, new_buffer_size)
    ys = np.sin(xs)
    zs = np.cos(xs)

    new_data = np.column_stack([xs, ys, zs])

    # set data that requires a larger buffer and check that old buffer is no longer referenced
    graphic.data = new_data
    graphic.colors = np.random.rand(new_buffer_size, 4)

    if graphic_type == "scatter":
        # changes values so that new larger buffers must be allocated
        graphic.markers = np.random.choice(list("osD+x^v<>*"), size=new_buffer_size)
        graphic.sizes = np.abs(zs)
        graphic.point_rotations = ys * 180

    for i in range(len(buffers)):
        with pytest.raises(ReferenceError) as fail:
            buffers[i]
            pytest.fail(
                f"GC failed for buffer: {buffers[i]}, "
                f"with referrers: {gc.get_referrers(buffers[i].__repr__.__self__)}"
            )


# test all combination of dims that require TextureArrays of shapes 1x1, 1x2, 1x3, 2x3, 3x3 etc.
@pytest.mark.parametrize("new_buffer_size", list(product(*[[(500, 1), (1200, 2), (2200, 3)]] * 2)))
def test_replace_image_buffer(new_buffer_size):

    # should
    orig_size = (1_500, 1_500)

    data = np.random.rand(*orig_size)

    fig = fpl.Figure()
    image = fig[0, 0].add_image(data)

    orig_buffers = [weakref.proxy(image.data.buffer.ravel()[i]) for i in range(image.data.buffer.size)]
    orig_shape = image.data.buffer.shape

    fig.show()

    new_dims = [v[0] for v in new_buffer_size]
    new_shape = tuple(v[1] for v in new_buffer_size)

    new_data = np.random.rand(*new_dims)
    image.data = new_data

    # test that old buffer is de-referenced
    for i in range(len(orig_buffers)):
        with pytest.raises(ReferenceError) as fail:
            orig_buffers[i]
            pytest.fail(
                f"GC failed for buffer: {orig_buffers[i]}, of shape: {orig_shape}"
                f"with referrers: {gc.get_referrers(orig_buffers[i].__repr__.__self__)}"
            )

    # check new texture array
    check_texture_array(
        data=new_data,
        ta=image.data,
        buffer_size=np.prod(new_shape),
        buffer_shape=new_shape,
        row_indices_size=new_shape[0],
        col_indices_size=new_shape[1],
        row_indices_values=np.array(
            [
                i * MAX_TEXTURE_SIZE
                for i in range(0, 1 + (new_data.shape[0] - 1) // MAX_TEXTURE_SIZE)
            ]
        ),
        col_indices_values=np.array(
            [
                i * MAX_TEXTURE_SIZE
                for i in range(0, 1 + (new_data.shape[1] - 1) // MAX_TEXTURE_SIZE)
            ]
        ),
    )
