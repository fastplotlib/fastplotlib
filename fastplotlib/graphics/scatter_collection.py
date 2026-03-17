from itertools import repeat
from numbers import Number
from typing import *

import numpy as np

import pygfx

from ..utils import parse_cmap_values
from ._collection_base import CollectionIndexer, GraphicCollection, CollectionFeature
from .scatter import ScatterGraphic
from .selectors import (
    LinearRegionSelector,
    LinearSelector,
    RectangleSelector,
    PolygonSelector,
)


class _ScatterCollectionProperties:
    """Mix-in class for ScatterCollection properties"""

    @property
    def colors(self) -> CollectionFeature:
        """get or set colors of scatters in the collection"""
        return CollectionFeature(self.graphics, "colors")

    @colors.setter
    def colors(self, values: str | np.ndarray | tuple[float] | list[float] | list[str]):
        if isinstance(values, str):
            # set colors of all scatter to one str color
            for g in self:
                g.colors = values
            return

        elif all(isinstance(v, str) for v in values):
            # individual str colors for each scatter
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
        """get or set data of scatters in the collection"""
        return CollectionFeature(self.graphics, "data")

    @data.setter
    def data(self, values):
        for g, v in zip(self, values):
            g.data = v

    @property
    def cmap(self) -> CollectionFeature:
        """
        Get or set a cmap along the scatter collection.

        Optionally set using a tuple ("cmap", <transform>) to set the transform.
        Example:

        scatter_collection.cmap = ("jet", sine_transform_vals, 0.7)

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
    def markers(self) -> CollectionFeature:
        """get or set markers of scatters in the collection"""
        return CollectionFeature(self.graphics, "markers")

    @markers.setter
    def markers(self, values: str | Sequence[str]):
        if isinstance(values, str):
            values = repeat(values, len(self))

        elif len(values) != len(self):
            raise IndexError("len(markers) must be the same as the number of ScatterGraphics in the collection")

        for g, v in zip(self, values):
            g.markers = v

    @property
    def sizes(self) -> CollectionFeature:
        """get or set sizes of scatter points in the collection"""
        return CollectionFeature(self.graphics, "sizes")

    @sizes.setter
    def sizes(self, values):
        if isinstance(values, Number):
            values = repeat(values, len(self))

        elif len(values) != len(self):
            raise IndexError("len(sizes) must be the same as the number of ScatterGraphics in the collection")

        for g, v in zip(self, values):
            g.sizes = v


class ScatterCollectionIndexer(CollectionIndexer, _ScatterCollectionProperties):
    """Indexer for scatter collections"""
    pass


class ScatterCollection(GraphicCollection, _ScatterCollectionProperties):
    _child_type = ScatterGraphic
    _indexer = ScatterCollectionIndexer

    def __init__(
        self,
        data: np.ndarray | List[np.ndarray],
        colors: str | Sequence[str] | np.ndarray | Sequence[np.ndarray] = "w",
        cmap: Sequence[str] | str = None,
        cmap_transform: np.ndarray | List = None,
        sizes: float | Sequence[float] = 5.0,
        uniform_size: bool = True,
        markers: np.ndarray | Sequence[str] = None,
        uniform_marker: bool = True,
        edge_width: float = 1.0,
        name: str = None,
        names: list[str] = None,
        metadata: Any = None,
        metadatas: Sequence[Any] | np.ndarray = None,
        **kwargs,
    ):
        """
        Create a collection of :class:`.ScatterGraphic`

        Parameters
        ----------
        data: list of array-like
            List or array-like of multiple line data to plot

            | if ``list`` each item in the list must be a 1D, 2D, or 3D numpy array
            | if  array-like, must be of shape [n_lines, n_points_line, y | xy | xyz]

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

        self._set_world_object(pygfx.Group())

        for i, d in enumerate(data):
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

            if markers is not None:
                if isinstance(markers, (tuple, list, np.ndarray)):
                    markers_ = markers[i]
                else:
                    markers_ = markers
            else:
                markers_ = "o"

            if sizes is not None:
                if isinstance(sizes, (tuple, list, np.ndarray)):
                    sizes_ = sizes[i]
                else:
                    sizes_ = sizes
            else:
                sizes_ = 5

            lg = ScatterGraphic(
                data=d,
                colors=_c,
                sizes=sizes_,
                markers=markers_,
                cmap=_cmap,
                name=_name,
                metadata=_m,
                uniform_marker=uniform_marker,
                uniform_size=uniform_size,
                edge_width=edge_width,
                **kwargs,
            )

            self.add_graphic(lg)

    def __getitem__(self, item) -> ScatterCollectionIndexer:
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


class ScatterStack(ScatterCollection):
    def __init__(
        self,
        data: np.ndarray | List[np.ndarray],
        colors: str | Sequence[str] | np.ndarray | Sequence[np.ndarray] = "w",
        cmap: Sequence[str] | str = None,
        cmap_transform: np.ndarray | List = None,
        name: str = None,
        names: list[str] = None,
        metadata: Any = None,
        metadatas: Sequence[Any] | np.ndarray = None,
        separation: float = 0.0,
        separation_axis: str = "y",
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

        separation: float, default 0.0
            space in between each line graphic in the stack

        separation_axis: str, default "y"
            axis in which the line graphics in the stack should be separated

        kwargs_collection
            kwargs for the collection, passed to GraphicCollection

        """
        super().__init__(
            data=data,
            colors=colors,
            cmap=cmap,
            cmap_transform=cmap_transform,
            name=name,
            names=names,
            metadata=metadata,
            metadatas=metadatas,
            **kwargs,
        )

        self._sepration_axis = separation_axis
        self._separation = separation

        self.separation = separation

    @property
    def separation(self) -> float:
        """distance between each line in the stack, in world space"""
        return self._separation

    @separation.setter
    def separation(self, value: float):
        separation = float(value)

        axis_zero = 0
        for i, line in enumerate(self.graphics):
            if self._sepration_axis == "x":
                line.offset = (axis_zero, *line.offset[1:])

            elif self._sepration_axis == "y":
                line.offset = (line.offset[0], axis_zero, line.offset[2])

            axis_zero = (
                    axis_zero + line.data.value[:, axes[self._sepration_axis]].max() + separation
            )

        self._separation = value
