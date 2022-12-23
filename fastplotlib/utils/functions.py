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


def get_colors(n_colors: int, cmap: str, alpha: float = 1.0) -> np.ndarray:
    cmap = _get_cmap(cmap, alpha)
    cm_ixs = np.linspace(0, 255, n_colors, dtype=int)
    return np.take(cmap, cm_ixs, axis=0).astype(np.float32)


def get_cmap_texture(name: str, alpha: float = 1.0) -> Texture:
    cmap = _get_cmap(name)
    return Texture(cmap, dim=1).get_view()


def get_cmap_labels(labels: iter, cmap: str, **kwargs) -> OrderedDict:
    """
    Get a dict for mapping labels onto colors
    Any kwargs are passed to auto_colormap()
    :param labels:  labels for creating a colormap. Order is maintained if it is a list of unique elements.
    :param cmap:    name of colormap
    :return:        dict of labels as keys and colors as values
    """
    if not len(set(labels)) == len(labels):
        labels = list(set(labels))
    else:
        labels = list(labels)

    colors = get_colors(len(labels), cmap, **kwargs)

    return OrderedDict(zip(labels, colors))


def map_labels_to_colors(labels: iter, cmap: str, **kwargs) -> list:
    """
    Map labels onto colors according to chosen colormap
    Any kwargs are passed to auto_colormap()
    :param labels:  labels for mapping onto a colormap
    :param cmap:    name of colormap
    :return:        list of colors mapped onto the labels
    """
    mapper = get_cmap_labels(labels, cmap, **kwargs)
    return list(map(mapper.get, labels))


def quick_min_max(data: np.ndarray) -> Tuple[float, float]:
    # adapted from pyqtgraph.ImageView
    # Estimate the min/max values of *data* by subsampling.
    # Returns [(min, max), ...] with one item per channel

    if hasattr(data, "min") and hasattr(data, "max"):
        # if value is pre-computed
        if isinstance(data.min, (float, int)) and isinstance(data.max, (float, int)):
            return data.min, data.max

    while data.size > 1e6:
        ax = np.argmax(data.shape)
        sl = [slice(None)] * data.ndim
        sl[ax] = slice(None, None, 2)
        data = data[tuple(sl)]

    return float(np.nanmin(data)), float(np.nanmax(data))


def to_float32(array):
    if isinstance(array, np.ndarray):
        return array.astype(np.float32, copy=False)

    return array


def fix_data(array, graphic_name: str) -> np.ndarray:
    """1d or 2d to 3d, cleanup data passed from user before instantiating any Graphic class"""
    if graphic_name == "ImageGraphic":
        return to_float32(array)

    if array.ndim == 1:
        # for scatter if we receive just 3 points in a 1d array, treat it as just a single datapoint
        # this is different from fix_data for LineGraphic since there we assume that a 1d array
        # is just y-values
        if graphic_name == "ScatterGraphic":
            array = np.array([array])
        elif graphic_name == "LineGraphic":
            array = np.dstack([np.arange(array.size), array])[0].astype(np.float32)

    if array.shape[1] != 3:
        if array.shape[1] != 2:
            raise ValueError(f"Must pass 1D, 2D or 3D data to {graphic_name}")

        # zeros for z
        zs = np.zeros(array.shape[0], dtype=np.float32)

        array = np.dstack([array[:, 0], array[:, 1], zs])[0]

    return array
