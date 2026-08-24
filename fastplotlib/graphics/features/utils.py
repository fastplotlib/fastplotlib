import numbers

import pygfx
import numpy as np

from ._base import to_gpu_supported_dtype
from ...utils import make_pygfx_colors


def is_single_color(value) -> bool:
    """
    Whether ``value`` represents a single RGB(A) color rather than a sequence of colors.

    A single color is a str, ``pygfx.Color``, or an RGB(A) array/list/tuple of 3-4 numbers.
    """
    if isinstance(value, np.ndarray):
        # returns True if a 1D RGB(A) array
        # returns False if shape is [n, 3 | 4]
        return value.shape in ((3,), (4,)) and value.dtype.kind in "fiu"

    if isinstance(value, (list, tuple)):
        # returns True if RGB(A) list or tuple of int/float
        # returns False otherwise
        return len(value) in (3, 4) and all(isinstance(v, numbers.Real) for v in value)

    # str, pygfx.Color, or any other scalar color specifier
    if isinstance(value, (pygfx.Color, str)):
        return True

    raise ValueError(
        "`colors` must be a str, pygfx.Color, array, list or tuple indicating an RGB(A) color, a "
        "sequence of str, pygfx.Color, and array of shape [n_datapoints, 3 | 4], or an existing "
        "`UniformColor` or `VertexColors` instance."
    )


def parse_colors(
    colors: str | np.ndarray | list[str] | tuple[str], n_colors: int | None
):
    """

    Parameters
    ----------
    colors
    n_colors

    Returns
    -------

    """

    # if provided as a numpy array of str
    if isinstance(colors, np.ndarray):
        if colors.dtype.kind in ["U", "S"]:
            colors = colors.tolist()
    # if the color is provided as a numpy array
    if isinstance(colors, np.ndarray):
        if colors.shape == (3,):  # single RGB array
            data = np.repeat(np.array([colors]), n_colors, axis=0)
        elif colors.shape == (4,):  # single RGBA array
            data = np.repeat(np.array([colors]), n_colors, axis=0)
        # else assume it's already a stack of RGBA arrays, keep this directly as the data
        elif colors.ndim == 2:
            if not (colors.shape[1] in (3, 4) and colors.shape[0] == n_colors):
                raise ValueError(
                    f"Valid array color arguments must be a single RGBA array or a stack of "
                    f"RGB or RGBA arrays for each datapoint in the shape [n_datapoints, 3] or [n_datapoints, 4].\n"
                    f"n_datapoints is: {n_colors}, you passed a colors array of shape: {colors.shape}"
                )
            data = colors
        else:
            raise ValueError(
                "Valid array color arguments must be a single RGB(A) array or a stack of "
                "RGB(A) arrays for each datapoint in the shape [n_datapoints, 3] or [n_datapoints, 4]"
            )

    # if the color is provided as list or tuple
    elif isinstance(colors, (list, tuple)):
        # if iterable of str
        if all([isinstance(val, str) for val in colors]):
            if not len(colors) == n_colors:
                raise ValueError(
                    f"Valid iterable color arguments must be a `tuple` or `list` of `str` "
                    f"where the length of the iterable is the same as the number of datapoints."
                )

            data = np.vstack([np.array(pygfx.Color(c)) for c in colors])

        # if it's a single RGB/RGBA array as a tuple/list
        elif len(colors) in (3, 4):
            c = pygfx.Color(colors)
            data = np.repeat(np.array([c]), n_colors, axis=0)

        else:
            raise ValueError(
                f"Valid iterable color arguments must be a `tuple` or `list` representing RGBA values or "
                f"an iterable of `str` with the same length as the number of datapoints."
            )
    elif isinstance(colors, str):
        if colors == "random":
            data = np.random.rand(n_colors, 3)
        else:
            data = make_pygfx_colors(colors, n_colors)
    else:
        # assume it's a single color, use pygfx.Color to parse it
        data = make_pygfx_colors(colors, n_colors)

    return to_gpu_supported_dtype(data)


def get_element_format_from_numpy_array(array):
    """Get the per-element format specifier from a numpy array.
    Returns None if the format appears to be a structured array.
    Raises an error if GPU-incompatible dtypes are used (64 bit).
    """

    # Uniform buffers are scalars with a structured dtype.
    # But can also create storage buffers with complex formats.
    if array.dtype.kind not in "iuf":
        return None

    # GPUs generally don't support 64-bit buffers or textures.
    # Note: the Python docs say that l and L are 32 bit, but converting
    # a int64 numpy array to a memoryview gives a format of 'l' instead
    # of 'q' on some systems/configs? So we need to check the itemsize.
    if array.itemsize == 8:
        raise ValueError(
            f"A dtype of {array.dtype.name} is not supported for buffers, use a 32-bit variant instead."
        )

    return array.dtype.str.lstrip("<>=|")


def normalize_min_max(a, vmin: float | None = None, vmax: float | None = None, gamma: float = 1.0):
    """
    normalize an array between 0 - 1, clipped to (vmin, vmax)
    """
    a = np.asarray(a)
    vmin = np.min(a) if vmin is None else vmin
    vmax = np.max(a) if vmax is None else vmax

    if vmax <= vmin:
        return np.zeros(a.size)

    transform = np.clip((a - vmin) / (vmax - vmin), 0, 1)
    if gamma == 1.0:
        return transform
    return transform**gamma