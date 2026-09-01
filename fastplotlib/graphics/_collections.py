import numpy as np

from .line import LineGraphic
from .scatter import ScatterGraphic
from .image import ImageGraphic
from ._collection_base import GraphicCollection
from .selectors import (
    LinearSelector,
    LinearRegionSelector,
    RectangleSelector,
    PolygonSelector,
)
from ..utils import calculate_figure_shape


class PositionsCollection(GraphicCollection):
    """A collection of positions-based graphics (lines, scatters); adds selectors spanning all graphics."""

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
        them.

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
    offset by its index times the data extent plus the ``separation`` gap, so the graphics are
    evenly spaced and do not overlap. Set ``separation`` or ``separation_axis`` to (re)stack, e.g.
    after changing the data.
    """

    def __init__(
        self,
        data,
        *,
        separation: tuple[float, float, float] = (0.0, 0.0, 0.0),
        separation_axis: str = "y",
        **kwargs,
    ):
        """
        Create a stack of graphics.

        Parameters
        ----------
        data: list of array-like
            one entry per graphic; its length is the number of graphics in the stack

        separation: (float, float, float), default (0.0, 0.0, 0.0)
            (x, y, z) gap between successive graphics, added to the data extent along the
            corresponding stacking axis

        separation_axis: str, default "y"
            axes to stack along, any combination of "x", "y", "z", e.g. "y", "xy", "xyz"

        **kwargs
            passed to the collection, e.g. ``colors``, ``thickness``, ``sizes``
        """
        super().__init__(data, **kwargs)
        self._separation = np.asarray(separation, dtype=float)
        self.separation_axis = separation_axis  # (re)stacks

    @property
    def separation(self) -> np.ndarray:
        """get or set the (x, y, z) gap added to the data extent along the stacking axes"""
        return self._separation

    @separation.setter
    def separation(self, value: tuple[float, float, float]):
        value = np.asarray(value, dtype=float)
        if value.shape != (3,):
            raise ValueError("separation must be an (x, y, z) iterable")
        self._separation = value
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
        # one max over all the data gives the extent to step by along each stacking axis
        extents = np.concatenate(self.data[:, :, axes]).max(axis=0)
        offsets = np.zeros((len(self), 3))
        offsets[:, axes] = np.arange(len(self))[:, np.newaxis] * (extents + self._separation[axes])
        self.offsets[:] = offsets


class LineStack(GraphicStack, LineCollection):
    pass


class ScatterStack(GraphicStack, ScatterCollection):
    pass
