import numpy as np
import pygfx
from typing import *

from ._base import Interaction, PreviouslyModifiedData, GraphicCollection
from .line import LineGraphic
from ..utils import get_colors
from copy import deepcopy


class LineCollection(GraphicCollection, Interaction):
    """Line Collection graphic"""
    child_type = LineGraphic
    feature_events = [
        "data",
        "colors",
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

    def _set_feature(self, feature: str, new_data: Any, indices: Any):
        if not hasattr(self, "_previous_data"):
            self._previous_data = dict()
        elif hasattr(self, "_previous_data"):
            self._reset_feature(feature)

        coll_feature = getattr(self[indices], feature)

        data = list()
        for fea in coll_feature._feature_instances:
            data.append(fea._data)

        # later we can think about multi-index events
        previous = deepcopy(data[0])
        coll_feature._set(new_data)

        if feature in self._previous_data.keys():
            self._previous_data[feature].data = previous
            self._previous_data[feature].indices = indices
        else:
            self._previous_data[feature] = PreviouslyModifiedData(data=previous, indices=indices)

    def _reset_feature(self, feature: str):
        # implemented for a single index at moment
        prev_ixs = self._previous_data[feature].indices
        coll_feature = getattr(self[prev_ixs], feature)

        coll_feature.block_events(True)
        coll_feature._set(self._previous_data[feature].data)
        coll_feature.block_events(False)