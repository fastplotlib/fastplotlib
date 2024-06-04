from typing import *
import weakref

import numpy as np

import pygfx

from ..utils import parse_cmap_values
from ._base import GraphicCollection, CollectionIndexer, CollectionFeature
from .line import LineGraphic
from .selectors import LinearRegionSelector, LinearSelector


class LineSelection(CollectionIndexer):
    @property
    def colors(self) -> CollectionFeature:
        return CollectionFeature(self.graphics, "colors")

    @colors.setter
    def colors(self, values: str | np.ndarray | tuple[float] | list[float] | list[str]):
        if isinstance(values, str):
            # set colors of all lines to one str color
            self.colors[:] = values
            return

        elif all(isinstance(v, str) for v in values):
            # individual str colors for each line
            if not len(values) == len(self):
                raise IndexError

            for g, v in zip(self.graphics, values):
                g.colors = v

            return

        if isinstance(values, np.ndarray):
            if values.ndim == 2:
                # assume individual colors for each
                for g, v in zip(self.graphics, values):
                    g.colors = v
                return

        elif len(values) == 4:
            # assume RGBA
            self.colors[:] = values

        else:
            # assume individual colors for each
            for g, v in zip(self.graphics, values):
                g.colors = v

    @property
    def data(self) -> CollectionFeature:
        return CollectionFeature(self.graphics, "data")

    @data.setter
    def data(self, values):
        self.data[:] = values

    @property
    def cmap(self) -> CollectionFeature:
        return CollectionFeature(self.graphics, "cmap")

    @cmap.setter
    def cmap(self, name: str):
        colors = parse_cmap_values(n_colors=len(self), cmap_name=name)
        self.colors = colors

    @property
    def thickness(self) -> np.ndarray:
        return np.asarray([g.thickness for g in self.graphics])

    @thickness.setter
    def thickness(self, values: np.ndarray | list[float]):
        if not len(values) == len(self):
            raise IndexError

        for g, v in zip(self.graphics, values):
            g.thickness = v


