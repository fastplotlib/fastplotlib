import itertools
from pathlib import Path

import numpy as np
from numpy import testing as npt
import pytest
from scipy.ndimage import gaussian_filter

import fastplotlib as fpl

if not fpl.IMGUI:
    pytest.skip("NDWidget requires imgui-bundle", allow_module_level=True)

from fastplotlib.widgets.nd_widget._async import run_sync
from fastplotlib.widgets.nd_widget._nd_image import NDImageSlicer


# zebrafish calcium imaging, [time, plane, row, col] uint8
ZFISH = np.load(
    Path(__file__).parent.parent / "examples" / "notebooks" / "zfish_test.npy"
)
N_TIME, N_PLANES, N_ROWS, N_COLS = ZFISH.shape

# the frames are square, so the order tests crop one so that a wrong display order is a shape error
ZFISH_CROPPED = ZFISH[:, :, :200]

DIMS = ("time", "plane", "row", "col")
DISPLAY_DIMS = ("row", "col")

# the reference index used by most tests, mid-range in every dim
TIME, PLANE = 50, 2
INDICES = {"time": TIME, "plane": PLANE}


def make_slicer(
    data=ZFISH, dims=DIMS, display_dims=DISPLAY_DIMS, **kwargs
) -> NDImageSlicer:
    kwargs.setdefault("compute_histogram", False)

    return NDImageSlicer(data, dims, display_dims, **kwargs)


def get_data(slicer: NDImageSlicer, indices: dict = INDICES) -> np.ndarray:
    return run_sync(slicer.get(indices))


def window_bounds(index: int, window: float, size: int) -> tuple[int, int]:
    """array bounds of a window_func window, ``[index - w/2, index + w/2)`` under the identity map"""
    start = min(max(round(index - window / 2), 0), size - 1)
    stop = min(max(round(index + window / 2), start + 1), size)

    return start, stop


def test_dims():
    slicer = make_slicer()

    assert slicer.slider_dims == {"time", "plane"}
    assert slicer.display_dims == DISPLAY_DIMS
    assert slicer.shape == {
        "time": N_TIME,
        "plane": N_PLANES,
        "row": N_ROWS,
        "col": N_COLS,
    }


def test_no_window_func():
    slicer = make_slicer()

    # each slider dim is indexed at a single value
    assert slicer._get_slider_dims_indexer(INDICES) == {
        "time": slice(TIME, TIME + 1, 1),
        "plane": slice(PLANE, PLANE + 1, 1),
    }
    npt.assert_array_equal(get_data(slicer), ZFISH[TIME, PLANE])


@pytest.mark.parametrize("plane", [0, N_PLANES - 1])
@pytest.mark.parametrize("time", [0, TIME, N_TIME - 1])
def test_index_bounds(time, plane):
    slicer = make_slicer()

    npt.assert_array_equal(
        get_data(slicer, {"time": time, "plane": plane}), ZFISH[time, plane]
    )


@pytest.mark.parametrize("time", [0, TIME, N_TIME - 1])
@pytest.mark.parametrize("window", [0, 5, 13, 1_000])
@pytest.mark.parametrize("func", [np.mean, np.max, np.min])
def test_window_func(func, window, time):
    slicer = make_slicer(window_funcs={"time": (func, window)}, window_order=("time",))
    indices = {**INDICES, "time": time}

    start, stop = window_bounds(time, window, N_TIME)
    assert slicer._get_slider_dims_indexer(indices)["time"] == slice(start, stop, 1)

    npt.assert_allclose(
        get_data(slicer, indices), func(ZFISH[start:stop, PLANE], axis=0)
    )


@pytest.mark.parametrize("order", [("time", "plane"), ("plane", "time")])
def test_window_order(order):
    """the funcs are applied in window_order, which matters for funcs that do not commute"""
    funcs = {"time": (np.mean, 13), "plane": (np.max, 3)}
    slicer = make_slicer(window_funcs=funcs, window_order=order)

    t_start, t_stop = window_bounds(TIME, 13, N_TIME)
    p_start, p_stop = window_bounds(PLANE, 3, N_PLANES)

    expected = ZFISH[t_start:t_stop, p_start:p_stop]
    for dim in order:
        # each func keeps the dim it reduced, so the axis of the next one is unchanged
        expected = funcs[dim][0](expected, axis=DIMS.index(dim), keepdims=True)

    npt.assert_allclose(get_data(slicer), expected.squeeze(axis=(0, 1)))


def test_window_order_differs():
    """mean-then-max and max-then-mean over two dims do not give the same result"""
    funcs = {"time": (np.mean, 13), "plane": (np.max, 3)}

    forward = get_data(make_slicer(window_funcs=funcs, window_order=("time", "plane")))
    reverse = get_data(make_slicer(window_funcs=funcs, window_order=("plane", "time")))

    assert not np.allclose(forward, reverse)


def test_window_func_not_in_window_order():
    """a dim with a window func that is not listed in window_order is indexed at a single value"""
    slicer = make_slicer(window_funcs={"time": (np.mean, 13)}, window_order=None)

    assert slicer._get_slider_dims_indexer(INDICES)["time"] == slice(
        TIME, TIME + 1, 1
    )
    npt.assert_array_equal(get_data(slicer), ZFISH[TIME, PLANE])


def smooth(frame: np.ndarray, sigma: float = 3.0) -> np.ndarray:
    """2D gaussian filter over the rendered frame"""
    return gaussian_filter(frame.astype(np.float32), sigma=sigma)


