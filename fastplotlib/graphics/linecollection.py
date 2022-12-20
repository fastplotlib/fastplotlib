import numpy as np
import pygfx
from typing import Union, List

from fastplotlib.graphics.line import LineGraphic
from typing import *
from fastplotlib.graphics._base import Interaction
from abc import ABC, abstractmethod


<<<<<<< HEAD
class LineCollection():
    def __init__(self, data: List[np.ndarray], z_position: Union[List[float], float] = None, size: Union[float, List[float]] = 2.0, colors: Union[List[np.ndarray], np.ndarray] = None,
=======
class LineCollection(Interaction):
    def __init__(self, data: List[np.ndarray], zlevel: Union[List[float], float] = None, size: Union[float, List[float]] = 2.0, colors: Union[List[np.ndarray], np.ndarray] = None,
>>>>>>> 16922e7 (git is so agitating sometimes)
                 cmap: Union[List[str], str] = None, *args, **kwargs):

        if not isinstance(z_position, float) and z_position is not None:
            if not len(data) == len(z_position):
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

        self.data = list()

        for i, d in enumerate(data):
            if isinstance(z_position, list):
                _z = z_position[i]
            else:
                _z = z_position

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

            self.data.append(LineGraphic(d, _z, _size, _colors, _cmap))

    @property
    def features(self) -> List[str]:
        return ["colors", "data"]

    def _set_feature(self, feature: str, new_data: Any, indices: Any):
        if feature in self.features:
            update_func = getattr(self.data[indices], f"update_{feature}")
            # if indices is a single indices or list of indices
            self.data[indices].update_colors(new_data)
        else:
            raise ValueError("name arg is not a valid feature")

    def _reset_feature(self, feature: str, old_data: Any):
        if feature in self.features:
            #update_func = getattr(self, f"update_{feature}")
            for i, line in enumerate(self.data):
                line.update_colors(old_data[i])
        else:
            raise ValueError("name arg is not a valid feature")

    def __getitem__(self, item):
        return self.data[item]



