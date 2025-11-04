from typing import *

import numpy as np

import pygfx

from ..utils import parse_cmap_values
from ._collection_base import CollectionIndexer, GraphicCollection, CollectionFeature
from .line import LineGraphic
from .selectors import (
    LinearRegionSelector,
    LinearSelector,
    RectangleSelector,
    PolygonSelector,
)


class _LineCollectionProperties:
    """Mix-in class for LineCollection properties"""

    @property
    def colors(self) -> CollectionFeature:
        """get or set colors of lines in the collection"""
        return CollectionFeature(self.graphics, "colors")

    @colors.setter
    def colors(self, values: str | np.ndarray | tuple[float] | list[float] | list[str]):
        if isinstance(values, str):
            # set colors of all lines to one str color
            for g in self:
                g.colors = values
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
                for g, v in zip(self, values):
                    g.colors = v
                return

        elif len(values) == 4:
            # assume RGBA
            self.colors[:] = values

        else:
            # assume individual colors for each
            for g, v in zip(self, values):
                g.colors = v

    @property
    def data(self) -> CollectionFeature:
        """get or set data of lines in the collection"""
        return CollectionFeature(self.graphics, "data")

    @data.setter
    def data(self, values):
        for g, v in zip(self, values):
            g.data = v

    @property
    def cmap(self) -> CollectionFeature:
        """
        Get or set a cmap along the line collection.

        Optionally set using a tuple ("cmap", <transform>) to set the transform..
        Example:

        line_collection.cmap = ("jet", sine_transform_vals, 0.7)

        """
        return CollectionFeature(self.graphics, "cmap")

    @cmap.setter
    def cmap(self, args):
        if isinstance(args, str):
            name = args
            transform = None
        elif len(args) == 1:
            name = args[0]
            transform = None
        elif len(args) == 2:
            name, transform = args
        else:
            raise ValueError(
                "Too many values for cmap (note that alpha is deprecated, set alpha on the graphic instead)"
            )

        self.colors = parse_cmap_values(
            n_colors=len(self), cmap_name=name, transform=transform
        )

    @property
    def thickness(self) -> np.ndarray:
        """get or set the thickness of the lines"""
        return np.asarray([g.thickness for g in self])

    @thickness.setter
    def thickness(self, values: np.ndarray | list[float]):
        if not len(values) == len(self):
            raise IndexError

        for g, v in zip(self, values):
            g.thickness = v


class LineCollectionIndexer(CollectionIndexer, _LineCollectionProperties):
    """Indexer for line collections"""

    pass


