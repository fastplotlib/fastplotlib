import numpy as np
import pygfx
from typing import *

from ._base import Interaction, PreviouslyModifiedData
from ._collection import GraphicCollection
from .line import LineGraphic
from ..utils import get_colors
from typing import *


class LineCollection(GraphicCollection, Interaction):
    """Line Collection graphic"""
    child_type = LineGraphic
    feature_events = [
        "data-changed",
        "color-changed",
        "cmap-changed",
    ]
    def __init__(
            self,
            data: List[np.ndarray],
            z_position: Union[List[float], float] = None,
            size: Union[float, List[float]] = 2.0,
            colors: Union[List[np.ndarray], np.ndarray] = "w",
            cmap: Union[List[str], str] = None,
            name: str = None,
            *args,
            **kwargs
    ):
        super(LineCollection, self).__init__(name)

        if not isinstance(z_position, float) and z_position is not None:
            if len(data) != len(z_position):
                raise ValueError("z_position must be a single float or an iterable with same length as data")

        if not isinstance(size, float):
            if len(size) != len(data):
                raise ValueError("args must be a single float or an iterable with same length as data")

        # cmap takes priority over colors
        if cmap is not None:
            # cmap across lines
            if isinstance(cmap, str):
                colors = get_colors(len(data), cmap)
                single_color = False
                cmap = None
            elif isinstance(cmap, (tuple, list)):
                if len(cmap) != len(data):
                    raise ValueError("cmap argument must be a single cmap or a list of cmaps "
                                     "with the same length as the data")
                single_color = False
            else:
                raise ValueError("cmap argument must be a single cmap or a list of cmaps "
                                 "with the same length as the data")
        else:
            if isinstance(colors, np.ndarray):
                if colors.shape == (4,):
                    single_color = True

                elif colors.shape == (len(data), 4):
                    single_color = False

                else:
                    raise ValueError(
                        "numpy array colors argument must be of shape (4,) or (len(data), 4)"
                    )

            elif isinstance(colors, str):
                single_color = True
                colors = pygfx.Color(colors)

            elif isinstance(colors, (tuple, list)):
                if len(colors) == 4:
                    if all([isinstance(c, (float, int)) for c in colors]):
                        single_color = True

                elif len(colors) == len(data):
                    single_color = False

                else:
                    raise ValueError(
                        "tuple or list colors argument must be a single color represented as [R, G, B, A], "
                        "or must be a str of tuple/list with the same length as the data"
                    )

        self._world_object = pygfx.Group()

        for i, d in enumerate(data):
            if isinstance(z_position, list):
                _z = z_position[i]
            else:
                _z = 1.0

            if isinstance(size, list):
                _s = size[i]
            else:
                _s = size

            if cmap is None:
                _cmap = None

                if single_color:
                    _c = colors
                else:
                    _c = colors[i]
            else:
                _cmap = cmap[i]
                _c = None

            lg = LineGraphic(
                data=d,
                size=_s,
                colors=_c,
                z_position=_z,
                cmap=_cmap,
                collection_index=i
            )

            self.add_graphic(lg, reset_index=False)

    def _set_feature(self, feature: str, new_data: Any, indices: Union[int, range]):
        if not hasattr(self, "_previous_data"):
            self._previous_data = {}
        elif hasattr(self, "_previous_data"):
            self._reset_feature(feature)
        #if feature in # need a way to check if feature is in
        feature_instance = getattr(self, feature)
        if indices is not None:
            previous = feature_instance[indices].copy()
            feature_instance[indices] = new_data
        else:
            previous = feature_instance[:].copy()
            feature_instance[:] = new_data
        if feature in self._previous_data.keys():
            self._previous_data[feature].previous_data = previous
            self._previous_data[feature].previous_indices = indices
        else:
            self._previous_data[feature] = PreviouslyModifiedData(previous_data=previous, previous_indices=indices)
        # else:
        #     raise ValueError("name arg is not a valid feature")

    def _reset_feature(self, feature: str):
        if feature not in self._previous_data.keys():
            raise ValueError("no previous data registered for this feature")
        else:
            feature_instance = getattr(self, feature)
            if self._previous_data[feature].previous_indices is not None:
                feature_instance[self._previous_data[feature].previous_indices] = self._previous_data[
                    feature].previous_data
            else:
                feature_instance[:] = self._previous_data[feature].previous_data