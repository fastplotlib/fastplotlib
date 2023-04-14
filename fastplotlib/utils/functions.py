import numpy as np
from pygfx import Texture
from collections import OrderedDict
from typing import *
from pathlib import Path
# some funcs adapted from mesmerize


qual_cmaps = ['Pastel1', 'Pastel2', 'Paired', 'Accent', 'Dark2', 'Set1',
              'Set2', 'Set3', 'tab10', 'tab20', 'tab20b', 'tab20c']


def _get_cmap(name: str, alpha: float = 1.0) -> np.ndarray:
    cmap_path = Path(__file__).absolute().parent.joinpath('colormaps', name)
    if cmap_path.is_file():
        cmap = np.loadtxt(cmap_path)

    else:
        try:
            from .generate_colormaps import make_cmap
            cmap = make_cmap(name, alpha)
        except ModuleNotFoundError as e:
            raise ModuleNotFoundError(
                "Couldn't find colormap files, matplotlib is required to generate them "
                "if they aren't found. Please install `matplotlib`."
            )

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
    name = cmap
    cmap = _get_cmap(name, alpha)

    if name in qual_cmaps:
        max_colors = cmap.shape[0]
        if n_colors > cmap.shape[0]:
            raise ValueError(f"You have requested <{n_colors}> but only <{max_colors} existing for the "
                             f"chosen cmap: <{cmap}>")
        return cmap[:n_colors]

    cm_ixs = np.linspace(0, 255, n_colors, dtype=int)
    return np.take(cmap, cm_ixs, axis=0).astype(np.float32)


def get_cmap_texture(name: str, alpha: float = 1.0) -> Texture:
    cmap = _get_cmap(name)
    return Texture(cmap, dim=1)


def make_colors_dict(labels: iter, cmap: str, **kwargs) -> OrderedDict:
    """
    Get a dict for mapping labels onto colors.

    Parameters
    ----------
    labels: Iterable[Any]
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
    # adapted from pyqtgraph.ImageView
    # Estimate the min/max values of *data* by subsampling.
    # Returns [(min, max), ...] with one item per channel

    if hasattr(data, "min") and hasattr(data, "max"):
        # if value is pre-computed
        if isinstance(data.min, (float, int, np.number)) and isinstance(data.max, (float, int, np.number)):
            return data.min, data.max

    while data.size > 1e6:
        ax = np.argmax(data.shape)
        sl = [slice(None)] * data.ndim
        sl[ax] = slice(None, None, 2)
        data = data[tuple(sl)]

    return float(np.nanmin(data)), float(np.nanmax(data))