class LineCollection(GraphicCollection, _LineCollectionProperties):
    _child_type = LineGraphic
    _indexer = LineCollectionIndexer

    def __init__(
        self,
        data: np.ndarray | List[np.ndarray],
        thickness: float | Sequence[float] = 2.0,
        colors: str | Sequence[str] | np.ndarray | Sequence[np.ndarray] = "w",
        uniform_colors: bool = False,
        cmap: Sequence[str] | str = None,
        cmap_transform: np.ndarray | List = None,
        name: str = None,
        names: list[str] = None,
        metadata: Any = None,
        metadatas: Sequence[Any] | np.ndarray = None,
        isolated_buffer: bool = True,
        kwargs_lines: list[dict] = None,
        **kwargs,
    ):
        """
        Create a collection of :class:`.LineGraphic`

        Parameters
        ----------
        data: list of array-like
            List or array-like of multiple line data to plot

            | if ``list`` each item in the list must be a 1D, 2D, or 3D numpy array
            | if  array-like, must be of shape [n_lines, n_points_line, y | xy | xyz]

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

        cmap_transform: 1D array-like of numerical values, optional
            if provided, these values are used to map the colors from the cmap

        name: str, optional
            name of the line collection as a whole

        names: list[str], optional
            names of the individual lines in the collection, ``len(names)`` must equal ``len(data)``

        metadata: Any
            meatadata associated with the collection as a whole

        metadatas: Iterable or array
            metadata for each individual line associated with this collection, this is for the user to manage.
            ``len(metadata)`` must be same as ``len(data)``

        kwargs_lines: list[dict], optional
            list of kwargs passed to the individual lines, ``len(kwargs_lines)`` must equal ``len(data)``

        kwargs_collection
            kwargs for the collection, passed to GraphicCollection

        """

        super().__init__(name=name, metadata=metadata, **kwargs)

        if not isinstance(thickness, (float, int)):
            if len(thickness) != len(data):
                raise ValueError(
                    f"len(thickness) != len(data)\n{len(thickness)} != {len(data)}"
                )

        if names is not None:
            if len(names) != len(data):
                raise ValueError(
                    f"len(names) != len(data)\n{len(names)} != {len(data)}"
                )

        if metadatas is not None:
            if len(metadatas) != len(data):
                raise ValueError(
                    f"len(metadata) != len(data)\n{len(metadatas)} != {len(data)}"
                )

        if kwargs_lines is not None:
            if len(kwargs_lines) != len(data):
                raise ValueError(
                    f"len(kwargs_lines) != len(data)\n"
                    f"{len(kwargs_lines)} != {len(data)}"
                )

        self._cmap_transform = cmap_transform
        self._cmap_str = cmap

        # cmap takes priority over colors
        if cmap is not None:
            # cmap across lines
            if isinstance(cmap, str):
                colors = parse_cmap_values(
                    n_colors=len(data), cmap_name=cmap, transform=cmap_transform
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
                if colors.shape in [(3,), (4,)]:
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
                    colors = np.random.rand(len(data), 3)
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

        if kwargs_lines is None:
            kwargs_lines = dict()

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

            if metadatas is not None:
                _m = metadatas[i]
            else:
                _m = None

            if names is not None:
                _name = names[i]
            else:
                _name = None

            lg = LineGraphic(
                data=d,
                thickness=_s,
                colors=_c,
                uniform_color=uniform_colors,
                cmap=_cmap,
                name=_name,
                metadata=_m,
                isolated_buffer=isolated_buffer,
                **kwargs_lines,
            )

            self.add_graphic(lg)

    def __getitem__(self, item) -> LineCollectionIndexer:
        return super().__getitem__(item)

    def add_linear_selector(
        self, selection: float = None, padding: float = 0.0, axis: str = "x", **kwargs
    ) -> LinearSelector:
        """
        Adds a linear selector.

        Parameters
        ----------
        Parameters
        ----------
        selection: float, optional
            selected point on the linear selector, computed from data if not provided

        axis: str, default "x"
            axis that the selector resides on

        padding: float, default 0.0
            Extra padding to extend the linear selector along the orthogonal axis to make it easier to interact with.

        kwargs
            passed to :class:`.LinearSelector`

        Returns
        -------
        LinearSelector

        """

        bounds_init, limits, size, center = self._get_linear_selector_init_args(
            axis, padding
        )

        if selection is None:
            selection = bounds_init[0]

        selector = LinearSelector(
            selection=selection,
            limits=limits,
            axis=axis,
            parent=self,
            **kwargs,
        )

        self._plot_area.add_graphic(selector, center=False)

        return selector

    def add_linear_region_selector(
        self,
        selection: tuple[float, float] = None,
        padding: float = 0.0,
        axis: str = "x",
        **kwargs,
    ) -> LinearRegionSelector:
        """
        Add a :class:`.LinearRegionSelector`. Selectors are just ``Graphic`` objects, so you can manage,
        remove, or delete them from a plot area just like any other ``Graphic``.

        Parameters
        ----------
        selection: (float, float), optional
            the starting bounds of the linear region selector, computed from data if not provided

        axis: str, default "x"
            axis that the selector resides on

        padding: float, default 0.0
            Extra padding to extend the linear region selector along the orthogonal axis to make it easier to interact with.

        kwargs
            passed to ``LinearRegionSelector``

        Returns
        -------
        LinearRegionSelector
            linear selection graphic

        """

        bounds_init, limits, size, center = self._get_linear_selector_init_args(
            axis, padding
        )

        if selection is None:
            selection = bounds_init

        # create selector
        selector = LinearRegionSelector(
            selection=selection,
            limits=limits,
            size=size,
            center=center,
            axis=axis,
            parent=self,
            **kwargs,
        )

        self._plot_area.add_graphic(selector, center=False)

        # PlotArea manages this for garbage collection etc. just like all other Graphics
        # so we should only work with a proxy on the user-end
        return selector

    def add_rectangle_selector(
        self,
        selection: tuple[float, float, float] = None,
        **kwargs,
    ) -> RectangleSelector:
        """
        Add a :class:`.RectangleSelector`. Selectors are just ``Graphic`` objects, so you can manage,
        remove, or delete them from a plot area just like any other ``Graphic``.

        Parameters
        ----------
        selection: (float, float, float, float), optional
            initial (xmin, xmax, ymin, ymax) of the selection
        """
        bbox = self.world_object.get_world_bounding_box()

        xdata = np.array(self.data[:, 0])
        xmin, xmax = (np.nanmin(xdata), np.nanmax(xdata))
        value_25px = (xmax - xmin) / 4

        ydata = np.array(self.data[:, 1])
        ymin = np.floor(ydata.min()).astype(int)

        ymax = np.ptp(bbox[:, 1])

        if selection is None:
            selection = (xmin, value_25px, ymin, ymax)

        limits = (xmin, xmax, ymin - (ymax * 1.5 - ymax), ymax * 1.5)

        selector = RectangleSelector(
            selection=selection,
            limits=limits,
            parent=self,
            **kwargs,
        )

        self._plot_area.add_graphic(selector, center=False)

        return selector

    def add_polygon_selector(
        self,
        selection: List[tuple[float, float]] = None,
        **kwargs,
    ) -> PolygonSelector:
        """
        Add a :class:`.PolygonSelector`. Selectors are just ``Graphic`` objects, so you can manage,
        remove, or delete them from a plot area just like any other ``Graphic``.

        Parameters
        ----------
        selection: List of positions, optional
            Initial points for the polygon. If not given or None, you'll start drawing the selection (clicking adds points to the polygon).
        """
        bbox = self.world_object.get_world_bounding_box()

        xdata = np.array(self.data[:, 0])
        xmin, xmax = (np.nanmin(xdata), np.nanmax(xdata))

        ydata = np.array(self.data[:, 1])
        ymin = np.floor(ydata.min()).astype(int)

        ymax = np.ptp(bbox[:, 1])

        limits = (xmin, xmax, ymin - (ymax * 1.5 - ymax), ymax * 1.5)

        selector = PolygonSelector(
            selection,
            limits,
            parent=self,
            **kwargs,
        )

        self._plot_area.add_graphic(selector, center=False)

        return selector

    def _get_linear_selector_init_args(self, axis, padding):
        # use bbox to get size and center
        bbox = self.world_object.get_world_bounding_box()

        if axis == "x":
            xdata = np.array(self.data[:, 0])
            xmin, xmax = (np.nanmin(xdata), np.nanmax(xdata))
            value_25p = (xmax - xmin) / 4

            bounds = (xmin, value_25p)
            limits = (xmin, xmax)
            # size from orthogonal axis
            size = np.ptp(bbox[:, 1]) * 1.5
            # center on orthogonal axis
            center = bbox[:, 1].mean()

        elif axis == "y":
            ydata = np.array(self.data[:, 1])
            xmin, xmax = (np.nanmin(ydata), np.nanmax(ydata))
            value_25p = (xmax - xmin) / 4

            bounds = (xmin, value_25p)
            limits = (xmin, xmax)

            size = np.ptp(bbox[:, 0]) * 1.5
            # center on orthogonal axis
            center = bbox[:, 0].mean()

        return bounds, limits, size, center


axes = {"x": 0, "y": 1, "z": 2}


class LineStack(LineCollection):
    def __init__(
        self,
        data: List[np.ndarray],
        thickness: float | Iterable[float] = 2.0,
        colors: str | Iterable[str] | np.ndarray | Iterable[np.ndarray] = "w",
        cmap: Iterable[str] | str = None,
        cmap_transform: np.ndarray | List = None,
        name: str = None,
        names: list[str] = None,
        metadata: Any = None,
        metadatas: Sequence[Any] | np.ndarray = None,
        isolated_buffer: bool = True,
        separation: float = 10.0,
        separation_axis: str = "y",
        kwargs_lines: list[dict] = None,
        **kwargs,
    ):
        """
        Create a stack of :class:`.LineGraphic` that are separated along the "x" or "y" axis.

        Parameters
        ----------
        data: list of array-like
            List or array-like of multiple line data to plot

            | if ``list`` each item in the list must be a 1D, 2D, or 3D numpy array
            | if  array-like, must be of shape [n_lines, n_points_line, y | xy | xyz]

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

        cmap_transform: 1D array-like of numerical values, optional
            if provided, these values are used to map the colors from the cmap

        name: str, optional
            name of the line collection as a whole

        names: list[str], optional
            names of the individual lines in the collection, ``len(names)`` must equal ``len(data)``

        metadata: Any
            metadata associated with the collection as a whole

        metadatas: Iterable or array
            metadata for each individual line associated with this collection, this is for the user to manage.
            ``len(metadata)`` must be same as ``len(data)``

        separation: float, default 10
            space in between each line graphic in the stack

        separation_axis: str, default "y"
            axis in which the line graphics in the stack should be separated


        kwargs_lines: list[dict], optional
            list of kwargs passed to the individual lines, ``len(kwargs_lines)`` must equal ``len(data)``

        kwargs_collection
            kwargs for the collection, passed to GraphicCollection

        """
        super().__init__(
            data=data,
            thickness=thickness,
            colors=colors,
            cmap=cmap,
            cmap_transform=cmap_transform,
            name=name,
            names=names,
            metadata=metadata,
            metadatas=metadatas,
            isolated_buffer=isolated_buffer,
            kwargs_lines=kwargs_lines,
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
