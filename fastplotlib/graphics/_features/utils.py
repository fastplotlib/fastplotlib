import pygfx
import numpy as np

from ._base import to_gpu_supported_dtype
from ...utils import make_pygfx_colors


def parse_colors(
    colors: str | np.ndarray | list[str] | tuple[str],
    n_colors: int | None,
    alpha: float | None = None,
):
    """

    Parameters
    ----------
    colors
    n_colors
    alpha
    key

    Returns
    -------

    """

    # if provided as a numpy array of str
    if isinstance(colors, np.ndarray):
        if colors.dtype.kind in ["U", "S"]:
            colors = colors.tolist()
    # if the color is provided as a numpy array
    if isinstance(colors, np.ndarray):
        if colors.shape == (4,):  # single RGBA array
            data = np.repeat(np.array([colors]), n_colors, axis=0)
        # else assume it's already a stack of RGBA arrays, keep this directly as the data
        elif colors.ndim == 2:
            if colors.shape[1] != 4 and colors.shape[0] != n_colors:
                raise ValueError(
                    "Valid array color arguments must be a single RGBA array or a stack of "
                    "RGBA arrays for each datapoint in the shape [n_datapoints, 4]"
                )
            data = colors
        else:
            raise ValueError(
                "Valid array color arguments must be a single RGBA array or a stack of "
                "RGBA arrays for each datapoint in the shape [n_datapoints, 4]"
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

        # if it's a single RGBA array as a tuple/list
        elif len(colors) == 4:
            c = pygfx.Color(colors)
            data = np.repeat(np.array([c]), n_colors, axis=0)

        else:
            raise ValueError(
                f"Valid iterable color arguments must be a `tuple` or `list` representing RGBA values or "
                f"an iterable of `str` with the same length as the number of datapoints."
            )
    elif isinstance(colors, str):
        if colors == "random":
            data = np.random.rand(n_colors, 4)
            data[:, -1] = alpha
        else:
            data = make_pygfx_colors(colors, n_colors)
    else:
        # assume it's a single color, use pygfx.Color to parse it
        data = make_pygfx_colors(colors, n_colors)

    if alpha is not None:
        if isinstance(alpha, float):
            data[:, -1] = alpha
        else:
            raise TypeError("if alpha is provided it must be of type `float`")

    return to_gpu_supported_dtype(data)
