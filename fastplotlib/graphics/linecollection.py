import numpy as np
import pygfx
from typing import Union
from .line import LineGraphic
from typing import *


class LineCollection():
    def __init__(self, data: List[np.ndarray], zlevel: Union[List[float], float] = None, size: Union[float, List[float]] = 2.0, colors: Union[List[np.ndarray], np.ndarray] = None,
                 cmap: Union[List[str], str] = None, *args, **kwargs):

        if not isinstance(zlevel, float) and zlevel is not None:
            if not len(data) == len(zlevel):
                raise ValueError("args must be the same length")
        if not isinstance(size, float):
            if not len(size) == len(data):
                raise ValueError("args must be the same length")
        if not isinstance(colors, np.ndarray) and colors is not None:
            if not len(data) == len(colors):
                raise ValueError("args must be the same length")
        if not isinstance(cmap, str) and cmap is not None:
            if not len(data) == len(cmap):
                raise ValueError("args must be the same length")

        self.collection = list()

        for i, d in enumerate(data):
            if isinstance(zlevel, list):
                _zlevel = zlevel[i]
            else:
                _zlevel = zlevel

            if isinstance(size, list):
                _size = size[i]
            else:
                _size = size

            if isinstance(colors, list):
                _colors = colors[i]
            else:
                _colors = colors

            if isinstance(cmap, list):
                _cmap = cmap[i]
            else:
                _cmap = cmap

            self.collection.append(LineGraphic(d, _zlevel, _size, _colors, _cmap))

    def __getitem__(self, item):
        return self.collection[item]