class LineCollection(GraphicCollection):
    child_type = LineGraphic
    _indexer = LineSelection

    def __init__(
        self,
        data: List[np.ndarray],
        thickness: float | Sequence[float] = 2.0,
        colors: str | Sequence[str] | np.ndarray | Sequence[np.ndarray] = "w",
        uniform_colors: bool = False,
        alpha: float = 1.0,
        cmap: Sequence[str] | str = None,
        cmap_values: np.ndarray | List = None,
        name: str = None,
        metadata: Sequence[Any] | np.ndarray = None,
        isolated_buffer: bool = True,
        **kwargs,
    ):
        """
        Create a collection of :class:`.LineGraphic`

        Parameters
        ----------
        data: list of array-like or array
            List of line data to plot, each element must be a 1D, 2D, or 3D numpy array
            if elements are 2D, interpreted as [y_vals, n_lines]

        thickness: float or Iterable of float, default 2.0
            | if ``float``, single thickness will be used for all lines
            | if ``list`` of ``float``, each value will apply to the individual lines

        colors: str, RGBA array, Iterable of RGBA array, or Iterable of str, default "w"
            | if single ``str`` such as "w", "r", "b", etc, represents a single color for all lines
            | if single ``RGBA array`` (tuple or list of size 4), represents a single color for all lines
            | if ``list`` of ``str``, represents color for each individual line, example ["w", "b", "r",...]
            | if ``RGBA array`` of shape [data_size, 4], represents a single RGBA array for each line

        alpha: float, optional
            alpha value for colors, if colors is a ``str``

        cmap: Iterable of str or str, optional
            | if ``str``, single cmap will be used for all lines
            | if ``list`` of ``str``, each cmap will apply to the individual lines

            .. note::
                ``cmap`` overrides any arguments passed to ``colors``

        cmap_values: 1D array-like or Iterable of numerical values, optional
            if provided, these values are used to map the colors from the cmap

        name: str, optional
            name of the line collection

        metadata: Iterable or array
            metadata associated with this collection, this is for the user to manage.
            ``len(metadata)`` must be same as ``len(data)``

        kwargs
            passed to Graphic

        Features
        --------

        Collections support the same features as the underlying graphic. You just have to slice the selection.

        See :class:`LineGraphic` details on the features.

        """

        super().__init__(name)

        if not isinstance(thickness, (float, int)):
            if len(thickness) != len(data):
                raise ValueError(
                    "args must be a single float or an iterable with same length as data"
                )

        if metadata is not None:
            if len(metadata) != len(data):
                raise ValueError(
                    f"len(metadata) != len(data)\n" f"{len(metadata)} != {len(data)}"
                )

        self._cmap_values = cmap_values
        self._cmap_str = cmap

        # cmap takes priority over colors
        if cmap is not None:
            # cmap across lines
            if isinstance(cmap, str):
                colors = parse_cmap_values(
                    n_colors=len(data), cmap_name=cmap, cmap_values=cmap_values
                )
                single_color = False
                cmap = None

            elif isinstance(cmap, (tuple, list)):
                if len(cmap) != len(data):
                    raise ValueError(
                        "cmap argument must be a single cmap or a list of cmaps "
                        "with the same length as the data"
                    )
                single_color = False
            else:
                raise ValueError(
                    "cmap argument must be a single cmap or a list of cmaps "
                    "with the same length as the data"
                )
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
                uniform_colors=uniform_colors,
                cmap=_cmap,
                metadata=_m,
                isolated_buffer=isolated_buffer,
                **kwargs,
            )

            self.add_graphic(lg)

    @property
    def cmap(self) -> str:
        return self._cmap_str

    @cmap.setter
    def cmap(self, cmap: str):
        colors = parse_cmap_values(
            n_colors=len(self), cmap_name=cmap, cmap_values=self.cmap_values
        )

        for i, g in enumerate(self.graphics):
            g.colors = colors[i]

        self._cmap_str = cmap

    @property
    def cmap_values(self) -> np.ndarray:
        return self._cmap_values

    @cmap_values.setter
    def cmap_values(self, values: np.ndarray | Iterable):
        colors = parse_cmap_values(
            n_colors=len(self), cmap_name=self.cmap, cmap_values=values
        )

        for i, g in enumerate(self.graphics):
            g.colors = colors[i]

        self._cmap_values = values

    def add_linear_selector(
        self, selection: int = None, padding: float = 50, **kwargs
    ) -> LinearSelector:
        """
        Adds a :class:`.LinearSelector` .

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
        # TODO: Use bbox to get size and center for selectors!

        (
            bounds,
            limits,
            size,
            origin,
            axis,
            end_points,
        ) = self._get_linear_selector_init_args(padding, **kwargs)

        if selection is None:
            selection = limits[0]

        if selection < limits[0] or selection > limits[1]:
            raise ValueError(
                f"the passed selection: {selection} is beyond the limits: {limits}"
            )

        selector = LinearSelector(
            selection=selection,
            limits=limits,
            end_points=end_points,
            parent=self,
            **kwargs,
        )

        self._plot_area.add_graphic(selector, center=False)
        selector.position_z = self.position_z + 1

        return weakref.proxy(selector)

    def add_linear_region_selector(
        self, padding: float = 100.0, **kwargs
    ) -> LinearRegionSelector:
        """
        Add a :class:`.LinearRegionSelector`

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

        (
            bounds,
            limits,
            size,
            origin,
            axis,
            end_points,
        ) = self._get_linear_selector_init_args(padding, **kwargs)

        selector = LinearRegionSelector(
            selection=bounds,
            limits=limits,
            size=size,
            origin=origin,
            parent=self,
            **kwargs,
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
            (
                _bounds_init,
                _limits,
                _size,
                _origin,
                axis,
                _end_points,
            ) = g._get_linear_selector_init_args(padding=0, **kwargs)

            bounds_init.append(_bounds_init)
            limits.append(_limits)
            sizes.append(_size)
            origin.append(_origin)
            end_points.append(_end_points)

        # set the init bounds using the extents of the collection
        b = np.vstack(bounds_init)
        bounds = (b[:, 0].min(), b[:, 1].max())

        # set the limits using the extents of the collection
        limits = np.vstack(limits)
        limits = (limits[:, 0].min(), limits[:, 1].max())

        # stack endpoints
        end_points = np.vstack(end_points)
        # use the min endpoint for index 0, highest endpoint for index 1
        end_points = [
            end_points[:, 0].min() - padding,
            end_points[:, 1].max() + padding,
        ]

        # TODO: refactor this to use `LineStack.graphics[-1].position.y`
        if isinstance(self, LineStack):
            stack_offset = self.separation * len(sizes)
            # sum them if it's a stack
            size = sum(sizes)
            # add the separations
            size += stack_offset

            # a better way to get the max y value?
            # graphics y-position + data y-max + padding
            end_points[1] = (
                self.graphics[-1].position_y
                + self.graphics[-1].data()[:, 1].max()
                + padding
            )

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


axes = {"x": 0, "y": 1, "z": 2}


class LineStack(LineCollection):
    def __init__(
        self,
        data: List[np.ndarray],
        thickness: float | Iterable[float] = 2.0,
        colors: str | Iterable[str] | np.ndarray | Iterable[np.ndarray] = "w",
        alpha: float = 1.0,
        cmap: Iterable[str] | str = None,
        cmap_values: np.ndarray | List = None,
        name: str = None,
        metadata: Iterable[Any] | np.ndarray = None,
        separation: float = 10.0,
        separation_axis: str = "y",
        **kwargs,
    ):
        """
        Create a stack of :class:`.LineGraphic` that are separated along the "x" or "y" axis.

        Parameters
        ----------
        data: list of array-like or array
            List of line data to plot, each element must be a 1D, 2D, or 3D numpy array
            if elements are 2D, interpreted as [y_vals, n_lines]

        thickness: float or Iterable of float, default 2.0
            | if ``float``, single thickness will be used for all lines
            | if ``list`` of ``float``, each value will apply to the individual lines

        colors: str, RGBA array, Iterable of RGBA array, or Iterable of str, default "w"
            | if single ``str`` such as "w", "r", "b", etc, represents a single color for all lines
            | if single ``RGBA array`` (tuple or list of size 4), represents a single color for all lines
            | if ``list`` of ``str``, represents color for each individual line, example ["w", "b", "r",...]
            | if ``RGBA array`` of shape [data_size, 4], represents a single RGBA array for each line

        cmap: Iterable of str or str, optional
            | if ``str``, single cmap will be used for all lines
            | if ``list`` of ``str``, each cmap will apply to the individual lines

            .. note::
                ``cmap`` overrides any arguments passed to ``colors``

        cmap_values: 1D array-like or Iterable of numerical values, optional
            if provided, these values are used to map the colors from the cmap

        metadata: Iterable or array
            metadata associated with this collection, this is for the user to manage.
            ``len(metadata)`` must be same as ``len(data)``

        separation: float, default 10
            space in between each line graphic in the stack

        separation_axis: str, default "y"
            axis in which the line graphics in the stack should be separated

        name: str, optional
            name of the line stack

        kwargs
            passed to LineCollection

        Features
        --------

        Collections support the same features as the underlying graphic. You just have to slice the selection.

        See :class:`LineGraphic` details on the features.

        """
        super().__init__(
            data=data,
            thickness=thickness,
            colors=colors,
            alpha=alpha,
            cmap=cmap,
            cmap_values=cmap_values,
            name=name,
            metadata=metadata,
            **kwargs,
        )

        axis_zero = 0
        for i, line in enumerate(self.graphics):
            if separation_axis == "x":
                line.offset = (axis_zero, *line.offset[1:])

            elif separation_axis == "y":
                line.offset = (line.offset[0], axis_zero, line.offset[2])

            axis_zero = (
                axis_zero + line.data.value[:, axes[separation_axis]].max() + separation
            )

        self.separation = separation
