import numpy as np
from pygfx import Texture
from collections import OrderedDict
from typing import *
from pathlib import Path
# some funcs adapted from mesmerize


qual_cmaps = ['Pastel1', 'Pastel2', 'Paired', 'Accent', 'Dark2', 'Set1',
              'Set2', 'Set3', 'tab10', 'tab20', 'tab20b', 'tab20c']


def _get_cmap(name: str, alpha: float = 1.0) -> np.ndarray:
    cmap = np.loadtxt(str(Path(__file__).absolute().parent.joinpath('colormaps', name)))
    cmap[:, -1] = alpha

    return cmap.astype(np.float32)


def get_colors(
        n_colors: int,
        cmap: str,
        spacing: str = 'uniform',
        alpha: float = 1.0
    ) \
        -> List[Union[np.ndarray, str]]:
    cmap = _get_cmap(cmap, alpha)
    cm_ixs = np.linspace(0, 255, n_colors, dtype=int)
    return np.take(cmap, cm_ixs, axis=0)


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
