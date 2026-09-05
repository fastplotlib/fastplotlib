import itertools

import cmap as cmap_lib
import numpy as np

from .line import LineGraphic
from .scatter import ScatterGraphic
from .image import ImageGraphic
from ._collection_base import GraphicCollection, cmap_across_graphics
from .selectors import (
    LinearSelector,
    LinearRegionSelector,
    RectangleSelector,
    PolygonSelector,
)
from ..utils import calculate_figure_shape


class PositionsCollection(GraphicCollection):
    """A collection of positions-based graphics (lines, scatters); adds selectors spanning all graphics."""

    def __init__(self, data, *, cmap=None, cmap_transform=None, cmap_range=None, **kwargs):
        super().__init__(data, **kwargs)
        self._set_cmap(cmap, cmap_transform, cmap_range)

    def _set_cmap(self, cmap, cmap_transform=None, cmap_range=None):
        """
        A single cmap (str or ``cmap_lib.Colormap``) gives each graphic a uniform color.
        An iterable of cmaps gives each graphic its own colormap.
        """
        if hasattr(cmap, "__next__"):
            # an iterator (itertools.repeat/cycle, a generator, ...): one cmap per graphic,
            # materialized so re-applying it (e.g. each frame in NDPositions) stays stable
            cmap = list(itertools.islice(cmap, len(self)))
        self._cmap = cmap
        self._cmap_transform = cmap_transform
        self._cmap_range = cmap_range

        if cmap is None:
            if cmap_transform is not None:
                raise ValueError("must pass `cmap` if passing `cmap_transform`")
            return

        single_cmap = isinstance(cmap, (str, cmap_lib.Colormap))
        # a single cmap needs a 1D transform (across graphics), an iterable needs a 2D transform (per-graphic)
        if cmap_transform is not None and single_cmap == (np.ndim(cmap_transform[0]) >= 1):
            raise ValueError(
                "`cmap` and `cmap_transform` must match: a single `cmap` uses a 1D transform, "
                "an iterable of cmaps uses a 2D transform"
            )

        if single_cmap:
            self.colors[:] = cmap_across_graphics(cmap, len(self), cmap_transform)
            return

        transforms = cmap_transform if cmap_transform is not None else itertools.repeat(None)
        ranges = cmap_range if np.ndim(cmap_range) == 2 else itertools.repeat(cmap_range)
        for graphic, one_cmap, transform, rng in zip(self.graphics, cmap, transforms, ranges):
            graphic.cmap = one_cmap
            if transform is not None:
                graphic.cmap_transform = transform
            if rng is not None:
                graphic.cmap_range = rng

    @property
    def cmap(self):
        """get or set the cmap of the graphics in the collection"""
        return self._cmap

    @cmap.setter
    def cmap(self, value):
        self._set_cmap(value, self._cmap_transform, self._cmap_range)

    @property
    def cmap_transform(self):
        """get or set the cmap_transform of the graphics in the collection"""
        return self._cmap_transform

    @cmap_transform.setter
    def cmap_transform(self, value):
        self._set_cmap(self._cmap, value, self._cmap_range)

    @property
    def cmap_range(self):
        """get or set the cmap_range of the graphics in the collection"""
        return self._cmap_range

    @cmap_range.setter
    def cmap_range(self, value):
        self._set_cmap(self._cmap, self._cmap_transform, value)

    def add_linear_selector(
        self, selection: float = None, padding: float = 0.0, axis: str = "x", **kwargs
    ) -> LinearSelector:
        """
        Add a :class:`.LinearSelector`.

        Parameters
        ----------
        selection: float, optional
            initial position of the selector along ``axis``, computed from the data if not given

        padding: float, default 0.0
            extra padding along the orthogonal axis to make the selector easier to grab

        axis: str, default "x"
            axis the selector moves along

        **kwargs
            passed to :class:`.LinearSelector`

        Returns
        -------
        LinearSelector
        """
        bounds_init, limits, size, center = self._get_linear_selector_init_args(axis, padding)

        if selection is None:
            selection = bounds_init[0]

        selector = LinearSelector(
            selection=selection, limits=limits, axis=axis, parent=self, **kwargs
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
        Add a :class:`.LinearRegionSelector`.

        Parameters
        ----------
        selection: (float, float), optional
            initial bounds of the region along ``axis``, computed from the data if not given

        padding: float, default 0.0
            extra padding along the orthogonal axis to make the selector easier to grab

        axis: str, default "x"
            axis the selector spans

        **kwargs
            passed to :class:`.LinearRegionSelector`

        Returns
        -------
        LinearRegionSelector
        """
        bounds_init, limits, size, center = self._get_linear_selector_init_args(axis, padding)

        if selection is None:
            selection = bounds_init

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

        return selector

    def add_rectangle_selector(
        self, selection: tuple[float, float, float, float] = None, **kwargs
    ) -> RectangleSelector:
        """
        Add a :class:`.RectangleSelector`.

        Parameters
        ----------
        selection: (float, float, float, float), optional
            initial (xmin, xmax, ymin, ymax), computed from the data if not given

        **kwargs
            passed to :class:`.RectangleSelector`

        Returns
        -------
        RectangleSelector
        """
        bbox = self.world_object.get_world_bounding_box()

        xdata = np.concatenate(self.data[:, :, 0])
        xmin, xmax = np.nanmin(xdata), np.nanmax(xdata)
        value_25px = (xmax - xmin) / 4

        ymin = np.floor(np.nanmin(np.concatenate(self.data[:, :, 1]))).astype(int)
        ymax = np.ptp(bbox[:, 1])

        if selection is None:
            selection = (xmin, value_25px, ymin, ymax)

        limits = (xmin, xmax, ymin - (ymax * 1.5 - ymax), ymax * 1.5)

        selector = RectangleSelector(
            selection=selection, limits=limits, parent=self, **kwargs
        )
        self._plot_area.add_graphic(selector, center=False)

        return selector

    def add_polygon_selector(
        self, selection: list[tuple[float, float]] = None, **kwargs
    ) -> PolygonSelector:
        """
        Add a :class:`.PolygonSelector`.

        Parameters
        ----------
        selection: list of (float, float), optional
            initial polygon points; if not given, you draw the polygon by clicking

        **kwargs
            passed to :class:`.PolygonSelector`

        Returns
        -------
        PolygonSelector
        """
        bbox = self.world_object.get_world_bounding_box()

        xdata = np.concatenate(self.data[:, :, 0])
        xmin, xmax = np.nanmin(xdata), np.nanmax(xdata)

        ymin = np.floor(np.nanmin(np.concatenate(self.data[:, :, 1]))).astype(int)
        ymax = np.ptp(bbox[:, 1])

        limits = (xmin, xmax, ymin - (ymax * 1.5 - ymax), ymax * 1.5)

        selector = PolygonSelector(selection, limits, parent=self, **kwargs)
        self._plot_area.add_graphic(selector, center=False)

        return selector

    def _get_linear_selector_init_args(self, axis: str, padding: float):
        bbox = self.world_object.get_world_bounding_box()
        axis_index = {"x": 0, "y": 1}[axis]
        orthogonal_index = 1 - axis_index

        data = np.concatenate(self.data[:, :, axis_index])
        vmin, vmax = np.nanmin(data), np.nanmax(data)

        bounds = (vmin, (vmax - vmin) / 4)
        limits = (vmin, vmax)
        # size and center on the orthogonal axis, from the world bounding box
        size = np.ptp(bbox[:, orthogonal_index]) * 1.5
        center = bbox[:, orthogonal_index].mean()

        return bounds, limits, size, center


class LineCollection(PositionsCollection):
    _child_type = LineGraphic


class ScatterCollection(PositionsCollection):
    _child_type = ScatterGraphic


class ImageCollection(GraphicCollection):
    _child_type = ImageGraphic


class ImageGrid(ImageCollection):
    def __init__(
        self,
        data,
        *,
        shape: tuple[int, int] = None,
        separation: tuple[float, float] = (0.0, 0.0),
        offsets: np.ndarray = None,
        **kwargs,
    ):
        """
        Lay out a collection of images in a grid.

        If ``offsets`` is given it is used directly as the per-image position. Otherwise the images
        are placed row-major into a grid of ``shape`` (rows, columns), each cell sized to the
        largest image so the rows and columns line up, with ``separation`` world-space gaps between
        them. By default there is separation space between the images.

        Parameters
        ----------
        data: list of array-like
            one image per grid cell

        shape: (int, int), optional
            grid (n_rows, n_cols); defaults to a roughly square grid that fits all the images

        separation: (float, float), default (0.0, 0.0)
            world-space (row, column) gaps between the images

        offsets: array-like, optional
            explicit (x, y, z) offset per image; when given, ``shape`` and ``separation`` are ignored

        **kwargs
            passed to :class:`.ImageCollection`, e.g. ``cmap``, ``vmin``, ``vmax``
        """
        super().__init__(data, **kwargs)
        n = len(self)

        if offsets is None:
            if shape is None:
                shape = calculate_figure_shape(n)  # roughly square (rows, cols)
            if np.prod(shape) < n:
                raise ValueError(f"grid shape {shape} has fewer cells than the {n} images")

            rows, cols = np.divmod(np.arange(n), shape[1])
            # cell size = the largest image, via the data accessor, so rows and columns line up
            sizes = np.array([image.shape[:2] for image in self.data[:]])  # (rows, cols) per image
            cell_height, cell_width = sizes.max(axis=0)
            row_sep, col_sep = separation

            offsets = np.zeros((n, 3))
            offsets[:, 0] = cols * (cell_width + col_sep)  # x, left to right
            offsets[:, 1] = -rows * (cell_height + row_sep)  # y, top row first

        self.offsets[:] = offsets


class GraphicStack:
    """
    Mixin that stacks a collection's graphics along the axes in ``separation_axis``. Each graphic is
    offset by its index times the data max plus the ``separation`` gap, so the graphics are evenly
    spaced and do not overlap; pass per-graphic ``steps`` to space them individually. Set
    ``separation`` or ``separation_axis`` to (re)stack, e.g. after changing the data.
    """

    def __init__(
        self,
        data,
        *,
        separation: tuple[float, float, float] = (0.0, 0.0, 0.0),
        separation_axis: str = "y",
        steps: np.ndarray = None,
        **kwargs,
    ):
        """
        Create a stack of graphics.

        Parameters
        ----------
        data: list of array-like
            one entry per graphic; its length is the number of graphics in the stack

        separation: (float, float, float), default (0.0, 0.0, 0.0)
            (x, y, z) gap between successive graphics, added to the step along the corresponding
            stacking axis

        separation_axis: str, default "y"
            axes to stack along, any combination of "x", "y", "z", e.g. "y", "xy", "xyz"

        steps: [n_graphics, 3] array-like, optional
            per-graphic step along each (x, y, z) axis, i.e. the max each graphic reaches. When
            ``None`` (default) a single max over all the data sets one uniform step. When given, each
            graphic is offset by the cumulative step of the graphics before it, plus ``separation``.

        **kwargs
            passed to the collection, e.g. ``colors``, ``thickness``, ``sizes``
        """
        super().__init__(data, **kwargs)
        self._separation = np.asarray(separation, dtype=float)
        self._steps = self._check_steps(steps)
        self.separation_axis = separation_axis  # (re)stacks

    def _check_steps(self, steps) -> np.ndarray | None:
        if steps is None:
            return None
        steps = np.asarray(steps, dtype=float)
        if steps.shape != (len(self), 3):
            raise ValueError(
                f"steps must be a [n_graphics, 3] array, got shape {steps.shape} for "
                f"{len(self)} graphics"
            )
        return steps

    @property
    def separation(self) -> np.ndarray:
        """get or set the (x, y, z) gap added to the step along the stacking axes"""
        return self._separation

    @separation.setter
    def separation(self, value: tuple[float, float, float]):
        value = np.asarray(value, dtype=float)
        if value.shape != (3,):
            raise ValueError("separation must be an (x, y, z) iterable")
        self._separation = value
        self._restack()

    @property
    def steps(self) -> np.ndarray | None:
        """get or set the per-graphic (x, y, z) steps used to space the stack, ``None`` to auto-determine"""
        return self._steps

    @steps.setter
    def steps(self, value: np.ndarray | None):
        self._steps = self._check_steps(value)
        self._restack()

    @property
    def separation_axis(self) -> str:
        """get or set the axes to stack along, e.g. "y", "xy", "xyz\""""
        return self._separation_axis

    @separation_axis.setter
    def separation_axis(self, value: str):
        if not set(value).issubset("xyz"):
            raise ValueError(
                f"separation_axis must be a combination of 'x', 'y', 'z', got {value!r}"
            )
        self._separation_axis = value
        self._restack()

    def _restack(self):
        axes = [{"x": 0, "y": 1, "z": 2}[axis] for axis in self._separation_axis]
        offsets = np.zeros((len(self), 3))
        if self._steps is None:
            # one max over all the data gives the step to stack by along each stacking axis
            step = np.concatenate(self.data[:, :, axes]).max(axis=0)
            offsets[:, axes] = np.arange(len(self))[:, np.newaxis] * (step + self._separation[axes])
        else:
            # per-graphic steps: offset each graphic past the previous ones by their cumulative step
            offsets[1:, axes] = np.cumsum(
                self._steps[:-1, axes] + self._separation[axes], axis=0
            )
        self.offsets[:] = offsets


class LineStack(GraphicStack, LineCollection):
    pass


class ScatterStack(GraphicStack, ScatterCollection):
    pass
