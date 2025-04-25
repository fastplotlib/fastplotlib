from collections import OrderedDict
from typing import *

import numpy as np
import cmap as cmap_lib

from pygfx import Texture, Color


cmap_catalog = cmap_lib.Catalog()

COLORMAPS = sorted(
    [
        "viridis",
        "plasma",
        "inferno",
        "magma",
        "cividis",
        "Greys",
        "Purples",
        "Blues",
        "Greens",
        "Oranges",
        "Reds",
        "tol:YlOrBr",
        "YlOrRd",
        "OrRd",
        "PuRd",
        "RdPu",
        "BuPu",
        "GnBu",
        "PuBu",
        "YlGnBu",
        "PuBuGn",
        "BuGn",
        "YlGn",
        "binary",
        "gist_yarg",
        "gist_gray",
        "gray",
        "bone",
        "pink",
        "spring",
        "summer",
        "autumn",
        "winter",
        "cool",
        "Wistia",
        "hot",
        "afmhot",
        "gist_heat",
        "matlab:copper",
        "PiYG",
        "tol:PRGn",
        "BrBG",
        "PuOr",
        "RdGy",
        "vispy:RdBu",
        "RdYlBu",
        "RdYlGn",
        "Spectral",
        "coolwarm",
        "bwr",
        "seismic",
        "berlin",
        "vanimo",
        "twilight",
        "twilight_shifted",
        "hsv",
        "Pastel1",
        "Pastel2",
        "Paired",
        "Accent",
        "Dark2",
        "Set1",
        "Set2",
        "Set3",
        "tab10",
        "tab20",
        "tab20b",
        "tab20c",
        "flag",
        "prism",
        "gnuplot:ocean",
        "gist_earth",
        "terrain",
        "gist_stern",
        "gnuplot",
        "gnuplot2",
        "CMRmap",
        "cubehelix",
        "brg",
        "gist_rainbow",
        "yorick:rainbow",
        "jet",
        "turbo",
        "nipy_spectral",
        "gist_ncar",
    ]
)

SEQUENTIAL_CMAPS = list()
QUALITATIVE_CMAPS = list()
CYCLIC_CMAPS = list()
DIVERGING_CMAPS = list()
MISC_CMAPS = list()


for name in COLORMAPS:
    _colormap = cmap_lib.Colormap(name)
    match _colormap.category:
        case "sequential":
            if _colormap.interpolation == "nearest":
                continue
            SEQUENTIAL_CMAPS.append(name)
        case "cyclic":
            if _colormap.interpolation == "nearest":
                continue
            CYCLIC_CMAPS.append(name)
        case "diverging":
            if _colormap.interpolation == "nearest":
                continue
            DIVERGING_CMAPS.append(name)
        case "qualitative":
            QUALITATIVE_CMAPS.append(name)
        case "miscellaneous":
            if _colormap.interpolation == "nearest":
                continue
            MISC_CMAPS.append(name)


COLORMAP_NAMES = {
    "sequential": sorted(SEQUENTIAL_CMAPS),
    "cyclic": sorted(CYCLIC_CMAPS),
    "diverging": sorted(DIVERGING_CMAPS),
    "qualitative": sorted(QUALITATIVE_CMAPS),
    "miscellaneous": sorted(MISC_CMAPS),
}


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

    cmap = cmap_lib.Colormap(name).lut(256, gamma=gamma)
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

    cm = cmap_lib.Colormap(cmap)

    # can also use cm.category == "qualitative", but checking for non-interpolated
    # colormaps is a bit more general.  (and not all "custom" colormaps will be
    # assigned a category)
    if cm.interpolation == "nearest":
        max_colors = len(cm.color_stops)
        if n_colors > max_colors:
            raise ValueError(
                f"You have requested <{n_colors}> colors but only <{max_colors}> exist for the "
                f"chosen cmap: <{cmap}>"
            )
        return np.asarray(cm.color_stops, dtype=np.float32)[:n_colors, 1:]

    cm_ixs = np.linspace(0, 255, n_colors, dtype=int)
    return cm(cm_ixs).astype(np.float32)


def get_cmap_texture(name: str, alpha: float = 1.0) -> Texture:
    return Texture(get_cmap(name, alpha), dim=1)


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


