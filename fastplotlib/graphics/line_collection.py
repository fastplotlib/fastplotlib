from typing import *
from copy import deepcopy
import weakref
import traceback

import numpy as np
import pygfx

from ._base import Interaction, PreviouslyModifiedData, GraphicCollection
from .features import GraphicFeature
from .line import LineGraphic
from .selectors import LinearRegionSelector, LinearSelector
from ..utils import make_colors, get_cmap, QUALITATIVE_CMAPS, normalize_min_max, parse_cmap_values


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
            alpha: float = 1.0,
            cmap: Union[List[str], str] = None,
            cmap_values: Union[np.ndarray, List] = None,
            name: str = None,
            metadata: Union[list, tuple, np.ndarray] = None,
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

        cmap_values: 1D array-like or list of numerical values, optional
            if provided, these values are used to map the colors from the cmap

        name: str, optional
            name of the line collection

        metadata: list, tuple, or array
            metadata associated with this collection, this is for the user to manage.
            ``len(metadata)`` must be same as ``len(data)``

        args
            passed to GraphicCollection

        kwargs
            passed to GraphicCollection


        Features
        --------

        Collections support the same features as the underlying graphic. You just have to slice the selection.

        .. code-block:: python

            # slice only the collection
            line_collection[10:20].colors = "blue"

            # slice the collection and a feature
            line_collection[20:30].colors[10:30] = "red"

            # the data feature also works like this

        See :class:`LineGraphic` details on the features.


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
            sine2 = np.dstack([xs, ys])[0]

            ys = np.cos(xs) + 5
            cosine = np.dstack([xs, ys])[0]

            # creating plot
            plot = Plot()

            # creating a line collection using the sine and cosine wave data
            line_collection = LineCollection(data=[sine, cosine, sine2], cmap=["Oranges", "Blues", "Reds"], thickness=20.0)

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

        if not isinstance(thickness, (float, int)):
            if len(thickness) != len(data):
                raise ValueError("args must be a single float or an iterable with same length as data")

        if metadata is not None:
            if len(metadata) != len(data):
                raise ValueError(
                    f"len(metadata) != len(data)\n"
                    f"{len(metadata)} != {len(data)}"
                )

        self._cmap_values = cmap_values
        self._cmap_str = cmap

        # cmap takes priority over colors
        if cmap is not None:
            # cmap across lines
            if isinstance(cmap, str):
                colors = parse_cmap_values(
                    n_colors=len(data),
                    cmap_name=cmap,
                    cmap_values=cmap_values
                )
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
                # single color for all lines in the collection as RGBA
                if colors.shape == (4,):
                    single_color = True

                # colors specified for each line as array of shape [n_lines, RGBA]
                elif colors.shape == (len(data), 4):
                    single_color = False

                else:
                    raise ValueError(
                        f"numpy array colors argument must be of shape (4,) or (n_lines, 4)."
                        f"You have pass the following shape: {colors.shape}"
                    )

            elif isinstance(colors, str):
                if colors == "random":
                    colors = np.random.rand(len(data), 4)
                    colors[:, -1] = alpha
                    single_color = False
                else:
                    # parse string color
                    single_color = True
                    colors = pygfx.Color(colors)

            elif isinstance(colors, (tuple, list)):
                if len(colors) == 4:
                    # single color specified as (R, G, B, A) tuple or list
                    if all([isinstance(c, (float, int)) for c in colors]):
                        single_color = True

                elif len(colors) == len(data):
                    # colors passed as list/tuple of colors, such as list of string
                    single_color = False

                else:
                    raise ValueError(
                        "tuple or list colors argument must be a single color represented as [R, G, B, A], "
                        "or must be a tuple/list of colors represented by a string with the same length as the data"
                    )

        self._set_world_object(pygfx.Group())

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

            if metadata is not None:
                _m = metadata[i]
            else:
                _m = None

            lg = LineGraphic(
                data=d,
                thickness=_s,
                colors=_c,
                z_position=_z,
                cmap=_cmap,
                collection_index=i,
                metadata=_m
            )

            self.add_graphic(lg, reset_index=False)

    @property
    def cmap(self) -> str:
        return self._cmap_str

    @cmap.setter
    def cmap(self, cmap: str):
        colors = parse_cmap_values(
            n_colors=len(self),
            cmap_name=cmap,
            cmap_values=self.cmap_values
        )

        for i, g in enumerate(self.graphics):
            g.colors = colors[i]

    @property
    def cmap_values(self) -> np.ndarray:
        return self._cmap_values

    @cmap_values.setter
    def cmap_values(self, values: Union[np.ndarray, list]):
        colors = parse_cmap_values(
            n_colors=len(self),
            cmap_name=self.cmap,
            cmap_values=values

        )

        for i, g in enumerate(self.graphics):
            g.colors = colors[i]

    def add_linear_selector(self, selection: int = None, padding: float = 50, **kwargs) -> LinearSelector:
        """
        Adds a :class:`.LinearSelector` .
        Selectors are just ``Graphic`` objects, so you can manage, remove, or delete them from a plot area just like
        any other ``Graphic``.

        Parameters
        ----------
        selection: int
            initial position of the selector

        padding: float
            pad the length of the selector

        kwargs
            passed to :class:`.LinearSelector`

        Returns
        -------
        LinearSelector

        """

        bounds, limits, size, origin, axis, end_points = self._get_linear_selector_init_args(padding, **kwargs)

        if selection is None:
            selection = limits[0]

        if selection < limits[0] or selection > limits[1]:
            raise ValueError(f"the passed selection: {selection} is beyond the limits: {limits}")

        selector = LinearSelector(
            selection=selection,
            limits=limits,
            end_points=end_points,
            parent=self,
            **kwargs
        )

        self._plot_area.add_graphic(selector, center=False)
        selector.position_z = self.position_z + 1

        return weakref.proxy(selector)

    def add_linear_region_selector(self, padding: float = 100.0, **kwargs) -> LinearRegionSelector:
        """
        Add a :class:`.LinearRegionSelector`
        Selectors are just ``Graphic`` objects, so you can manage, remove, or delete them from a plot area just like
        any other ``Graphic``.

        Parameters
        ----------
        padding: float, default 100.0
            Extends the linear selector along the y-axis to make it easier to interact with.

        kwargs
            passed to ``LinearRegionSelector``

        Returns
        -------
        LinearRegionSelector
            linear selection graphic

        """

        bounds, limits, size, origin, axis, end_points = self._get_linear_selector_init_args(padding, **kwargs)

        selector = LinearRegionSelector(
            bounds=bounds,
            limits=limits,
            size=size,
            origin=origin,
            parent=self,
            **kwargs
        )

        self._plot_area.add_graphic(selector, center=False)
        selector.position_z = self.position_z - 1

        return weakref.proxy(selector)

    def _get_linear_selector_init_args(self, padding, **kwargs):
        bounds_init = list()
        limits = list()
        sizes = list()
        origin = list()
        end_points = list()

        for g in self.graphics:
            _bounds_init, _limits, _size, _origin, axis, _end_points = \
                g._get_linear_selector_init_args(padding=0, **kwargs)

            bounds_init.append(_bounds_init)
            limits.append(_limits)
            sizes.append(_size)
            origin.append(_origin)
            end_points.append(_end_points)

        # set the init bounds using the extents of the collection
        b = np.vstack(bounds_init)
        bounds = (b[:, 0].min(), b[:, 1].max())

        # set the limits using the extents of the collection
        l = np.vstack(limits)
        limits = (l[:, 0].min(), l[:, 1].max())

        # stack endpoints
        end_points = np.vstack(end_points)
        # use the min endpoint for index 0, highest endpoint for index 1
        end_points = [end_points[:, 0].min() - padding, end_points[:, 1].max() + padding]

        # TODO: refactor this to use `LineStack.graphics[-1].position.y`
        if isinstance(self, LineStack):
            stack_offset = self.separation * len(sizes)
            # sum them if it's a stack
            size = sum(sizes)
            # add the separations
            size += stack_offset

            # a better way to get the max y value?
            # graphics y-position + data y-max + padding
            end_points[1] = self.graphics[-1].position_y + self.graphics[-1].data()[:, 1].max() + padding

        else:
            # just the biggest one if not stacked
            size = max(sizes)

        size += padding

        if axis == "x":
            o = np.vstack(origin)
            origin_y = (o[:, 1].min() + o[:, 1].max()) / 2
            origin = (limits[0], origin_y)
        else:
            o = np.vstack(origin)
            origin_x = (o[:, 0].min() + o[:, 0].max()) / 2
            origin = (origin_x, limits[0])

        return bounds, limits, size, origin, axis, end_points

    def _add_plot_area_hook(self, plot_area):
        self._plot_area = plot_area

    def _set_feature(self, feature: str, new_data: Any, indices: Any):
        # if single value force to be an array of size 1
        if isinstance(indices, (np.integer, int)):
            indices = np.array([indices])
        if not hasattr(self, "_previous_data"):
            self._previous_data = dict()
        elif hasattr(self, "_previous_data"):
            if feature in self._previous_data.keys():
                # for now assume same index won't be changed with diff data
                # I can't think of a usecase where we'd have to check the data too
                # so unless there is a bug we keep it like this
                if self._previous_data[feature].indices == indices:
                    return  # nothing to change, and this allows bidirectional linking without infinite recursion

            self._reset_feature(feature)

        # coll_feature = getattr(self[indices], feature)

        data = list()

        for graphic in self.graphics[indices]:
            feature_instance: GraphicFeature = getattr(graphic, feature)
            data.append(feature_instance())

        # later we can think about multi-index events
        previous_data = deepcopy(data[0])

        if feature in self._previous_data.keys():
            self._previous_data[feature].data = previous_data
            self._previous_data[feature].indices = indices
        else:
            self._previous_data[feature] = PreviouslyModifiedData(data=previous_data, indices=indices)

        # finally set the new data
        # this MUST occur after setting the previous data attribute to prevent recursion
        # since calling `feature._set()` triggers all the feature callbacks
        feature_instance._set(new_data)

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


        Features
        --------

        Collections support the same features as the underlying graphic. You just have to slice the selection.

        .. code-block:: python

            # slice only the collection
            line_collection[10:20].colors = "blue"

            # slice the collection and a feature
            line_collection[20:30].colors[10:30] = "red"

            # the data feature also works like this

        See :class:`LineGraphic` details on the features.


        Examples
        --------
        .. code-block:: python

            from fastplotlib import Plot
            from fastplotlib.graphics import LineStack

            # create plot
            plot = Plot()

            # create line data
            xs = np.linspace(-10, 10, 100)
            ys = np.sin(xs)

            sine = np.dstack([xs, ys])[0]

            ys = np.sin(xs)
            cosine = np.dstack([xs, ys])[0]

            # create line stack
            line_stack = LineStack(data=[sine, cosine], cmap=["Oranges", "Blues"], thickness=20.0, separation=5.0)

            # add graphic to plot
            plot.add_graphic(line_stack)

            # show plot
            plot.show()

            # change the color of the sine wave to white
            line_stack[0].colors = "w"

            # change certain color indexes of the cosine data to red
            line_stack[1].colors[0:15] = "r"

            # more slicing
            line_stack[0].colors[35:70] = "magenta"

        """
        super(LineStack, self).__init__(
            data=data,
            z_position=z_position,
            thickness=thickness,
            colors=colors,
            cmap=cmap,
            name=name,
            **kwargs
        )

        axis_zero = 0
        for i, line in enumerate(self.graphics):
            if separation_axis == "x":
                line.position_x = axis_zero
            elif separation_axis == "y":
                line.position_y = axis_zero

            axis_zero = axis_zero + line.data()[:, axes[separation_axis]].max() + separation

        self.separation = separation
