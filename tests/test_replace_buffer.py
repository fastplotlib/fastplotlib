import gc
import weakref

import pytest
import numpy as np

import fastplotlib as fpl
fpl.select_adapter(fpl.enumerate_adapters()[1])


@pytest.mark.parametrize("graphic_type", ["line", "scatter"])
@pytest.mark.parametrize("new_buffer_size", [50, 150])
def test_replace_buffer(graphic_type, new_buffer_size):
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

    graphic = adder(
        data=data,
        colors=np.random.rand(orig_datapoints, 4),
        **kwargs
    )

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
