import numpy as np
from numpy import testing as npt
import pytest

import fastplotlib as fpl

if not fpl.IMGUI:
    pytest.skip("NDWidget requires imgui-bundle", allow_module_level=True)

from fastplotlib.widgets.nd_widget._index import (
    AutoRangeContinuous,
    RangeContinuous,
    ReferenceIndices,
)


# [time, depth, row, col]
IMAGE_DATA = np.linspace(0, 1, 10 * 4 * 8 * 8, dtype=np.float32).reshape(10, 4, 8, 8)
IMAGE_DIMS = ("time", "depth", "row", "col")
DISPLAY_DIMS = ("row", "col")

INDICES_RETURN_VALUE: dict = None


def make_ref_indices() -> ReferenceIndices:
    """one identity dim, and one whose reference units are not array indices"""
    return ReferenceIndices({"time": (0, 100, 1), "depth": (15.0, 35.0, 0.5)})


def indices_handler(indices):
    global INDICES_RETURN_VALUE
    INDICES_RETURN_VALUE = dict(indices)


def check_auto_range(ri: ReferenceIndices, dim: str, size: int):
    """an AutoRangeContinuous for a dim of ``size`` covers exactly the array indices [0, size - 1]"""
    rr = ri.ref_ranges[dim]

    assert isinstance(rr, AutoRangeContinuous)
    assert (rr.start, rr.stop, rr.step) == (0, size, 1)

    # the slider runs over [start, stop - step], which must be exactly [0, size - 1]
    assert rr[0] == 0
    assert rr[size - 1] == size - 1
    with pytest.raises(IndexError):
        rr[size]

    # and the index is clamped to exactly that span
    ri.set_dim_index(dim, size)
    assert ri[dim] == size - 1
    ri.set_dim_index(dim, -1)
    assert ri[dim] == 0


def test_range_continuous():
    rr = RangeContinuous(15.0, 35.0, 0.5)

    assert rr.start == 15.0
    assert rr.stop == 35.0
    assert rr.step == 0.5
    assert rr.size == 20.0

    rr.start = 10.0
    rr.stop = 40.0
    assert (rr.start, rr.stop, rr.size) == (10.0, 40.0, 30.0)


def test_range_continuous_throttle():
    rr = RangeContinuous(0, 10, 1)
    assert rr.throttle == 0.05

    rr.throttle = 0.0
    assert rr.throttle == 0.0

    with pytest.raises(ValueError):
        rr.throttle = -0.1


@pytest.mark.parametrize("args", [(5, 5, 1), (10, 2, 1), (0.5, 0.5, 0.1)])
def test_range_continuous_start_after_stop(args):
    with pytest.raises(IndexError):
        RangeContinuous(*args)


def test_range_continuous_getitem():
    rr = RangeContinuous(15.0, 35.0, 0.5)

    assert rr[0] == 15.0
    assert rr[1] == 15.5
    assert rr[20] == 25.0

    # stop is an exclusive bound, so the last valid index is the one that the slider and the
    # ReferenceIndices clamp reach, i.e. stop - step
    assert rr[39] == 34.5

    with pytest.raises(IndexError):
        rr[40]

    with pytest.raises(IndexError):
        rr[1_000]

    with pytest.raises(ValueError):
        rr[-1]


def test_reference_indices_ranges():
    ri = make_ref_indices()

    assert ri.dims == {"time", "depth"}
    assert isinstance(ri.ref_ranges["time"], RangeContinuous)
    assert isinstance(ri.ref_ranges["depth"], RangeContinuous)

    # each dim starts at the start of its range
    assert dict(ri) == {"time": 0, "depth": 15.0}
    assert ri == {"time": 0, "depth": 15.0}
    assert len(ri) == 2
    assert ri["time"] == 0

    with pytest.raises(KeyError):
        ri["nope"]


def test_reference_indices_range_instances():
    rr = RangeContinuous(5, 10, 1)
    auto = AutoRangeContinuous(0, 8, 1)

    ri = ReferenceIndices({"a": rr, "b": auto})

    assert ri.ref_ranges["a"] is rr
    assert ri.ref_ranges["b"] is auto
    assert dict(ri) == {"a": 5, "b": 0}


