import itertools

import numpy as np
from numpy import testing as npt
from numpy.lib.stride_tricks import sliding_window_view
import pytest
from scipy.ndimage import gaussian_filter1d

import fastplotlib as fpl

if not fpl.IMGUI:
    pytest.skip("NDWidget requires imgui-bundle", allow_module_level=True)

from fastplotlib.widgets.nd_widget._async import run_sync
from fastplotlib.widgets.nd_widget._nd_positions import NDPositionsSlicer


N_FREQS = 5
N_AMPLS = 4
N_LINES = 3
N_DATAPOINTS = 500

# 10 samples per reference unit
XS = np.linspace(0, 50, N_DATAPOINTS)

# a stack of sine and cosine waves, [freq, ampl, line, p, xy]. Every dim changes the y values, so a
# slice taken along the wrong dim does not go unnoticed
DATA = np.zeros((N_FREQS, N_AMPLS, N_LINES, N_DATAPOINTS, 2), dtype=np.float32)
for _freq in range(N_FREQS):
    for _ampl in range(N_AMPLS):
        for _line in range(N_LINES):
            _ys = np.sin(XS * (_freq + 1)) if _line % 2 == 0 else np.cos(XS * (_freq + 1))
            DATA[_freq, _ampl, _line] = np.column_stack(
                [XS, _ys * (_ampl + 1) * (_line + 1)]
            )

DIMS = ("freq", "ampl", "line", "p", "xy")
DISPLAY_DIMS = ("line", "p", "xy")

# the reference index used by most tests, mid-range in every dim
FREQ, AMPL, P = 2, 2, 25.0
INDICES = {"freq": FREQ, "ampl": AMPL, "p": P}

# a float32 reduction sums in a different order depending on the memory layout of its input, so a
# slice of a permuted array and a contiguous ground truth differ in the last few bits. A wrong axis
# or an off-by-one window is off by orders of magnitude more than this
RTOL = 1e-4


def make_slicer(data=DATA, dims=DIMS, **kwargs) -> NDPositionsSlicer:
    kwargs.setdefault("slider_maps", {"p": XS})
    kwargs.setdefault("display_window", 10.0)
    kwargs.setdefault("max_display_datapoints", None)

    return NDPositionsSlicer(data, dims, DISPLAY_DIMS, **kwargs)


def get_data(slicer: NDPositionsSlicer, indices: dict = INDICES) -> np.ndarray:
    return run_sync(slicer.get(indices))["data"]


def dw_bounds(index_ref: float, window: float, pad: float = 0.0) -> tuple[int, int]:
    """
    Array bounds of the display window, i.e. ``[index - w/2, index + w/2)`` in reference units mapped
    through ``XS.searchsorted``. ``pad`` is the extra half-window a ``datapoints_window_func`` adds.
    """
    half = (window + pad) / 2

    start = min(max(XS.searchsorted(index_ref - half), 0), N_DATAPOINTS - 1)
    stop = min(max(XS.searchsorted(index_ref + half), start + 1), N_DATAPOINTS)

    return start, stop


def test_dims():
    slicer = make_slicer()

    # the datapoints dim is both a display dim and a slider dim
    assert set(slicer.slider_dims) == {"freq", "ampl", "p"}
    assert slicer.display_dims == DISPLAY_DIMS
    assert slicer.shape == {
        "freq": N_FREQS,
        "ampl": N_AMPLS,
        "line": N_LINES,
        "p": N_DATAPOINTS,
        "xy": 2,
    }


def test_display_window_none():
    slicer = make_slicer(display_window=None)

    # every datapoint of the indexed sine and cosine waves
    npt.assert_array_equal(get_data(slicer), DATA[FREQ, AMPL])


def test_display_window_zero():
    slicer = make_slicer(display_window=0)

    # only the datapoint at the current index
    index = XS.searchsorted(P)
    npt.assert_array_equal(get_data(slicer), DATA[FREQ, AMPL][:, index : index + 1])


@pytest.mark.parametrize("p", [0.0, 25.0, 50.0])
def test_display_window(p):
    slicer = make_slicer(display_window=10.0)
    indices = {**INDICES, "p": p}

    start, stop = dw_bounds(p, 10.0)
    assert slicer._get_dw_slice(indices) == slice(start, stop, 1)

    npt.assert_array_equal(get_data(slicer, indices), DATA[FREQ, AMPL][:, start:stop])


