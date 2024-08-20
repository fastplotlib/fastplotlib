import numpy as np
from numpy import testing as npt
import pytest

from fastplotlib.graphics._features import PointsSizesFeature
from .utils import generate_slice_indices


def generate_data(input_type: str) -> np.ndarray | float:
    """
    Point sizes varying with a sine wave

    Parameters
    ----------
    input_type: str
        one of "sine", "cosine", or "float"
    """
    if input_type == "float":
        return 10.0
    xs = np.linspace(0, 10 * np.pi, 10)

    if input_type == "sine":
        return np.abs(np.sin(xs)).astype(np.float32)

    if input_type == "cosine":
        return np.abs(np.cos(xs)).astype(np.float32)


@pytest.mark.parametrize("data", [generate_data(v) for v in ["float", "sine"]])
def test_create_buffer(data):
    sizes = PointsSizesFeature(data, n_datapoints=10)

    if isinstance(data, float):
        npt.assert_almost_equal(sizes[:], generate_data("float"))

    elif isinstance(data, np.ndarray):
        npt.assert_almost_equal(sizes[:], generate_data("sine"))


@pytest.mark.parametrize(
    "slice_method", [generate_slice_indices(i) for i in range(0, 16)]
)
@pytest.mark.parametrize("user_input", ["float", "cosine"])
def test_slice(slice_method: dict, user_input: str):
    data = generate_data("sine")

    s = slice_method["slice"]
    indices = slice_method["indices"]
    offset = slice_method["offset"]
    size = slice_method["size"]
    others = slice_method["others"]

    sizes = PointsSizesFeature(data, n_datapoints=10)

    match user_input:
        case "float":
            sizes[s] = 20.0
            truth = np.full(len(indices), 20.0)
            npt.assert_almost_equal(sizes[s], truth)
            npt.assert_almost_equal(sizes[indices], truth)
            # make sure other sizes not modified
            npt.assert_almost_equal(sizes[others], data[others])

        case "cosine":
            cosine = generate_data("cosine")
            sizes[s] = cosine[s]
            npt.assert_almost_equal(sizes[s], cosine[s])
            npt.assert_almost_equal(sizes[indices], cosine[s])
            # make sure other sizes not modified
            npt.assert_almost_equal(sizes[others], data[others])