@pytest.mark.parametrize("spec", [(0, 1), (0, 1, 2, 3)])
def test_reference_indices_bad_range(spec):
    # a range spec must be a (start, stop, step) 3-tuple
    with pytest.raises(ValueError):
        ReferenceIndices({"a": spec})


def test_push_dims():
    ri = ReferenceIndices({"time": (0, 100, 1)})
    ri.set_dim_index("time", 50)

    ri.push_dims({"depth": (15.0, 35.0, 0.5)})

    assert ri.dims == {"time", "depth"}
    assert ri["depth"] == 15.0
    # the dims that were already there are untouched
    assert ri["time"] == 50


def test_push_dims_replaces_existing():
    ri = ReferenceIndices({"time": (0, 100, 1)})
    ri.set_dim_index("time", 50)

    ri.push_dims({"time": (1_000, 2_000, 10)})

    rr = ri.ref_ranges["time"]
    assert (rr.start, rr.stop, rr.step) == (1_000, 2_000, 10)
    # the index is re-initialized to the start of the new range
    assert ri["time"] == 1_000


def test_pop_dims():
    ri = make_ref_indices()
    ri.set({"time": 50, "depth": 20.0})

    popped = ri.pop_dims("time")

    assert set(popped.keys()) == {"time"}
    assert ri.dims == {"depth"}
    assert dict(ri) == {"depth": 20.0}

    with pytest.raises(KeyError):
        ri["time"]

    # the returned ranges go straight back in
    ri.push_dims(popped)

    assert ri.dims == {"time", "depth"}
    assert ri.ref_ranges["time"] is popped["time"]
    assert ri["time"] == 0


def test_pop_dims_unknown():
    ri = make_ref_indices()

    with pytest.raises(KeyError):
        ri.pop_dims("nope")

    # every dim is checked before any of them are removed
    with pytest.raises(KeyError):
        ri.pop_dims("time", "nope")

    assert ri.dims == {"time", "depth"}


@pytest.mark.parametrize("setter", ["set", "set_dim_index"])
def test_set_indices(setter):
    ri = make_ref_indices()

    if setter == "set":
        ri.set({"time": 50})
    else:
        ri.set_dim_index("time", 50)

    assert ri["time"] == 50
    # a dim that was not given keeps its index
    assert ri["depth"] == 15.0


@pytest.mark.parametrize("setter", ["set", "set_dim_index"])
@pytest.mark.parametrize(
    "dim, value, expected",
    [
        # clamped into [start, stop - step] at both ends
        ("time", 1e6, 99),
        ("time", 99, 99),
        ("time", 0, 0),
        ("time", -50, 0),
        ("depth", 1e6, 34.5),
        ("depth", 34.5, 34.5),
        ("depth", 15.0, 15.0),
        ("depth", -1.0, 15.0),
    ],
)
def test_clamp(setter, dim, value, expected):
    ri = make_ref_indices()

    if setter == "set":
        ri.set({dim: value})
    else:
        ri.set_dim_index(dim, value)

    assert ri[dim] == expected


@pytest.mark.parametrize("setter", ["set", "set_dim_index"])
def test_set_unknown_dim(setter):
    ri = make_ref_indices()

    with pytest.raises(KeyError):
        if setter == "set":
            ri.set({"nope": 1})
        else:
            ri.set_dim_index("nope", 1)


def test_indices_event():
    global INDICES_RETURN_VALUE
    ri = make_ref_indices()
    ri.add_event_handler(indices_handler)

    INDICES_RETURN_VALUE = None
    ri.set_dim_index("time", 10)
    # the handler is given every index, not just the one that changed
    assert INDICES_RETURN_VALUE == {"time": 10, "depth": 15.0}

    INDICES_RETURN_VALUE = None
    ri.set({"time": 20, "depth": 20.0})
    assert INDICES_RETURN_VALUE == {"time": 20, "depth": 20.0}

    INDICES_RETURN_VALUE = None
    ri.remove_event_handler(indices_handler)
    ri.set_dim_index("time", 30)
    assert INDICES_RETURN_VALUE is None