def test_display_window_bounds():
    """the window is truncated at each end of the p dim, and reaches the first and last datapoint"""
    slicer = make_slicer(display_window=10.0)

    # 5 reference units either side of the index, at 10 samples per unit
    assert slicer._get_dw_slice({**INDICES, "p": 25.0}) == slice(200, 300, 1)
    assert slicer._get_dw_slice({**INDICES, "p": 0.0}) == slice(0, 50, 1)
    assert slicer._get_dw_slice({**INDICES, "p": 50.0}) == slice(450, N_DATAPOINTS, 1)


def window_bounds(index: int, window: float, size: int) -> tuple[int, int]:
    """array bounds of a window_func window, ``[index - w/2, index + w/2)`` under the identity map"""
    start = min(max(round(index - window / 2), 0), size - 1)
    stop = min(max(round(index + window / 2), start + 1), size)

    return start, stop


@pytest.mark.parametrize("func", [np.mean, np.max, np.std])
@pytest.mark.parametrize("window", [0, 2, 3, 100])
def test_window_func(func, window):
    slicer = make_slicer(window_funcs={"freq": (func, window)}, window_order=("freq",))

    start, stop = window_bounds(FREQ, window, N_FREQS)
    assert slicer._get_slider_dims_indexer(INDICES)["freq"] == slice(start, stop, 1)

    dw_start, dw_stop = dw_bounds(P, 10.0)
    expected = func(DATA[start:stop, AMPL], axis=0)[:, dw_start:dw_stop]

    npt.assert_allclose(get_data(slicer), expected, rtol=RTOL)


@pytest.mark.parametrize("order", [("freq", "ampl"), ("ampl", "freq")])
def test_window_order(order):
    """the funcs are applied in window_order, which matters for funcs that do not commute"""
    funcs = {"freq": (np.mean, 2), "ampl": (np.max, 3)}
    slicer = make_slicer(window_funcs=funcs, window_order=order)

    f_start, f_stop = window_bounds(FREQ, 2, N_FREQS)
    a_start, a_stop = window_bounds(AMPL, 3, N_AMPLS)

    expected = DATA[f_start:f_stop, a_start:a_stop]
    for dim in order:
        # each func keeps the dim it reduced, so the axis of the next one is unchanged
        expected = funcs[dim][0](expected, axis=DIMS.index(dim), keepdims=True)

    dw_start, dw_stop = dw_bounds(P, 10.0)
    expected = expected.squeeze(axis=(0, 1))[:, dw_start:dw_stop]

    npt.assert_allclose(get_data(slicer), expected, rtol=RTOL)


def test_window_order_differs():
    """mean-then-max and max-then-mean over two dims do not give the same result"""
    funcs = {"freq": (np.mean, 2), "ampl": (np.max, 3)}

    forward = get_data(make_slicer(window_funcs=funcs, window_order=("freq", "ampl")))
    reverse = get_data(make_slicer(window_funcs=funcs, window_order=("ampl", "freq")))

    assert not np.allclose(forward, reverse)


def test_window_func_not_in_window_order():
    """a dim with a window func that is not listed in window_order is indexed at a single value"""
    slicer = make_slicer(window_funcs={"freq": (np.mean, 2)}, window_order=None)

    assert slicer._get_slider_dims_indexer(INDICES)["freq"] == slice(FREQ, FREQ + 1, 1)

    dw_start, dw_stop = dw_bounds(P, 10.0)
    npt.assert_array_equal(
        get_data(slicer), DATA[FREQ, AMPL][:, dw_start:dw_stop]
    )


def test_window_func_bad_signature():
    # a window func must take `axis` and `keepdims`
    with pytest.raises(TypeError):
        make_slicer(window_funcs={"freq": (np.cumsum, 2)}, window_order=("freq",))


def test_window_func_bad_dim():
    # a window func can only be set for a slider dim
    with pytest.raises(KeyError):
        make_slicer(window_funcs={"line": (np.mean, 2)})

    with pytest.raises(ValueError):
        make_slicer(window_funcs={"freq": (np.mean, 2)}, window_order=("line",))


