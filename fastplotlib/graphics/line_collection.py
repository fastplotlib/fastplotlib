import numpy as np
import pygfx
from typing import *

from ._base import Interaction, PreviouslyModifiedData, GraphicCollection
from .line import LineGraphic
from ..utils import make_colors
from copy import deepcopy


class LineCollection(GraphicCollection, Interaction):
    child_type = LineGraphic
    feature_events = [
        "data",
        "colors",
        "cmap",
        "thickness",
        "present"
    ]

    def __init__(
            self,
            data: List[np.ndarray],
            z_position: Union[List[float], float] = None,
            thickness: Union[float, List[float]] = 2.0,
            colors: Union[List[np.ndarray], np.ndarray] = "w",
            cmap: Union[List[str], str] = None,
            name: str = None,
            *args,
            **kwargs
    ):
        """
        Create a Line Collection

        Parameters
        ----------
        data: list of array-like
            List of line data to plot, if elements 2D must be of shape [n_points, 2], if elements
            3D must be of shape [n_points, 3]

        z_position: list of float or float, optional
            z-axis position for each line graphic, single value will apply to
            all line graphics in the collection

        thickness: float or list of float, default 2.0
            thickness of each line in the collection, sinlge value will apply to
            all line graphics in the collection

        colors: list array or array, default "w"
            specify color for each line graphic as a list of RGBA arrays or a single
            RGBA array that will apply to all line graphics in the collection

        cmap: list of str or str, optional
            apply colormap to each individual line in the collection instead of passing
            colors manually, single str will apply same cmap to all lines in the collection,
            overrides any arguments passed to "colors"

        name: str, optional
            name of the line collection

        args
            passed to GraphicCollection

        kwargs
            passed to GraphicCollection
        """
        super(LineCollection, self).__init__(name)

        if not isinstance(z_position, float) and z_position is not None:
            if len(data) != len(z_position):
                raise ValueError("z_position must be a single float or an iterable with same length as data")

        if not isinstance(thickness, float):
            if len(thickness) != len(data):
                raise ValueError("args must be a single float or an iterable with same length as data")

        # cmap takes priority over colors
        if cmap is not None:
            # cmap across lines
            if isinstance(cmap, str):
                colors = make_colors(len(data), cmap)
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

            if isinstance(thickness, list):
                _s = thickness[i]
            else:
                _s = thickness

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
                thickness=_s,
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
            if feature in self._previous_data.keys():
                # for now assume same index won't be changed with diff data
                # I can't think of a usecase where we'd have to check the data too
                # so unless there is bug we keep it like this
                if self._previous_data[feature].indices == indices:
                    return  # nothing to change, and this allows bidirectional linking without infinite recusion

            self._reset_feature(feature)

        coll_feature = getattr(self[indices], feature)

        data = list()
        for fea in coll_feature._feature_instances:
            data.append(fea._data)

        # later we can think about multi-index events
        previous = deepcopy(data[0])

        if feature in self._previous_data.keys():
            self._previous_data[feature].data = previous
            self._previous_data[feature].indices = indices
        else:
            self._previous_data[feature] = PreviouslyModifiedData(data=previous, indices=indices)

        # finally set the new data
        # this MUST occur after setting the previous data attribute to prevent recursion
        # since calling `feature._set()` triggers all the feature callbacks
        coll_feature._set(new_data)

    def _reset_feature(self, feature: str):
        if feature not in self._previous_data.keys():
            return

        # implemented for a single index at moment
        prev_ixs = self._previous_data[feature].indices
        coll_feature = getattr(self[prev_ixs], feature)

        coll_feature.block_events(True)
        coll_feature._set(self._previous_data[feature].data)
        coll_feature.block_events(False)


axes = {
    "x": 0,
    "y": 1,
    "z": 2
}


class LineStack(LineCollection):
    def __init__(
            self,
            data: List[np.ndarray],
            z_position: Union[List[float], float] = None,
            thickness: Union[float, List[float]] = 2.0,
            colors: Union[List[np.ndarray], np.ndarray] = "w",
            cmap: Union[List[str], str] = None,
            separation: float = 10,
            separation_axis: str = "y",
            name: str = None,
            *args,
            **kwargs
    ):
        """
        Create a line stack

        Parameters
        ----------
        data: list of array-like
            List of line data to plot, if elements 2D must be of shape [n_points, 2], if elements
            3D must be of shape [n_points, 3]

        z_position: list of float or float, optional
            z-axis position for each line graphic, single value will apply to
            all line graphics in the stack

        thickness: float or list of float, default 2.0
            thickness of each line in the collection, sinlge value will apply to
            all line graphics in the stack

        colors: list array or array, default "w"
            specify color for each line graphic as a list of RGBA arrays or a single
            RGBA array that will apply to all line graphics in the stack

        cmap: list of str or str, optional
            apply colormap to each individual line in the stack instead of passing
            colors manually, single str will apply same cmap to all lines in the stack,
            overrides any arguments passed to "colors"

        separation: float, default 10
            space in between each line graphic in the stack

        separation_axis: str, default "y"
            axis in which the line graphics in the stack should be separated

        name: str, optional
            name of the line stack

        args
            passed to LineCollection

        kwargs
            passed to LineCollection
        """
        super(LineStack, self).__init__(
            data=data,
            z_position=z_position,
            thickness=thickness,
            colors=colors,
            cmap=cmap,
            name=name
        )

        axis_zero = 0
        for i, line in enumerate(self._graphics):
            getattr(line.position, f"set_{separation_axis}")(axis_zero)
            axis_zero = axis_zero + line.data()[:, axes[separation_axis]].max() + separation