def quick_min_max(data: np.ndarray, max_size=1e6) -> tuple[float, float]:
    """
    Adapted from pyqtgraph.ImageView.
    Estimate the min/max values of *data* by subsampling.

    Parameters
    ----------
    data: np.ndarray or array-like with `min` and `max` attributes

    max_size : int, optional
        largest array size allowed in the subsampled array. Default is 1e6.

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

    data = subsample_array(data, max_size=max_size)

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


def calculate_figure_shape(n_subplots: int) -> tuple[int, int]:
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
    transform: np.ndarray | list[int | float] = None,
) -> np.ndarray:
    """

    Parameters
    ----------
    n_colors: int
        number of graphics in collection

    cmap_name: str
        colormap name

    transform: np.ndarray | List[int | float], optional
        cmap transform
    Returns
    -------

    """
    if transform is None:
        colors = make_colors(n_colors, cmap_name)
        return colors

    else:
        if not isinstance(transform, np.ndarray):
            transform = np.array(transform)

        # use the of the cmap_transform to set the color of the corresponding data
        # each individual data[i] has its color based on the transform values
        if len(transform) != n_colors:
            raise ValueError(
                f"len(cmap_values) != len(data): {len(transform)} != {n_colors}"
            )

        colormap = get_cmap(cmap_name)

        n_colors = colormap.shape[0] - 1

        # can also use cm.category == "qualitative"
        if cmap_lib.Colormap(cmap_name).interpolation == "nearest":

            # check that cmap_values are <int> and within the number of colors `n_colors`

            # do not scale, use directly
            if not np.issubdtype(transform.dtype, np.integer):
                raise TypeError(
                    f"<int> `cmap_transform` values should be used with qualitative colormaps, "
                    f"the dtype you have passed is {transform.dtype}"
                )
            if max(transform) > n_colors:
                raise IndexError(
                    f"You have chosen the qualitative colormap <'{cmap_name}'> which only has "
                    f"<{n_colors}> colors, which is lower than the max value of your `cmap_transform`."
                    f"Choose a cmap with more colors, or a non-quantitative colormap."
                )
            norm_cmap_values = transform
        else:
            # scale between 0 - n_colors so we can just index the colormap as a LUT
            norm_cmap_values = (normalize_min_max(transform) * n_colors).astype(int)

        # use colormap as LUT to map the cmap_values to the colormap index
        colors = np.vstack([colormap[val] for val in norm_cmap_values])

        return colors


def subsample_array(
    arr: np.ndarray, max_size: int = 1e6, ignore_dims: Sequence[int] | None = None
):
    """
    Subsamples an input array while preserving its relative dimensional proportions.

    The dimensions (shape) of the array can be represented as:

    .. math::

        [d_1, d_2, \\dots d_n]

    The product of the dimensions can be represented as:

    .. math::

        \\prod_{i=1}^{n} d_i

    To find the factor ``f`` by which to divide the size of each dimension in order to
    get max_size ``s`` we must solve for ``f`` in the following expression:

    .. math::

        \\prod_{i=1}^{n} \\frac{d_i}{\\mathbf{f}} = \\mathbf{s}

    The solution for ``f`` is is simply the nth root of the product of the dims divided by the max_size
    where n is the number of dimensions

    .. math::

        \\mathbf{f} = \\sqrt[n]{\\frac{\\prod_{i=1}^{n} d_i}{\\mathbf{s}}}

    Parameters
    ----------
    arr: np.ndarray
        input array of any dimensionality to be subsampled.

    max_size: int, default 1e6
        maximum number of elements in subsampled array

    ignore_dims: Sequence[int], optional
        List of dimension indices to exclude from subsampling (i.e. retain full resolution).
        For example, `ignore_dims=[0]` will avoid subsampling along the first axis.

    Returns
    -------
    np.ndarray
        subsample of the input array
    """
    if np.prod(arr.shape, dtype=np.int64) <= max_size:
        return arr[:]  # no need to subsample if already below the threshold

    # get factor by which to divide all dims
    f = np.power((np.prod(arr.shape, dtype=np.int64) / max_size), 1.0 / arr.ndim)

    # new shape for subsampled array
    ns = np.floor(np.array(arr.shape) / f).clip(min=1)

    # get the step size for the slices
    slices = tuple(
        slice(None, None, int(s)) for s in np.floor(arr.shape / ns).astype(int)
    )

    # ignore dims e.g. RGB, which we don't want to downsample
    if ignore_dims is not None:
        for dim in ignore_dims:
            slices[dim] = slice(None)

    slices = tuple(slices)

    return np.asarray(arr[slices])
