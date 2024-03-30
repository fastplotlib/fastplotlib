from collections import OrderedDict
from typing import *

import numpy as np
from cmap import Colormap

from pygfx import Texture, Color


def get_cmap(name: str, alpha: float = 1.0, gamma: float = 1.0) -> np.ndarray:
    """
    Get a colormap as numpy array

    Parameters
    ----------
    name: str
        name of colormap
    alpha: float
        alpha, 0.0 - 1.0
    gamma: float
        gamma, 0.0 - 1.0

    Returns
    -------
    np.ndarray
        [n_colors, 4], i.e. [n_colors, RGBA]

    """
    cmap = Colormap(name).lut(256, gamma=gamma)
    cmap[:, -1] = alpha
    return cmap.astype(np.float32)


def make_colors(n_colors: int, cmap: str, alpha: float = 1.0) -> np.ndarray:
    """
    Get colors from a colormap. The returned colors are uniformly spaced, except
    for qualitative colormaps where they are returned subsequently.

    Parameters
    ----------
    n_colors: int
        number of colors to get

    cmap: str
        name of colormap

    alpha: float, default 1.0
        alpha value

    Returns
    -------
    np.ndarray
        shape is [n_colors, 4], where the last dimension is RGBA

    """
    cm = Colormap(cmap)

    # can also use cm.category == "qualitative", but checking for non-interpolated
    # colormaps is a bit more general.  (and not all "custom" colormaps will be
    # assigned a category)
    if cm.interpolation == "nearest":
        max_colors = len(cm.color_stops)
        if n_colors > max_colors:
            raise ValueError(
                f"You have requested <{n_colors}> but only <{max_colors} existing for the "
                f"chosen cmap: <{cmap}>"
            )
        return np.asarray(cm.color_stops, dtype=np.float32)[:n_colors, 1:]

    cm_ixs = np.linspace(0, 255, n_colors, dtype=int)
    return cm(cm_ixs).astype(np.float32)


def get_cmap_texture(name: str, alpha: float = 1.0) -> Texture:
    return Colormap(name).to_pygfx()


def make_colors_dict(labels: Sequence, cmap: str, **kwargs) -> OrderedDict:
    """
    Get a dict for mapping labels onto colors.

    Parameters
    ----------
    labels: Sequence[Any]
        labels for creating a colormap. Order is maintained if it is a list of unique elements.

    cmap: str
        name of colormap

    **kwargs
        passed to make_colors()

    Returns
    -------
    OrderedDict
        keys are labels, values are colors

    Examples
    --------

    .. code-block:: python

        from fastplotlib.utils import get_colors_dict

        labels = ["l1", "l2", "l3"]
        labels_cmap = get_colors_dict(labels, cmap="tab10")

        # illustration of what the `labels_cmap` dict would look like:
        # keep in mind that the tab10 cmap was chosen here

        {
            "l1": <RGBA array for the blue 'tab10' color>,
            "l2": <RGBA array for the orange 'tab10' color>,
            "l3": <RGBA array for the green 'tab10' color>,
        }

        # another example with a non-qualitative cmap
        labels_cmap_seismic = get_colors_dict(labels, cmap="bwr")

        {
            "l1": <RGBA array for the blue 'bwr' color>,
            "l2": <RGBA array for the white 'bwr' color>,
            "l3": <RGBA array for the red 'bwr' color>,
        }

    """
    if not len(set(labels)) == len(labels):
        labels = list(set(labels))
    else:
        labels = list(labels)

    colors = make_colors(len(labels), cmap, **kwargs)

    return OrderedDict(zip(labels, colors))


def quick_min_max(data: np.ndarray) -> Tuple[float, float]:
    """
    Adapted from pyqtgraph.ImageView.
    Estimate the min/max values of *data* by subsampling.

    Parameters
    ----------
    data: np.ndarray or array-like with `min` and `max` attributes

    Returns
    -------
    (float, float)
        (min, max)
    """

    if hasattr(data, "min") and hasattr(data, "max"):
        # if value is pre-computed
        if isinstance(data.min, (float, int, np.number)) and isinstance(
            data.max, (float, int, np.number)
        ):
            return data.min, data.max

    while data.size > 1e6:
        ax = np.argmax(data.shape)
        sl = [slice(None)] * data.ndim
        sl[ax] = slice(None, None, 2)
        data = data[tuple(sl)]

    return float(np.nanmin(data)), float(np.nanmax(data))


def make_pygfx_colors(colors, n_colors):
    """
    Parse and make colors array using pyfx.Color

    Parameters
    ----------
    colors: str, list, tuple, or np.ndarray
        pygfx parseable color

    n_colors: int
        number of repeats of the color

    Returns
    -------
    np.ndarray
        shape is [n_colors, 4], i.e. [n_colors, RGBA]
    """

    c = Color(colors)
    colors_array = np.repeat(np.array([c]), n_colors, axis=0)

    return colors_array


def calculate_gridshape(n_subplots: int) -> Tuple[int, int]:
    """
    Returns ``(n_rows, n_cols)`` from given number of subplots ``n_subplots``
    """
    sr = np.sqrt(n_subplots)

    return (int(np.round(sr)), int(np.ceil(sr)))


def normalize_min_max(a):
    """normalize an array between 0 - 1"""
    if np.unique(a).size == 1:
        return np.zeros(a.size)

    return (a - np.min(a)) / (np.max(a - np.min(a)))


def parse_cmap_values(
    n_colors: int,
    cmap_name: str,
    cmap_values: Union[np.ndarray, List[Union[int, float]]] = None,
) -> np.ndarray:
    """

    Parameters
    ----------
    n_colors: int
        number of graphics in collection

    cmap_name: str
        colormap name

    cmap_values: np.ndarray | List[int | float], optional
        cmap values
    Returns
    -------

    """
    if cmap_values is None:
        # use the cmap values linearly just along the collection indices
        # for example, if len(data) = 10 and the cmap is "jet", then it will
        # linearly go from blue to red from data[0] to data[-1]
        colors = make_colors(n_colors, cmap_name)
        return colors

    else:
        if not isinstance(cmap_values, np.ndarray):
            cmap_values = np.array(cmap_values)

        # use the values within cmap_values to set the color of the corresponding data
        # each individual data[i] has its color based on the "relative cmap_value intensity"
        if len(cmap_values) != n_colors:
            raise ValueError(
                f"len(cmap_values) != len(data): {len(cmap_values)} != {n_colors}"
            )

        colormap = get_cmap(cmap_name)

        n_colors = colormap.shape[0] - 1

        # can also use cm.category == "qualitative"
        if Colormap(cmap_name).interpolation == "nearest":
            # check that cmap_values are <int> and within the number of colors `n_colors`
            # do not scale, use directly
            if not np.issubdtype(cmap_values.dtype, np.integer):
                raise TypeError(
                    f"<int> cmap_values should be used with qualitative colormaps, the dtype you "
                    f"have passed is {cmap_values.dtype}"
                )
            if max(cmap_values) > n_colors:
                raise IndexError(
                    f"You have chosen the qualitative colormap <'{cmap_name}'> which only has "
                    f"<{n_colors}> colors, which is lower than the max value of your `cmap_values`."
                    f"Choose a cmap with more colors, or a non-quantitative colormap."
                )
            norm_cmap_values = cmap_values
        else:
            # scale between 0 - n_colors so we can just index the colormap as a LUT
            norm_cmap_values = (normalize_min_max(cmap_values) * n_colors).astype(int)

        # use colormap as LUT to map the cmap_values to the colormap index
        colors = np.vstack([colormap[val] for val in norm_cmap_values])

        return colors