def test_spatial_func():
    slicer = make_slicer(spatial_func=smooth)

    npt.assert_allclose(get_data(slicer), smooth(ZFISH[TIME, PLANE]))


def test_spatial_func_after_window_func():
    """the spatial func is given the slice the window funcs produced"""
    slicer = make_slicer(
        window_funcs={"time": (np.mean, 13)},
        window_order=("time",),
        spatial_func=smooth,
    )

    start, stop = window_bounds(TIME, 13, N_TIME)
    expected = smooth(ZFISH[start:stop, PLANE].mean(axis=0))

    npt.assert_allclose(get_data(slicer), expected)


def test_spatial_func_in_display_order():
    """the spatial func is given the slice as it is rendered, not in array order"""
    slicer = make_slicer(
        data=ZFISH_CROPPED, display_dims=("col", "row"), spatial_func=smooth
    )

    npt.assert_allclose(get_data(slicer), smooth(ZFISH_CROPPED[TIME, PLANE].T))


def test_display_dims_transposed():
    """display_dims gives the display order, the array does not have to be laid out that way"""
    slicer = make_slicer(data=ZFISH_CROPPED, display_dims=("col", "row"))

    npt.assert_array_equal(get_data(slicer), ZFISH_CROPPED[TIME, PLANE].T)


def test_array_order():
    """the display dims do not have to be laid out in display order in the array"""
    slicer = make_slicer(
        data=ZFISH_CROPPED.transpose(0, 1, 3, 2),
        dims=("time", "plane", "col", "row"),
    )

    npt.assert_array_equal(get_data(slicer), ZFISH_CROPPED[TIME, PLANE])


@pytest.mark.parametrize(
    "display_dims", list(itertools.permutations(("plane", "row", "col")))
)
def test_display_dims_volume(display_dims):
    """three display dims render a volume, in any display order"""
    slicer = make_slicer(data=ZFISH_CROPPED, display_dims=display_dims)

    assert slicer.slider_dims == {"time"}

    axes = tuple(("plane", "row", "col").index(d) for d in display_dims)
    npt.assert_array_equal(
        get_data(slicer, {"time": TIME}), ZFISH_CROPPED[TIME].transpose(*axes)
    )


def test_display_dims_invalid():
    # images take 2 or 3 display dims
    with pytest.raises(ValueError):
        make_slicer(display_dims=("row",))

    with pytest.raises(KeyError):
        make_slicer(display_dims=("row", "nope"))


def test_histogram():
    slicer = make_slicer(compute_histogram=True)

    counts, edges = slicer.histogram
    assert counts.shape == (100,)
    assert edges.shape == (101,)

    slicer.compute_histogram = False
    assert slicer.histogram is None

    slicer.compute_histogram = True
    npt.assert_array_equal(slicer.histogram[0], counts)
    npt.assert_array_equal(slicer.histogram[1], edges)


def make_ndwidget(**kwargs) -> tuple[fpl.NDWidget, "fpl.widgets.nd_widget.NDImage"]:
    kwargs.setdefault("compute_histogram", False)

    ndw = fpl.NDWidget(
        ranges={"time": (0, N_TIME, 1), "plane": (0, N_PLANES, 1)}, size=(400, 300)
    )
    ndi = ndw[0, 0].add_nd_image(ZFISH, DIMS, DISPLAY_DIMS, name="zfish", **kwargs)

    return ndw, ndi


def test_nd_image():
    ndw, ndi = make_ndwidget(
        window_funcs={"time": (np.max, 13)}, window_order=("time",)
    )

    assert isinstance(ndi.graphic, fpl.ImageGraphic)
    assert ndw[0, 0]["zfish"] is ndi

    ndw.indices.set(INDICES)
    run_sync(ndi._set_indices_())

    assert ndi.indices_displayed == INDICES

    start, stop = window_bounds(TIME, 13, N_TIME)
    npt.assert_array_equal(
        ndi.graphic.data.value, ZFISH[start:stop, PLANE].max(axis=0)
    )


def test_nd_image_display_dims_swaps_graphic():
    ndw, ndi = make_ndwidget()
    assert isinstance(ndi.graphic, fpl.ImageGraphic)

    # a third display dim makes it a volume
    ndi.display_dims = ("plane", "row", "col")

    assert isinstance(ndi.graphic, fpl.ImageVolumeGraphic)
    npt.assert_array_equal(ndi.graphic.data.value, ZFISH[ndw.indices["time"]])


def test_clim_quantiles():
    ndw, ndi = make_ndwidget(compute_histogram=True, clim_quantiles=(0.01, 0.99))

    assert ndi.clim_quantiles == (0.01, 0.99)
    # the quantiles cut off the tails, so the limits sit inside the range of the data
    assert ZFISH.min() <= ndi.graphic.vmin < ndi.graphic.vmax <= ZFISH.max()


@pytest.mark.parametrize("quantiles", [(0.9, 0.1), (-0.1, 0.5), (0.1, 1.5), (0.5, 0.5)])
def test_clim_quantiles_invalid(quantiles):
    ndw, ndi = make_ndwidget(compute_histogram=True)

    with pytest.raises(ValueError):
        ndi.clim_quantiles = quantiles


def test_clim_quantiles_requires_histogram():
    # the quantiles are taken from the histogram
    ndw, ndi = make_ndwidget(compute_histogram=False)

    with pytest.raises(ValueError):
        ndi.clim_quantiles = (0.01, 0.99)