def test_indices_event_clear():
    global INDICES_RETURN_VALUE
    ri = make_ref_indices()
    ri.add_event_handler(indices_handler)
    ri.clear_event_handlers()

    INDICES_RETURN_VALUE = None
    ri.set_dim_index("time", 10)

    assert INDICES_RETURN_VALUE is None


def test_bad_event_name():
    ri = make_ref_indices()

    with pytest.raises(ValueError):
        ri.add_event_handler(indices_handler, "bogus")


def test_auto_range_created():
    ndw = fpl.NDWidget(size=(200, 200))

    with pytest.warns(UserWarning, match="No reference range specified"):
        ndg = ndw[0, 0].add_nd_image(
            IMAGE_DATA, IMAGE_DIMS, DISPLAY_DIMS, compute_histogram=False
        )

    assert ndw.indices.dims == {"time", "depth"}
    check_auto_range(ndw.indices, "time", IMAGE_DATA.shape[0])
    check_auto_range(ndw.indices, "depth", IMAGE_DATA.shape[1])

    # every slider position maps onto its own array index, both ends included
    for dim, size in [("time", IMAGE_DATA.shape[0]), ("depth", IMAGE_DATA.shape[1])]:
        mapped = [ndg.slicer._ref_index_to_array_index(dim, i) for i in range(size)]
        npt.assert_array_equal(mapped, np.arange(size))


def test_auto_range_grows():
    big = np.linspace(0, 1, 25 * 4 * 8 * 8, dtype=np.float32).reshape(25, 4, 8, 8)

    ndw = fpl.NDWidget(size=(200, 200))
    with pytest.warns(UserWarning):
        ndw[0, 0].add_nd_image(
            IMAGE_DATA, IMAGE_DIMS, DISPLAY_DIMS, compute_histogram=False
        )

    # a larger array grows the existing auto range to fit it
    ndw[0, 0].add_nd_image(big, IMAGE_DIMS, DISPLAY_DIMS, compute_histogram=False)
    check_auto_range(ndw.indices, "time", big.shape[0])

    # a smaller one does not shrink it
    ndw[0, 0].add_nd_image(
        IMAGE_DATA, IMAGE_DIMS, DISPLAY_DIMS, compute_histogram=False
    )
    check_auto_range(ndw.indices, "time", big.shape[0])


def test_explicit_range_kept():
    ndw = fpl.NDWidget(ranges={"time": (0.0, 5.0, 0.1)}, size=(200, 200))

    with pytest.warns(UserWarning, match="depth"):
        ndw[0, 0].add_nd_image(
            IMAGE_DATA, IMAGE_DIMS, DISPLAY_DIMS, compute_histogram=False
        )

    # an explicit range is never replaced, nor grown to the size of the data
    rr = ndw.indices.ref_ranges["time"]
    assert not isinstance(rr, AutoRangeContinuous)
    assert (rr.start, rr.stop, rr.step) == (0.0, 5.0, 0.1)

    check_auto_range(ndw.indices, "depth", IMAGE_DATA.shape[1])


def test_pop_dim_in_use():
    ndw = fpl.NDWidget(
        ranges={"time": (0, 10, 1), "depth": (0, 4, 1), "unused": (0, 3, 1)},
        size=(200, 200),
    )
    ndw[0, 0].add_nd_image(
        IMAGE_DATA, IMAGE_DIMS, DISPLAY_DIMS, compute_histogram=False
    )

    # a dim that an NDGraphic slices with cannot be removed
    with pytest.raises(ValueError, match="cannot pop dim"):
        ndw.indices.pop_dims("time")

    assert ndw.indices.dims == {"time", "depth", "unused"}

    # one that nothing uses can be
    popped = ndw.indices.pop_dims("unused")

    assert set(popped.keys()) == {"unused"}
    assert ndw.indices.dims == {"time", "depth"}