@pytest.mark.parametrize("max_datapoints", [None, 10, 25, 1_000])
def test_max_display_datapoints(max_datapoints):
    slicer = make_slicer(display_window=10.0, max_display_datapoints=max_datapoints)

    start, stop = dw_bounds(P, 10.0)
    step = 1 if max_datapoints is None else max(1, (stop - start) // max_datapoints)

    assert slicer._get_dw_slice(INDICES) == slice(start, stop, step)
    npt.assert_array_equal(
        get_data(slicer), DATA[FREQ, AMPL][:, start:stop:step]
    )


@pytest.mark.parametrize("setter", ["constructor", "property"])
def test_max_display_datapoints_invalid(setter):
    def set_value(v):
        if setter == "constructor":
            make_slicer(max_display_datapoints=v)
        else:
            make_slicer().max_display_datapoints = v

    with pytest.raises(ValueError):
        set_value(1)

    with pytest.raises(TypeError):
        set_value(10.0)


@pytest.mark.parametrize("setter", ["constructor", "property"])
def test_display_window_invalid(setter):
    if setter == "constructor":
        with pytest.raises(TypeError):
            make_slicer(display_window="10")
    else:
        with pytest.raises(TypeError):
            make_slicer().display_window = "10"


def dwf_window_size(window: float) -> int:
    """the datapoints_window_func size in array indices: at least 3, and rounded up to odd"""
    ws = max(min(XS.searchsorted(window), N_DATAPOINTS - 1), 3)

    return ws + 1 if ws % 2 == 0 else ws


@pytest.mark.parametrize("apply_dims", ["all", "y"])
@pytest.mark.parametrize("func", [np.mean, np.max])
def test_datapoints_window_func(func, apply_dims):
    window = 1.0
    slicer = make_slicer(
        display_window=10.0, datapoints_window_func=(func, apply_dims, window)
    )

    # the display window is padded by half the datapoints window on each side
    start, stop = dw_bounds(P, 10.0, pad=window)
    assert slicer._get_dw_slice(INDICES) == slice(start, stop, 1)

    ws = dwf_window_size(window)
    hw = ws // 2
    padded = DATA[FREQ, AMPL][:, start:stop]
    windows = sliding_window_view(padded, ws, axis=1)  # [line, p - ws + 1, xy, ws]

    if apply_dims == "all":
        expected = func(windows, axis=-1)
    else:
        # the coordinates that are not named are passed through unchanged
        expected = padded[:, hw : padded.shape[1] - hw].copy()
        expected[..., 1] = func(windows[..., 1, :], axis=-1)

    npt.assert_allclose(get_data(slicer), expected, rtol=RTOL)


def test_datapoints_window_func_skipped_at_zero_window():
    slicer = make_slicer(
        display_window=0, datapoints_window_func=(np.mean, "y", 1.0)
    )

    # there is only one datapoint to window over
    index = XS.searchsorted(P)
    npt.assert_array_equal(get_data(slicer), DATA[FREQ, AMPL][:, index : index + 1])


def test_datapoints_window_func_skipped_when_too_expensive():
    """the window func is skipped when the display window spans more than 2 * max_display_datapoints"""
    slicer = make_slicer(
        display_window=10.0,
        max_display_datapoints=25,
        datapoints_window_func=(np.mean, "y", 1.0),
    )

    start, stop = dw_bounds(P, 10.0, pad=1.0)
    step = max(1, (stop - start) // 25)

    npt.assert_array_equal(
        get_data(slicer), DATA[FREQ, AMPL][:, start:stop:step]
    )


def smooth_y(array: np.ndarray, sigma: float = 2.0) -> np.ndarray:
    """gaussian filter along the datapoints dim of the y coordinate"""
    out = array.copy()
    out[..., 1] = gaussian_filter1d(array[..., 1], sigma=sigma, axis=1)

    return out


def test_spatial_func():
    slicer = make_slicer(display_window=10.0, spatial_func=smooth_y)

    start, stop = dw_bounds(P, 10.0)
    expected = smooth_y(DATA[FREQ, AMPL][:, start:stop])

    npt.assert_allclose(get_data(slicer), expected, rtol=RTOL)


def test_spatial_func_after_datapoints_window_func():
    """the spatial func is given the slice the datapoints window func produced"""
    window = 1.0
    slicer = make_slicer(
        display_window=10.0,
        datapoints_window_func=(np.mean, "all", window),
        spatial_func=smooth_y,
    )

    start, stop = dw_bounds(P, 10.0, pad=window)
    ws = dwf_window_size(window)
    padded = DATA[FREQ, AMPL][:, start:stop]
    expected = smooth_y(np.mean(sliding_window_view(padded, ws, axis=1), axis=-1))

    npt.assert_allclose(get_data(slicer), expected, rtol=RTOL)


@pytest.mark.parametrize("dwf", [None, (np.mean, "y", 1.0)])
@pytest.mark.parametrize("order", list(itertools.permutations(DISPLAY_DIMS)))
def test_array_order(order, dwf):
    """the display dims do not have to be laid out in display order in the array"""
    axes = (0, 1) + tuple(2 + DISPLAY_DIMS.index(d) for d in order)
    slicer = make_slicer(
        data=DATA.transpose(*axes).copy(),
        dims=DIMS[:2] + order,
        display_window=10.0,
        datapoints_window_func=dwf,
    )

    if dwf is None:
        start, stop = dw_bounds(P, 10.0)
        expected = DATA[FREQ, AMPL][:, start:stop]
    else:
        start, stop = dw_bounds(P, 10.0, pad=dwf[2])
        ws = dwf_window_size(dwf[2])
        hw = ws // 2
        padded = DATA[FREQ, AMPL][:, start:stop]
        expected = padded[:, hw : padded.shape[1] - hw].copy()
        expected[..., 1] = dwf[0](
            sliding_window_view(padded[..., 1], ws, axis=1), axis=-1
        )

    npt.assert_allclose(get_data(slicer), expected, rtol=RTOL)


def make_ndwidget() -> tuple[fpl.NDWidget, "fpl.widgets.nd_widget.NDTimeseries"]:
    ndw = fpl.NDWidget(
        ranges={"p": (0, 50, 0.1), "freq": (0, N_FREQS, 1), "ampl": (0, N_AMPLS, 1)},
        size=(400, 300),
    )
    ndt = ndw[0, 0].add_nd_timeseries(
        DATA,
        DIMS,
        DISPLAY_DIMS,
        slider_maps={"p": XS},
        display_window=10.0,
        max_display_datapoints=None,
        x_range_mode="fixed",
        name="waves",
    )

    return ndw, ndt


def test_nd_timeseries():
    ndw, ndt = make_ndwidget()

    assert isinstance(ndt.graphic, fpl.LineStack)
    assert len(ndt.graphic) == N_LINES
    assert ndw[0, 0]["waves"] is ndt

    ndw.indices.set(INDICES)
    run_sync(ndt._set_indices_())

    assert ndt.indices_displayed == INDICES

    start, stop = dw_bounds(P, 10.0)
    expected = DATA[FREQ, AMPL][:, start:stop]

    for i, graphic in enumerate(ndt.graphic.graphics):
        # a LineStack holds xyz, the z column is unused for timeseries
        npt.assert_allclose(graphic.data.value[:, :2], expected[i], rtol=RTOL)


def test_nd_timeseries_x_range():
    ndw, ndt = make_ndwidget()

    ndw.indices.set(INDICES)
    run_sync(ndt._set_indices_())

    assert ndt.display_range == (P - 5.0, P + 5.0)
    # x_range_mode="fixed" pins the camera to the display window
    npt.assert_allclose(ndw.figure[0, 0].x_range, (P - 5.0, P + 5.0))

    # every datapoint is displayed, so there is no window for the camera to follow
    ndt.display_window = None
    assert ndt.display_range is None
    assert ndt.x_range_mode is None


def test_nd_timeseries_linear_selector():
    ndw, ndt = make_ndwidget()

    ndw.indices.set(INDICES)
    run_sync(ndt._set_indices_())

    selector = ndw.figure[0, 0]["__ndw_manged_linear_selector"]
    assert selector.selection == P

    # dragging the selector drives the p index of the shared ReferenceIndices
    selector.selection = P + 1.0
    assert ndw.indices["p"] == P + 1.0
