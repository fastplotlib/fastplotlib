import numpy as np
import pygfx
from typing import *

from ._base import Interaction, PreviouslyModifiedData, GraphicCollection
from .line import LineGraphic
from ..utils import make_colors
from copy import deepcopy


class LineCollection(GraphicCollection, Interaction):
    child_type = LineGraphic
    feature_events = (
        "data",
        "colors",
        "cmap",
        "thickness",
        "present"
    )

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

        data: list of array-like or array
            List of line data to plot, each element must be a 1D, 2D, or 3D numpy array
            if elements are 2D, interpreted as [y_vals, n_lines]

        z_position: list of float or float, optional
            | if ``float``, single position will be used for all lines
            | if ``list`` of ``float``, each value will apply to the individual lines

        thickness: float or list of float, default 2.0
            | if ``float``, single thickness will be used for all lines
            | if ``list`` of ``float``, each value will apply to the individual lines

        colors: str, RGBA array, list of RGBA array, or list of str, default "w"
            | if single ``str`` such as "w", "r", "b", etc, represents a single color for all lines
            | if single ``RGBA array`` (tuple or list of size 4), represents a single color for all lines
            | if ``list`` of ``str``, represents color for each individual line, example ["w", "b", "r",...]
            | if ``RGBA array`` of shape [data_size, 4], represents a single RGBA array for each line

        cmap: list of str or str, optional
            | if ``str``, single cmap will be used for all lines
            | if ``list`` of ``str``, each cmap will apply to the individual lines
            **Note:** ``cmap`` overrides any arguments passed to ``colors``

        name: str, optional
            name of the line collection

        args
            passed to GraphicCollection

        kwargs
            passed to GraphicCollection

        Examples
        --------
        .. code-block:: python

            from fastplotlib import Plot
            from fastplotlib.graphics import LineCollection
            # creating data for sine and cosine waves
            xs = np.linspace(-10, 10, 100)
            ys = np.sin(xs)
            sine = np.dstack([xs, ys])[0]
            ys = np.sin(xs) + 10
            ys = np.cos(xs) + 5
            sine2 = np.dstack([xs, ys])[0]
            cosine = np.dstack([xs, ys])[0]
            # creating plot
            plot = Plot()
            # creating a line collection using the sine and cosine wave data
            line_collection = LineCollection(data=[sine, cosine, sine2], cmap=["Oranges", "Blues"], thickness=20.0)
            # add graphic to plot
            plot.add_graphic(line_collection)
            # show plot
            plot.show()
            # change the color of the sine wave to white
            line_collection[0].colors = "w"
            # change certain color indexes of the cosine data to red
            line_collection[1].colors[0:15] = "r"
            # toggle presence of sine2 and rescale graphics
            line_collection[2].present = False
            plot.autoscale()
            line_collection[2].present = True
            plot.autoscale()
            # can also do slicing
            line_collection[1:].colors[35:70] = "magenta"
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
            List of line data to plot, each element must be a 1D, 2D, or 3D numpy array
            if elements are 2D, interpreted as [y_vals, n_lines]

        z_position: list of float or float, optional
            | if ``float``, single position will be used for all lines
            | if ``list`` of ``float``, each value will apply to individual lines

        thickness: float or list of float, default 2.0
            | if ``float``, single thickness will be used for all lines
            | if ``list`` of ``float``, each value will apply to the individual lines

        colors: str, RGBA array, list of RGBA array, or list of str, default "w"
            | if single ``str`` such as "w", "r", "b", etc, represents a single color for all lines
            | if single ``RGBA array`` (tuple or list of size 4), represents a single color for all lines
            | is ``list`` of ``str``, represents color for each individual line, example ["w", "b", "r",...]
            | if ``list`` of ``RGBA array`` of shape [data_size, 4], represents a single RGBA array for each line

        cmap: list of str or str, optional
            | if ``str``, single cmap will be used for all lines
            | if ``list`` of ``str``, each cmap will apply to the individual lines
            **Note:** ``cmap`` overrides any arguments passed to ``colors``

        name: str, optional
            name of the line stack

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

        Examples
        --------


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
