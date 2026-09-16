from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

import cmap as cmap_lib
import numpy as np
import pygfx
import pynapple as nap

from ....graphics import ImageGraphic, LineStack, ScatterCollection
from ....utils import ArrayProtocol, subsample_array
from .._async import run_in_thread_pool, run_sync
from .._base import NDSlicer, identity
from .._nd_image import NDImage, NDImageSlicer
from ._nd_positions import NDPositionsSlicer
from ._nd_timeseries import NDTimeseries


def metadata_categories(values: Sequence) -> np.ndarray:
    """
    Unique values of a metadata column, **in order of first appearance** rather than sorted.

    Parameters
    ----------
    values: Sequence
        A column of a pynapple ``metadata`` table.

    Returns
    -------
    np.ndarray
        The unique values, ordered by where they first occur in ``values``.

    """
    values = np.asarray(values)
    categories, first = np.unique(values, return_index=True)

    return categories[np.argsort(first)]


def metadata_codes(values: Sequence) -> tuple[np.ndarray, np.ndarray]:
    """
    Encode a metadata column as integer codes.

    Numeric columns are returned unchanged. Anything else is encoded against
    :func:`metadata_categories`, so the codes follow the order the categories occur in the object.

    Parameters
    ----------
    values: Sequence
        A column of a pynapple ``metadata`` table.

    Returns
    -------
    (np.ndarray, np.ndarray)
        ``(codes, categories)``. ``categories`` is empty for a numeric column.

    """
    values = np.asarray(values)

    if np.issubdtype(values.dtype, np.number):
        return values, np.empty(0)

    categories = metadata_categories(values)
    lookup = {category: code for code, category in enumerate(categories)}

    return np.array([lookup[v] for v in values]), categories


def sort_order(data: Any, column: str) -> np.ndarray:
    """
    Permutation that orders the graphics of a pynapple object by one of its metadata columns.

    Used by the slicers for ``sort_by`` and by ``NDWSubplot.add_pynapple_obj`` to put per-graphic
    colors in the same order, so the two cannot disagree.

    Parameters
    ----------
    data: pynapple.TsGroup | pynapple.TsdFrame | pynapple.IntervalSet
        Any pynapple object carrying metadata.

    column: str
        Name of the metadata column to order by. A categorical column is ordered by its
        :func:`metadata_categories`, i.e. by where each category first occurs.

    Returns
    -------
    np.ndarray
        Indices that order the graphics.

    """
    codes, _ = metadata_codes(data.metadata[column])

    return np.argsort(codes, kind="stable")


def _is_color_column(values: np.ndarray) -> bool:
    """whether every unique value of a metadata column names a color"""
    if np.issubdtype(values.dtype, np.number):
        return False

    try:
        for value in np.unique(values):
            pygfx.Color(value)
    except (ValueError, TypeError):
        return False

    return True


def _color_kwargs(
    values: Sequence, cmap: str | None, vmin: float, vmax: float
) -> dict[str, Any]:
    """map a metadata column onto ``cmap``/``cmap_transform``/``cmap_range``/``colors`` kwargs"""
    values = np.asarray(values)

    if _is_color_column(values):
        # the column already names the colors, no colormap involved
        return {"colors": values}

    codes, categories = metadata_codes(values)

    if categories.size == 0:
        # numeric, mapped linearly onto the colormap between the percentile bounds
        return {
            "cmap": cmap if cmap is not None else "viridis",
            "cmap_transform": codes,
            "cmap_range": (
                float(np.nanpercentile(codes, vmin, method="closest_observation")),
                float(np.nanpercentile(codes, vmax, method="closest_observation")),
            ),
        }

    name = cmap if cmap is not None else "tab10"
    colormap = cmap_lib.Colormap(name)

    if colormap.interpolation == "nearest" and categories.size > colormap.num_colors:
        raise IndexError(
            f"there are {categories.size} categories but the qualitative colormap "
            f"'{colormap.name}' has only {colormap.num_colors} colors, pass a `cmap` with at "
            f"least {categories.size} colors"
        )

    # no `cmap_range`: on a collection a qualitative transform indexes the colors directly, so
    # category k is already color k, and a range raises
    return {"cmap": name, "cmap_transform": codes}


def tsgroup_colors(
    data: nap.TsGroup,
    column: str,
    cmap: str = None,
    vmin: float = 0.0,
    vmax: float = 100.0,
) -> dict[str, Any]:
    """
    Graphic feature kwargs coloring the units of a ``TsGroup`` by one of its metadata columns.

    Parameters
    ----------
    data: pynapple.TsGroup
        The units to color.

    column: str
        Name of the metadata column, ex: ``"cell_type"`` or ``"rate"``.

    cmap: str, optional
        Colormap name. Defaults to ``"tab10"`` for a categorical column and ``"viridis"`` for a
        numeric one.

    vmin, vmax: float, default 0.0 and 100.0
        Percentiles of a numeric column used as the ``cmap_range``. Ignored for a categorical
        column, whose codes index the colormap directly.

    Returns
    -------
    dict[str, Any]
        Kwargs to pass to ``add_pynapple_obj`` or an ``add_nd_*`` method, in the order of the
        object itself. Pass ``color_by`` to ``add_pynapple_obj`` instead to have them ordered to
        match ``sort_by``.

    """
    return _color_kwargs(data.metadata[column], cmap, vmin, vmax)


def tsdframe_colors(
    data: nap.TsdFrame,
    column: str,
    cmap: str = None,
    vmin: float = 0.0,
    vmax: float = 100.0,
) -> dict[str, Any]:
    """
    Graphic feature kwargs coloring the columns of a ``TsdFrame`` by one of its metadata columns.

    Parameters
    ----------
    data: pynapple.TsdFrame
        The columns to color.

    column: str
        Name of the metadata column, ex: ``"region"``.

    cmap: str, optional
        Colormap name. Defaults to ``"tab10"`` for a categorical column and ``"viridis"`` for a
        numeric one.

    vmin, vmax: float, default 0.0 and 100.0
        Percentiles of a numeric column used as the ``cmap_range``.

    Returns
    -------
    dict[str, Any]
        Kwargs to pass to ``add_pynapple_obj`` or an ``add_nd_*`` method.

    """
    return _color_kwargs(data.metadata[column], cmap, vmin, vmax)


def intervalset_colors(
    data: nap.IntervalSet, column: str, cmap: str = None
) -> dict[str, Any]:
    """
    Graphic feature kwargs coloring the rows of an :class:`IntervalSetSlicer` by their category.

    The rows of that slicer are the unique values of ``column``, one per category, so the colors
    identify the categories rather than the individual epochs.

    .. important::
        Only applies to the line and scatter representations. A heatmap, which is the default,
        colors by the coverage value instead.

    Parameters
    ----------
    data: pynapple.IntervalSet
        The epochs whose categories are colored.

    column: str
        Name of the metadata column whose unique values are the rows.

    cmap: str, default ``"tab10"``
        Colormap name.

    Returns
    -------
    dict[str, Any]
        Kwargs to pass to ``add_pynapple_obj`` or an ``add_nd_*`` method.

    """
    categories = metadata_categories(data.metadata[column])

    return _color_kwargs(np.arange(categories.size), cmap, 0.0, 100.0)


def ranges_from_time_support(
    *data: Any, dim: str = "time", step: float = None
) -> dict[str, tuple[float, float, float]]:
    """
    Reference range spanning the overlap of the ``time_support`` of every given object.

    The reference range must be the **intersection** of what each modality covers. Past the end of
    the shortest one the slider keeps moving while that graphic's index is clamped to its last
    sample, so it sits there showing a stale slice that looks like real data.

    Using ``time_support`` rather than ``t[0]`` and ``t[-1]`` also handles a recording with gaps,
    whose support is several intervals that the first and last timestamp would span straight over.

    Parameters
    ----------
    data: pynapple objects
        Any objects carrying a ``time_support``.

    dim: str, default ``"time"``
        Name of the reference dim, i.e. the key of the returned mapping.

    step: float, optional
        Increment used by the step buttons and playback, in seconds. Defaults to the **coarsest**
        median sampling interval among the objects that have timestamps, since stepping finer than
        the slowest modality only re-renders its same sample. Objects without timestamps, ex: a
        ``TsGroup`` or an ``IntervalSet``, do not contribute, and it must be given explicitly if
        none of them do.

    Returns
    -------
    dict[str, tuple[float, float, float]]
        ``{dim: (start, stop, step)}``, ready to pass as the ``ranges`` of an ``NDWidget``.

    """
    # an IntervalSet has no `time_support`, it already is one
    supports = [
        obj if isinstance(obj, nap.IntervalSet) else obj.time_support for obj in data
    ]

    support = supports[0]
    for other in supports[1:]:
        support = support.intersect(other)

    if len(support) == 0:
        raise ValueError(
            "the `time_support` of the given objects do not overlap, so there is no reference "
            "range that covers all of them"
        )

    if step is None:
        intervals = [
            float(np.median(np.diff(obj.t)))
            for obj in data
            if hasattr(obj, "t") and np.size(obj.t) > 1
        ]

        if not intervals:
            raise ValueError(
                "none of the given objects have timestamps to take a sampling interval from, "
                "pass `step` explicitly"
            )

        step = max(intervals)

    return {dim: (float(support.start[0]), float(support.end[-1]), float(step))}


def covered_by(ep: nap.IntervalSet, times: np.ndarray) -> np.ndarray:
    """
    Boolean mask of the timestamps that an epoch of ``ep`` covers.

    Parameters
    ----------
    ep: pynapple.IntervalSet
        The epochs to test against.

    times: np.ndarray
        Timestamps in seconds.

    Returns
    -------
    np.ndarray
        Boolean mask, ``True`` where an epoch covers that timestamp.

    """
    # `IntervalSet.in_interval` would do this, but it takes a `Ts`, and building one on every
    # index change allocates and warns about a zero-duration time_support whenever the window
    # holds a single timestamp. The epochs are sorted and non-overlapping, so the first epoch
    # ending at or after a timestamp is the only one that can contain it. `side="left"` keeps
    # both ends inclusive, which is pynapple's convention.
    index = np.searchsorted(ep.end, times, side="left")

    covered = index < len(ep)
    covered[covered] = times[covered] >= ep.start[index[covered]]

    return covered


class _PynapplePositionsSlicer(NDPositionsSlicer):
    """
    Shared timebase, ``ep`` and ``sort_by`` handling for the pynapple positional slicers.

    Not used directly. The ``p`` slider map always comes from the pynapple object itself, so a
    reference value in seconds is never converted to an index by hand.
    """

    # cap on the number of samples read to estimate the per-graphic y max used for stack spacing
    _max_y_samples = 1_000_000

    #: the representation this slicer's output is normally drawn as, used by
    #: ``NDWSubplot.add_pynapple_obj`` when no ``graphic_type`` is given
    default_graphic_type = LineStack

    #: the ``NDGraphic`` that carries this slicer's mutable properties, assigned at the end of the
    #: module since the graphics are defined after the slicers
    nd_graphic_type: type = None

    def __init__(
        self,
        data: Any,
        dims: Sequence[str],
        display_dims: tuple[str, str, str],
        ep: nap.IntervalSet = None,
        sort_by: str = None,
        **kwargs,
    ):
        # both are read while producing a slice, set them before the base fetches the first one
        self._ep = None
        self._sort_by = None

        super().__init__(data, dims, display_dims, **kwargs)

        self.ep = ep
        self.sort_by = sort_by

    @property
    def time_dim(self) -> str:
        """name of the ``p`` dim, i.e. the time axis"""
        return self.display_dims[1]

    def _time_map(self):
        """reference seconds -> array index along ``p``"""
        return self.data.t.searchsorted

    @property
    def slider_maps(self) -> dict[str, Any]:
        """
        Per-slider-dim mapping from reference-space values to local array indices.

        The map for the ``p`` dim is taken from the pynapple object's own timestamps and cannot be
        given; every other dim behaves as in :class:`NDSlicer`.
        """
        return self._index_mappings

    @slider_maps.setter
    def slider_maps(self, maps: dict[str, Any] | None):
        if maps is not None and self.time_dim in maps:
            raise ValueError(
                f"the map for '{self.time_dim}' comes from the timestamps of the "
                f"{type(self.data).__name__} itself, remove it from `slider_maps`"
            )

        maps = dict(maps) if maps is not None else dict()
        maps[self.time_dim] = self._time_map()

        NDSlicer.slider_maps.fset(self, maps)

    @property
    def ep(self) -> nap.IntervalSet | None:
        """
        Get or set the epochs to restrict to. ``None`` uses every epoch of the object's
        ``time_support``.
        """
        return self._ep

    @ep.setter
    def ep(self, ep: nap.IntervalSet | None):
        if ep is not None and not isinstance(ep, nap.IntervalSet):
            raise TypeError(
                f"`ep` must be a `pynapple.IntervalSet` or `None`, you passed a "
                f"{type(ep).__name__}"
            )

        self._ep = ep

    @property
    def sort_by(self) -> str | None:
        """
        Get or set the name of the metadata column the graphics are ordered by. ``None`` keeps the
        order of the object.
        """
        return self._sort_by

    @sort_by.setter
    def sort_by(self, column: str | None):
        if column is not None:
            if not hasattr(self.data, "metadata_columns"):
                raise TypeError(
                    f"a {type(self.data).__name__} carries no metadata to sort by"
                )

            if column not in self.data.metadata_columns:
                raise KeyError(
                    f"'{column}' is not a metadata column of this "
                    f"{type(self.data).__name__}, available columns are: "
                    f"{list(self.data.metadata_columns)}"
                )

        self._sort_by = column

    def _order(self) -> np.ndarray | None:
        """permutation of the graphics axis for the current ``sort_by``"""
        if self.sort_by is None:
            return None

        return sort_order(self.data, self.sort_by)

    def _outside_ep(self, times: np.ndarray) -> np.ndarray | None:
        """boolean mask of the timestamps that no epoch of ``ep`` covers"""
        if self.ep is None:
            return None

        return ~covered_by(self.ep, times)


class TsdFrameSlicer(_PynapplePositionsSlicer):
    def __init__(
        self,
        data: nap.Tsd | nap.TsdFrame,
        dims: tuple[str, str, str],
        display_dims: tuple[str, str, str],
        ep: nap.IntervalSet = None,
        sort_by: str = None,
        **kwargs,
    ):
        """
        ``NDPositionsSlicer`` subclass for a ``pynapple.Tsd`` or ``pynapple.TsdFrame``.

        Produces ``[n_columns, p, 2]`` slices, where the x coordinate is the object's own
        timestamps and the y coordinate is its values. Only the display window is ever read, so a
        lazily loaded object stays out-of-core. A ``Tsd`` is the single-column case.

        Parameters
        ----------
        data: pynapple.Tsd | pynapple.TsdFrame
            The object to display. Its timestamps are used as the ``p`` slider map.

        dims: tuple[str, str, str]
            Names for the 3 dims. A ``TsdFrame`` has no further dims to name, so these are the same
            3 names as ``display_dims``.

        display_dims: tuple[str, str, str]
            The 3 spatial dims **in display order**: ``(n_graphics, p, <value dim>)``.

        ep: pynapple.IntervalSet, optional
            Restrict to these epochs. Samples that no epoch covers are set to ``NaN``, which
            renders as a break in a line and as nothing in a scatter. A heatmap has no ``NaN``
            handling, so there they are not distinguishable from the colormap minimum.

        sort_by: str, optional
            Name of a metadata column to order the columns by.

        kwargs
            passed to :class:`NDPositionsSlicer`, i.e. ``display_window``,
            ``max_display_datapoints``, ``datapoints_window_func``, ``window_funcs``,
            ``window_order`` and ``spatial_func``.

        See Also
        --------
            NDPositionsSlicer : Base class with full parameter documentation.

        """
        super().__init__(data, dims, display_dims, ep=ep, sort_by=sort_by, **kwargs)

    @property
    def data(self) -> nap.Tsd | nap.TsdFrame:
        """get or set the managed object, the new object is interpreted to have the same dims"""
        return self._data

    @data.setter
    def data(self, data: nap.Tsd | nap.TsdFrame):
        if not isinstance(data, (nap.Tsd, nap.TsdFrame)):
            raise TypeError(
                f"`data` must be a `pynapple.Tsd` or `pynapple.TsdFrame`, you passed a "
                f"{type(data).__name__}"
            )

        self._data = data

    @property
    def n_columns(self) -> int:
        """number of columns, i.e. the number of graphics in the collection"""
        return 1 if self.data.ndim == 1 else self.data.shape[1]

    @property
    def shape(self) -> dict[str, int]:
        """interpreted shape of the data, the number of columns, timestamps, and the value dim"""
        n_graphics, p, d = self.display_dims

        return {n_graphics: self.n_columns, p: self.data.t.size, d: 2}

    @property
    def ndim(self) -> int:
        """number of dims, always 3"""
        return 3

    def _stack(self, times: np.ndarray, values: ArrayProtocol) -> np.ndarray:
        """``[p]`` timestamps and ``[p, n_columns]`` values -> ``[n_columns, p, 2]``"""
        values = np.asarray(values)
        if values.ndim == 1:
            values = values[:, None]

        order = self._order()
        if order is not None:
            values = values[:, order]

        out = np.empty((values.shape[1], times.size, 2), dtype=np.float32)
        out[..., 0] = times
        out[..., 1] = values.T

        return out

    def _read(self, dw_slice: slice) -> np.ndarray:
        times = self.data.t[dw_slice]
        out = self._stack(times, self.data.values[dw_slice])

        outside = self._outside_ep(times)
        if outside is not None:
            out[:, outside, 1] = np.nan

        return self._finalize(out)

    async def get(self, indices: dict[str, Any]) -> dict[str, np.ndarray]:
        """
        Get the data slice to display at the given indices.

        Reads only the display window from the object, stacks its timestamps and values into
        ``[n_columns, p, 2]``, then applies the ``datapoints_window_func`` and ``spatial_func``.

        Parameters
        ----------
        indices: dict[str, Any]
            Reference-space value for the ``p`` dim, ex: ``{"time": 46.397}``.

        Returns
        -------
        dict[str, np.ndarray]
            ``"data"`` holds the data slice, the remaining keys are the windowed graphic features.

        """
        dw_slice = self._get_dw_slice(indices)

        data = await run_in_thread_pool(self._executor, self._read, dw_slice)

        return {"data": data, **self._get_other_features(data, dw_slice)}

    def _strided_read(self) -> np.ndarray:
        # stride along time only so every column survives; `subsample_array` spreads its factor
        # over all dims and stops honoring `max_size` once a dim is given to `ignore_dims`
        n = self.data.t.size
        step = max(1, n // max(1, self._max_y_samples // self.n_columns))

        return self._stack(self.data.t[::step], self.data.values[::step])

    async def _get_raw_data_slice(self, indices: dict[str, Any]) -> np.ndarray:
        # only reached from `NDTimeseries._p_y_max`, which needs the per-graphic y max over the
        # full `p` dim to space a LineStack/ScatterStack. Nothing records that max: NWB carries
        # `conversion`/`offset`/`resolution`, HDF5 has no per-dataset extrema, and an h5py Dataset
        # has no `.max`. So estimate it from a strided read, as vmin/vmax already are.
        return await run_in_thread_pool(self._executor, self._strided_read)


class TsGroupRateSlicer(_PynapplePositionsSlicer):
    def __init__(
        self,
        data: nap.TsGroup,
        dims: tuple[str, str, str],
        display_dims: tuple[str, str, str],
        bin_size: float = 0.01,
        ep: nap.IntervalSet = None,
        sort_by: str = None,
        **kwargs,
    ):
        """
        ``NDPositionsSlicer`` subclass that bins a ``pynapple.TsGroup`` into firing rates.

        Produces ``[n_units, p, 2]`` slices where the y coordinate is the firing rate in Hz, the
        same quantity as ``TsGroup.rate``.

        The bins sit on a grid anchored at the start of the recording, not at the start of the
        display window, so the edges stay put as you scroll rather than sliding with the view.

        Rate rather than raw counts so the values keep their meaning when :attr:`bin_size` changes,
        and because ``max_display_datapoints`` may widen the rendered bins over a large window.
        Once the bins are finer than the interspike interval the values collapse towards ``0`` and
        ``1 / bin_size``, which is the regime for :class:`TsGroupSpikesSlicer` instead.

        Parameters
        ----------
        data: pynapple.TsGroup
            The spike trains to bin.

        dims: tuple[str, str, str]
            Names for the 3 dims, the same 3 names as ``display_dims``.

        display_dims: tuple[str, str, str]
            The 3 spatial dims **in display order**: ``(n_graphics, p, <value dim>)``.

        bin_size: float, default 0.01
            Size of the bins the spikes are counted in, in seconds. Also settable afterwards as
            :attr:`bin_size`. Over a window holding more than ``max_display_datapoints`` bins the
            rendered bins are widened to a whole multiple of it, see :meth:`effective_bin_size`.

        ep: pynapple.IntervalSet, optional
            Restrict to these epochs. Spikes outside them are not counted, so a bin that no epoch
            covers is genuinely ``0`` Hz.

        sort_by: str, optional
            Name of a metadata column to order the units by.

        kwargs
            passed to :class:`NDPositionsSlicer`.

        Notes
        -----
        The datapoints are synthesized rather than read from the object, so there is no full ``p``
        dim to index into and per-datapoint windowed graphic features do not apply.

        See Also
        --------
            TsGroupSpikesSlicer : Individual spikes rather than binned rates.

        """
        self._bin_size = None

        super().__init__(data, dims, display_dims, ep=ep, sort_by=sort_by, **kwargs)

        self.bin_size = bin_size

    # a rate raster is a heatmap, one row per unit, color from the rate
    default_graphic_type = ImageGraphic

    @property
    def data(self) -> nap.TsGroup:
        """get or set the managed object, the new object is interpreted to have the same dims"""
        return self._data

    @data.setter
    def data(self, data: nap.TsGroup):
        if not isinstance(data, nap.TsGroup):
            raise TypeError(
                f"`data` must be a `pynapple.TsGroup`, you passed a {type(data).__name__}"
            )

        self._data = data

    def _time_map(self):
        # the bins are synthesized from the display window, so there is no array to index into and
        # reference seconds are used directly
        return identity

    @property
    def bin_size(self) -> float:
        """
        Get or set the bin size the spikes are counted in, in seconds. Setting it re-renders the
        current data slice.
        """
        return self._bin_size

    @bin_size.setter
    def bin_size(self, bin_size: float):
        bin_size = float(bin_size)

        if bin_size <= 0:
            raise ValueError(
                f"`bin_size` must be > 0, a rate over zero duration is undefined, you passed: "
                f"{bin_size}"
            )

        self._bin_size = bin_size

    def effective_bin_size(self, span: float) -> float:
        """
        The bin size actually rendered over a window of ``span`` seconds.

        Equal to :attr:`bin_size` unless the window holds more bins than
        ``max_display_datapoints``, in which case they are widened to a whole multiple of it. They
        are never decimated: dropping every n-th bin would drop the spikes counted in it, and the
        raster would under-report the firing rate without saying so.

        Parameters
        ----------
        span: float
            Width of the window in seconds.

        Returns
        -------
        float
            Bin size in seconds, always a whole multiple of :attr:`bin_size`.

        """
        if self.max_display_datapoints is None:
            return self.bin_size

        n_bins = int(np.ceil(span / self.bin_size))
        widen = max(1, int(np.ceil(n_bins / self.max_display_datapoints)))

        return self.bin_size * widen

    @property
    def n_bins(self) -> int:
        """number of bins rendered per unit at the current display window, i.e. the ``p`` dim"""
        if self.display_window is None:
            span = float(self.data.time_support.tot_length())
        else:
            span = float(self.display_window)

        return max(1, int(np.ceil(span / self.effective_bin_size(span))))

    @property
    def shape(self) -> dict[str, int]:
        """interpreted shape of the data, the number of units, bins, and the value dim"""
        n_graphics, p, d = self.display_dims

        return {n_graphics: len(self.data), p: self.n_bins, d: 2}

    @property
    def ndim(self) -> int:
        """number of dims, always 3"""
        return 3

    def _window(self, indices: dict[str, Any]) -> tuple[float, float]:
        """the display window in seconds"""
        if self.display_window is None:
            support = self.data.time_support
            return float(support.start[0]), float(support.end[-1])

        half_window = self.display_window / 2
        centre = indices[self.time_dim]

        return centre - half_window, centre + half_window

    def _rates(self, start: float, stop: float, bin_size: float) -> np.ndarray:
        # snap to a grid anchored at the start of the recording, otherwise `count` anchors the
        # bins to the window and every edge slides as the window scrolls
        anchor = float(self.data.time_support.start[0])
        start = anchor + np.floor((start - anchor) / bin_size) * bin_size
        stop = anchor + np.ceil((stop - anchor) / bin_size) * bin_size

        window = nap.IntervalSet(start, stop)

        # restrict first so only the spikes of the selected epochs are counted, then bin over the
        # whole window so the grid stays uniform and a heatmap is not interpolated across gaps
        spikes = self.data
        if self.ep is not None:
            spikes = spikes.restrict(window.intersect(self.ep))

        counts = spikes.count(bin_size, ep=window)

        # [n_units, n_bins] in Hz, the same quantity as TsGroup.rate
        rates = np.asarray(counts.values, dtype=np.float32).T / bin_size

        order = self._order()
        if order is not None:
            rates = rates[order]

        out = np.empty((*rates.shape, 2), dtype=np.float32)
        out[..., 0] = counts.t
        out[..., 1] = rates

        return out

    def _bin(self, indices: dict[str, Any]) -> np.ndarray:
        start, stop = self._window(indices)

        if stop <= start:
            # a rate over zero duration is undefined, the NDGraphic hides itself on an empty slice
            return np.empty((len(self.data), 0, 2), dtype=np.float32)

        return self._finalize(
            self._rates(start, stop, self.effective_bin_size(stop - start))
        )

    async def get(self, indices: dict[str, Any]) -> dict[str, np.ndarray]:
        """
        Get the data slice to display at the given indices.

        Bins the spikes of the display window into ``max_display_datapoints`` bins and returns
        their firing rates in Hz.

        Parameters
        ----------
        indices: dict[str, Any]
            Reference-space value for the ``p`` dim, ex: ``{"time": 46.397}``.

        Returns
        -------
        dict[str, np.ndarray]
            ``"data"`` holds the data slice.

        """
        return {"data": await run_in_thread_pool(self._executor, self._bin, indices)}

    def _support_rates(self) -> np.ndarray:
        # for LineStack/ScatterStack spacing only. Binning the whole recording at `bin_size` can
        # produce far more values than the recording has spikes, so the bins are widened until the
        # total fits the sample budget. Wider bins under-estimate the peak rate, so the spacing is
        # an estimate; set `steps` on the graphic directly if it matters.
        support = self.data.time_support
        start, stop = float(support.start[0]), float(support.end[-1])

        budget = max(1, self._max_y_samples // max(1, len(self.data)))
        widen = max(1, int(np.ceil((stop - start) / self.bin_size / budget)))

        return self._rates(start, stop, self.bin_size * widen)

    async def _get_raw_data_slice(self, indices: dict[str, Any]) -> np.ndarray:
        return await run_in_thread_pool(self._executor, self._support_rates)


class TsGroupSpikesSlicer(_PynapplePositionsSlicer):
    def __init__(
        self,
        data: nap.TsGroup,
        dims: tuple[str, str, str],
        display_dims: tuple[str, str, str],
        y: str = None,
        ep: nap.IntervalSet = None,
        sort_by: str = None,
        max_display_datapoints: int | None = 1_000_000,
        **kwargs,
    ):
        """
        ``NDPositionsSlicer`` subclass that renders the individual spikes of a ``pynapple.TsGroup``.

        Produces ``[1, n_spikes, 2]`` slices, one graphic holding every spike of the display
        window, where x is the spike time and y is the row the spike is drawn on. Usually rendered
        as a ``ScatterCollection``.

        Unlike :class:`TsGroupRateSlicer` the datapoints are real, so the display window indexes a
        sorted list of spike times and ``max_display_datapoints`` decimates it. Decimating spikes
        drops them, so the default cap is raised to 1e6 and the cost is bounded by
        ``display_window`` instead.

        Parameters
        ----------
        data: pynapple.TsGroup
            The spike trains to display.

        dims: tuple[str, str, str]
            Names for the 3 dims, the same 3 names as ``display_dims``.

        display_dims: tuple[str, str, str]
            The 3 spatial dims **in display order**: ``(n_graphics, p, <value dim>)``. The first is
            of size 1, since every spike is held by a single graphic.

        y: str, optional
            Name of a metadata column giving the row each unit is drawn on, ex: the depth of the
            unit on the probe. A categorical column is encoded as integer codes. ``None`` uses the
            unit key. Mutually exclusive with ``sort_by``.

        ep: pynapple.IntervalSet, optional
            Restrict to these epochs. Spikes that no epoch covers are dropped from the slice.

        sort_by: str, optional
            Name of a metadata column to order the units by. The row of each unit is then its rank
            in that order. Mutually exclusive with ``y``.

        max_display_datapoints: int | None, default 1e6
            Maximum number of spikes rendered. ``None`` renders every spike in the window.

        kwargs
            passed to :class:`NDPositionsSlicer`.

        See Also
        --------
            TsGroupRateSlicer : Binned firing rates rather than individual spikes.

        """
        if y is not None and sort_by is not None:
            raise ValueError(
                "`y` and `sort_by` both set the row of each unit, pass only one of them"
            )

        self._y = y
        self._tsd = None

        super().__init__(
            data,
            dims,
            display_dims,
            ep=ep,
            sort_by=sort_by,
            max_display_datapoints=max_display_datapoints,
            **kwargs,
        )

    # every spike is a point, drawn by the one graphic that holds them all
    default_graphic_type = ScatterCollection

    @property
    def data(self) -> nap.TsGroup:
        """get or set the managed object, the new object is interpreted to have the same dims"""
        return self._data

    @data.setter
    def data(self, data: nap.TsGroup):
        if not isinstance(data, nap.TsGroup):
            raise TypeError(
                f"`data` must be a `pynapple.TsGroup`, you passed a {type(data).__name__}"
            )

        self._data = data
        self._tsd = None

    @property
    def y(self) -> str | None:
        """
        Get or set the name of the metadata column giving the row each unit is drawn on, ``None``
        uses the unit key.
        """
        return self._y

    @y.setter
    def y(self, column: str | None):
        if column is not None and column not in self.data.metadata_columns:
            raise KeyError(
                f"'{column}' is not a metadata column of this TsGroup, available columns are: "
                f"{list(self.data.metadata_columns)}"
            )

        self._y = column
        self._tsd = None

    @_PynapplePositionsSlicer.sort_by.setter
    def sort_by(self, column: str | None):
        _PynapplePositionsSlicer.sort_by.fset(self, column)
        self._tsd = None

    def _rows(self) -> list | None:
        """the row each unit is drawn on, ``None`` uses the unit key"""
        if self.sort_by is not None:
            # the row of a unit is its rank in the sorted order
            return np.argsort(self._order(), kind="stable").tolist()

        if self.y is not None:
            codes, _ = metadata_codes(self.data.metadata[self.y])
            return codes.tolist()

        return None

    @property
    def tsd(self) -> nap.Tsd:
        """every spike of the group flattened into one ``Tsd``, x is the time and y is the row"""
        if self._tsd is None:
            rows = self._rows()
            self._tsd = self.data.to_tsd() if rows is None else self.data.to_tsd(rows)

        return self._tsd

    def _time_map(self):
        return self._searchsorted_spikes

    def _searchsorted_spikes(self, value: Any) -> int:
        return self.tsd.t.searchsorted(value)

    @property
    def shape(self) -> dict[str, int]:
        """interpreted shape of the data, always 1 graphic, the number of spikes, and the value dim"""
        n_graphics, p, d = self.display_dims

        return {n_graphics: 1, p: self.tsd.t.size, d: 2}

    @property
    def ndim(self) -> int:
        """number of dims, always 3"""
        return 3

    def _stack(self, times: np.ndarray, rows: np.ndarray) -> np.ndarray:
        out = np.empty((1, times.size, 2), dtype=np.float32)
        out[0, :, 0] = times
        out[0, :, 1] = rows

        return out

    def _read(self, dw_slice: slice) -> np.ndarray:
        times = self.tsd.t[dw_slice]
        rows = self.tsd.values[dw_slice]

        outside = self._outside_ep(times)
        if outside is not None:
            # spikes are events with no connectivity, so an excluded one is simply dropped
            times, rows = times[~outside], rows[~outside]

        return self._finalize(self._stack(times, rows))

    async def get(self, indices: dict[str, Any]) -> dict[str, np.ndarray]:
        """
        Get the data slice to display at the given indices.

        Returns every spike of the display window as ``[1, n_spikes, 2]``.

        Parameters
        ----------
        indices: dict[str, Any]
            Reference-space value for the ``p`` dim, ex: ``{"time": 46.397}``.

        Returns
        -------
        dict[str, np.ndarray]
            ``"data"`` holds the data slice, the remaining keys are the windowed graphic features.

        """
        dw_slice = self._get_dw_slice(indices)

        data = await run_in_thread_pool(self._executor, self._read, dw_slice)

        return {"data": data, **self._get_other_features(data, dw_slice)}

    async def _get_raw_data_slice(self, indices: dict[str, Any]) -> np.ndarray:
        return self._stack(self.tsd.t, self.tsd.values)


class IntervalSetSlicer(_PynapplePositionsSlicer):
    def __init__(
        self,
        data: nap.IntervalSet,
        dims: tuple[str, str, str],
        display_dims: tuple[str, str, str],
        column: str = None,
        ep: nap.IntervalSet = None,
        **kwargs,
    ):
        """
        ``NDPositionsSlicer`` subclass that rasterizes a ``pynapple.IntervalSet`` into an ethogram.

        Produces ``[n_categories, p, 2]`` slices where each row is one unique value of ``column``
        and the y coordinate is the **fraction of that bin covered** by the epochs of that row, in
        ``[0, 1]``. Usually rendered as an ``ImageGraphic``.

        Coverage rather than sampling the epoch state at each bin centre: an ``IntervalSet`` has no
        timestamps, so the bins are synthesized from the display window, and point sampling drops
        every epoch shorter than the bin spacing without any warning. Coverage keeps them — a brief
        epoch reads as a faint column that goes solid as you zoom in, rather than blinking in and
        out — and stays in ``[0, 1]`` at every zoom, so the colormap does not shift under it.

        Parameters
        ----------
        data: pynapple.IntervalSet
            The epochs to rasterize.

        dims: tuple[str, str, str]
            Names for the 3 dims, the same 3 names as ``display_dims``.

        display_dims: tuple[str, str, str]
            The 3 spatial dims **in display order**: ``(n_graphics, p, <value dim>)``.

        column: str, optional
            Name of the metadata column whose unique values become the rows, ex: ``"tags"`` for a
            behavioural state. ``None`` puts every epoch on one row.

        ep: pynapple.IntervalSet, optional
            Restrict to these epochs. Coverage is computed against the intersection, so a bin that
            they do not cover is genuinely ``0``.

        kwargs
            passed to :class:`NDPositionsSlicer`.

        Notes
        -----
        Building contiguous bins makes pynapple warn ``Some starts and ends are equal. Removing 1
        microsecond!`` and biases each bin by 1 µs.

        The datapoints are synthesized rather than read from the object, so there is no full ``p``
        dim to index into and per-datapoint windowed graphic features do not apply.

        """
        self._column = None

        super().__init__(data, dims, display_dims, ep=ep, **kwargs)

        self.column = column

    # an ethogram is a heatmap, one row per category, color from the coverage
    default_graphic_type = ImageGraphic

    @property
    def data(self) -> nap.IntervalSet:
        """get or set the managed object, the new object is interpreted to have the same dims"""
        return self._data

    @data.setter
    def data(self, data: nap.IntervalSet):
        if not isinstance(data, nap.IntervalSet):
            raise TypeError(
                f"`data` must be a `pynapple.IntervalSet`, you passed a {type(data).__name__}"
            )

        self._data = data

    def _time_map(self):
        # the bins are synthesized from the display window, so there is no array to index into and
        # reference seconds are used directly
        return identity

    @property
    def column(self) -> str | None:
        """
        Get or set the name of the metadata column whose unique values become the rows, ``None``
        puts every epoch on one row.
        """
        return self._column

    @column.setter
    def column(self, column: str | None):
        if column is not None and column not in self.data.metadata_columns:
            raise KeyError(
                f"'{column}' is not a metadata column of this IntervalSet, available columns "
                f"are: {list(self.data.metadata_columns)}"
            )

        self._column = column

    @_PynapplePositionsSlicer.sort_by.setter
    def sort_by(self, column: str | None):
        if column is not None:
            raise NotImplementedError(
                "the rows are the categories of `column`, not individual epochs, so there is "
                "nothing to sort; set `column` instead"
            )

        _PynapplePositionsSlicer.sort_by.fset(self, None)

    @property
    def categories(self) -> np.ndarray:
        """the value of ``column`` that each row represents, in order of first appearance"""
        if self.column is None:
            return np.zeros(1)

        return metadata_categories(self.data.metadata[self.column])

    @property
    def n_bins(self) -> int:
        """number of bins rendered per row, i.e. the ``p`` dim"""
        return self.max_display_datapoints or 1_000

    @property
    def shape(self) -> dict[str, int]:
        """interpreted shape of the data, the number of rows, bins, and the value dim"""
        n_graphics, p, d = self.display_dims

        return {n_graphics: self.categories.size, p: self.n_bins, d: 2}

    @property
    def ndim(self) -> int:
        """number of dims, always 3"""
        return 3

    def _window(self, indices: dict[str, Any]) -> tuple[float, float]:
        """the display window in seconds"""
        if self.display_window is None:
            return float(self.data.start[0]), float(self.data.end[-1])

        half_window = self.display_window / 2
        centre = indices[self.time_dim]

        return centre - half_window, centre + half_window

    def _epochs_per_row(self) -> list[nap.IntervalSet]:
        if self.column is None:
            return [self.data]

        values = np.asarray(self.data.metadata[self.column])

        return [self.data[values == category] for category in self.categories]

    @staticmethod
    def _bin_coverage(
        bins: nap.IntervalSet, epochs: nap.IntervalSet, edges: np.ndarray
    ) -> np.ndarray:
        """fraction of each bin that ``epochs`` covers"""
        covered_time = np.zeros(edges.size - 1)

        if len(epochs) > 0:
            # intersect clips the epochs at every bin boundary, so each returned piece starts
            # inside exactly one bin and searchsorted identifies which
            covered = bins.intersect(epochs)

            if len(covered) > 0:
                index = np.searchsorted(edges, covered.start, side="right") - 1
                np.add.at(
                    covered_time,
                    np.clip(index, 0, covered_time.size - 1),
                    covered.end - covered.start,
                )

        return covered_time / np.diff(edges)

    def _rasterize(self, indices: dict[str, Any]) -> np.ndarray:
        start, stop = self._window(indices)

        rows = self._epochs_per_row()

        if stop <= start:
            # the NDGraphic hides itself on an empty slice
            return np.empty((len(rows), 0, 2), dtype=np.float32)

        edges = np.linspace(start, stop, self.n_bins + 1)
        bins = nap.IntervalSet(edges[:-1], edges[1:])

        out = np.empty((len(rows), self.n_bins, 2), dtype=np.float32)
        out[..., 0] = (edges[:-1] + edges[1:]) / 2

        for i, epochs in enumerate(rows):
            if self.ep is not None:
                epochs = epochs.intersect(self.ep)

            out[i, :, 1] = self._bin_coverage(bins, epochs, edges)

        return self._finalize(out)

    async def get(self, indices: dict[str, Any]) -> dict[str, np.ndarray]:
        """
        Get the data slice to display at the given indices.

        Rasterizes the epochs of the display window into ``max_display_datapoints`` bins per row
        and returns the fraction of each bin they cover.

        Parameters
        ----------
        indices: dict[str, Any]
            Reference-space value for the ``p`` dim, ex: ``{"time": 46.397}``.

        Returns
        -------
        dict[str, np.ndarray]
            ``"data"`` holds the data slice.

        """
        return {
            "data": await run_in_thread_pool(self._executor, self._rasterize, indices)
        }

    async def _get_raw_data_slice(self, indices: dict[str, Any]) -> np.ndarray:
        # coverage is always within [0, 1], so a stack needs no estimate of the y max
        return np.ones((self.categories.size, 1, 2), dtype=np.float32)


class NDPynappleTimeseries(NDTimeseries):
    """
    ``NDTimeseries`` subclass for the pynapple slicers, adding :attr:`ep` and :attr:`sort_by`.

    Both alias the slicer and re-render, the same way ``display_window`` does. The graphic is
    hidden whenever the display window contains no data, rather than being left showing a stale
    slice.
    """

    # per-graphic color features in the order of the object. Kept unsorted so they can be
    # re-permuted whenever ``sort_by`` changes, otherwise the rows move and the colors stay put
    # and stop identifying the graphic.
    _unsorted_colors: dict[str, Any] = None

    _color_by: str | None = None
    _color_cmap: str | None = None

    # features whose values are per-graphic and therefore follow the sort order
    _ordered_features = ("colors", "cmap_transform")

    # `cmap` has to be set before `cmap_transform`, which raises without one
    _apply_order = ("cmap", "cmap_range", "colors", "cmap_transform")

    def _set_unsorted_colors(self, features: dict[str, Any]):
        """store the color features in the object's order and apply them in the rendered order"""
        self._unsorted_colors = dict(features)
        self._apply_colors()

    def _apply_colors(self):
        """re-apply the stored color features, permuted to the current sort order"""
        if not self._unsorted_colors:
            return

        order = self.slicer._order()

        for name in self._apply_order:
            if name not in self._unsorted_colors:
                continue

            value = self._unsorted_colors[name]
            if order is not None and name in self._ordered_features:
                value = np.asarray(value)[order]

            self._set_feature(name, value)

    @property
    def ep(self) -> nap.IntervalSet | None:
        """
        Get or set the epochs to restrict to, ``None`` uses every epoch of the object's
        ``time_support``. Setting it re-renders the current data slice.
        """
        return self.slicer.ep

    @ep.setter
    def ep(self, ep: nap.IntervalSet | None):
        self.slicer.ep = ep
        # force a render
        run_sync(self._set_indices_())

    @property
    def color_by(self) -> str | None:
        """
        Get or set the name of the metadata column the graphics are colored by, ``None`` stops
        deriving them and leaves the current colors in place.

        A numeric column is mapped onto :attr:`color_cmap` between its percentile bounds, a
        categorical one onto a qualitative colormap so that category *k* is always color *k*, and a
        column that already names colors is used as-is. The colors stay in step with
        :attr:`sort_by`.
        """
        return self._color_by

    @color_by.setter
    def color_by(self, column: str | None):
        self._color_by = column
        self._refresh_colors()

    @property
    def color_cmap(self) -> str | None:
        """
        Get or set the colormap used by :attr:`color_by`. ``None`` uses ``"tab10"`` for a
        categorical column and ``"viridis"`` for a numeric one.
        """
        return self._color_cmap

    @color_cmap.setter
    def color_cmap(self, cmap: str | None):
        self._color_cmap = cmap
        self._refresh_colors()

    def _refresh_colors(self):
        """re-derive the color features from the metadata and apply them in the rendered order"""
        if self._color_by is None:
            self._unsorted_colors = None
            return

        _, colors_helper = dispatch(self.slicer.data)

        self._set_unsorted_colors(
            colors_helper(self.slicer.data, self._color_by, cmap=self._color_cmap)
        )

    @property
    def sort_by(self) -> str | None:
        """
        Get or set the name of the metadata column the graphics are ordered by, ``None`` keeps the
        order of the object. Setting it re-renders the current data slice.
        """
        return self.slicer.sort_by

    @sort_by.setter
    def sort_by(self, column: str | None):
        self.slicer.sort_by = column
        # the rows have moved, so the per-graphic colors have to move with them
        self._apply_colors()
        # force a render
        run_sync(self._set_indices_())

    def _fit_y(self):
        """
        Frame the current slice vertically and put the x-range back.

        Used when a property changes what the y values *mean*, ex: rows from a different metadata
        column, so the range the camera was framing no longer refers to anything.
        """
        subplot = self._nd_subplot.subplot

        x_range = subplot.x_range
        subplot.auto_scale(maintain_aspect=False)
        subplot.x_range = x_range

    def _update_graphic(self, new_features: dict[str, Any], indices: dict[str, Any]):
        if new_features["data"].shape[1] == 0:
            # the window covers no data, ex: it falls entirely outside `ep`. `_update_view` reads
            # the first and last datapoint, so there is nothing to update to.
            self.graphic.visible = False
            return

        self.graphic.visible = True
        super()._update_graphic(new_features, indices)


class NDPynappleRate(NDPynappleTimeseries):
    """``NDPynappleTimeseries`` for a :class:`TsGroupRateSlicer`, adding :attr:`bin_size`."""

    @property
    def bin_size(self) -> float:
        """
        Get or set the bin size the spikes are counted in, in seconds. Setting it re-renders the
        current data slice.
        """
        return self.slicer.bin_size

    @bin_size.setter
    def bin_size(self, bin_size: float):
        self.slicer.bin_size = bin_size
        # force a render
        run_sync(self._set_indices_())


class NDPynappleSpikes(NDPynappleTimeseries):
    """``NDPynappleTimeseries`` for a :class:`TsGroupSpikesSlicer`, adding :attr:`y`."""

    @property
    def y(self) -> str | None:
        """
        Get or set the name of the metadata column giving the row each unit is drawn on, ``None``
        uses the unit key. Setting it re-renders the current data slice.
        """
        return self.slicer.y

    @y.setter
    def y(self, column: str | None):
        self.slicer.y = column
        # there are still as many spikes, but every one is on a different row, and the old y-range
        # was framing the values of the previous column
        run_sync(self._set_indices_())
        self._fit_y()


class NDPynappleEthogram(NDPynappleTimeseries):
    """``NDPynappleTimeseries`` for an :class:`IntervalSetSlicer`, adding :attr:`column`."""

    @property
    def column(self) -> str | None:
        """
        Get or set the name of the metadata column whose unique values are the rows, ``None`` puts
        every epoch on one row. Setting it rebuilds the graphic, since the number of rows changes.
        """
        return self.slicer.column

    @column.setter
    def column(self, column: str | None):
        self.slicer.column = column

        # a different column means a different number of rows, so the buffers are the wrong shape
        if self.graphic is not None:
            self._nd_subplot.subplot.delete_graphic(self.graphic)
            self._graphic = None

        run_sync(self._create_graphic())
        # the colors are per-row, so they have to be derived again for the new rows
        self._refresh_colors()
        run_sync(self._set_indices_())
        # the old y-range was framing a different number of rows
        self._fit_y()


class TsdTensorSlicer(NDImageSlicer):
    def __init__(
        self,
        data: nap.TsdTensor,
        dims: Sequence[str],
        display_dims: tuple[str, str] | tuple[str, str, str],
        ep: nap.IntervalSet = None,
        **kwargs,
    ):
        """
        ``NDImageSlicer`` subclass for a ``pynapple.TsdTensor``, ex: an imaging movie.

        Axis 0 of a ``TsdTensor`` is always time, so ``dims[0]`` is the time dim and its slider map
        is taken from the object's own timestamps.

        Parameters
        ----------
        data: pynapple.TsdTensor
            The frames to display.

        dims: Sequence[str]
            Name for every dim of ``data``, in order. ``dims[0]`` names the time axis.

        display_dims: tuple[str, str] | tuple[str, str, str]
            The 2 or 3 spatial dims **in display order**, see :class:`NDImageSlicer`.

        ep: pynapple.IntervalSet, optional
            Restrict to these epochs. A frame is a single point in time rather than a window, so
            :class:`NDPynappleImage` hides the graphic while the current index falls outside them
            rather than leaving a stale frame on screen.

        kwargs
            passed to :class:`NDImageSlicer`.

        See Also
        --------
            NDImageSlicer : Base class with full parameter documentation.

        """
        self._ep = None

        super().__init__(data, dims, display_dims, **kwargs)

        self.ep = ep

    #: the ``NDGraphic`` that carries this slicer's mutable properties, assigned at the end of the
    #: module since the graphics are defined after the slicers
    nd_graphic_type: type = None

    @property
    def data(self) -> nap.TsdTensor:
        """get or set the managed object, the new object is interpreted to have the same dims"""
        return self._data

    @data.setter
    def data(self, data: nap.TsdTensor):
        if not isinstance(data, nap.TsdTensor):
            raise TypeError(
                f"`data` must be a `pynapple.TsdTensor`, you passed a {type(data).__name__}"
            )

        self._data = data
        self._recompute_histogram()

    @property
    def time_dim(self) -> str:
        """name of the time dim, always axis 0 of a ``TsdTensor``"""
        return self.dims[0]

    @property
    def slider_maps(self) -> dict[str, Any]:
        """
        Per-slider-dim mapping from reference-space values to local array indices.

        The map for the time dim is taken from the object's own timestamps and cannot be given;
        every other dim behaves as in :class:`NDSlicer`, so a ``[time, z, m, n]`` tensor can still
        map its ``z`` dim.
        """
        return self._index_mappings

    @slider_maps.setter
    def slider_maps(self, maps: dict[str, Any] | None):
        if maps is not None and self.time_dim in maps:
            raise ValueError(
                f"the map for '{self.time_dim}' comes from the timestamps of the TsdTensor "
                f"itself, remove it from `slider_maps`"
            )

        maps = dict(maps) if maps is not None else dict()
        maps[self.time_dim] = self.data.t.searchsorted

        NDSlicer.slider_maps.fset(self, maps)

    @property
    def ep(self) -> nap.IntervalSet | None:
        """
        Get or set the epochs to restrict to. ``None`` uses every epoch of the object's
        ``time_support``.
        """
        return self._ep

    @ep.setter
    def ep(self, ep: nap.IntervalSet | None):
        if ep is not None and not isinstance(ep, nap.IntervalSet):
            raise TypeError(
                f"`ep` must be a `pynapple.IntervalSet` or `None`, you passed a "
                f"{type(ep).__name__}"
            )

        self._ep = ep

    def in_ep(self, indices: dict[str, Any]) -> bool:
        """whether the given reference index falls inside :attr:`ep`"""
        if self.ep is None:
            return True

        return bool(covered_by(self.ep, np.atleast_1d(indices[self.time_dim]))[0])

    def _recompute_histogram(self):
        # `np.isnan(tsdtensor) | np.isinf(tsdtensor)` returns NotImplemented from pynapple's
        # __array_ufunc__, so the base implementation raises on a TsdTensor. Reduce over the plain
        # values instead, which also keeps a lazily loaded object lazy.
        if not self._compute_histogram or self.data is None:
            self._histogram = None
            return

        if self.spatial_func is not None:
            # a spatial func often needs the full spatial resolution, see NDImageSlicer
            ignore_dims = [self.dims.index(dim) for dim in self.display_dims]
        else:
            ignore_dims = None

        sub = np.asarray(subsample_array(self.data.values, ignore_dims=ignore_dims))

        self._histogram = np.histogram(sub[np.isfinite(sub)], bins=100)


class NDPynappleImage(NDImage):
    """
    ``NDImage`` subclass for :class:`TsdTensorSlicer`, adding :attr:`ep`.

    A frame is a single point in time rather than a window, so the graphic is hidden while the
    current index falls outside the epochs rather than being left showing a stale frame.
    """

    def __init__(
        self,
        *args,
        slicer_type: type[TsdTensorSlicer] = TsdTensorSlicer,
        ep: nap.IntervalSet = None,
        **kwargs,
    ):
        # `in_ep` is only defined by TsdTensorSlicer, so it is the only sensible default here
        super().__init__(*args, slicer_type=slicer_type, **kwargs)

        if ep is not None:
            # NDImage constructs the slicer itself with a fixed set of kwargs, so there is no
            # route for `ep` other than setting it once the slicer exists
            self.ep = ep

    @property
    def ep(self) -> nap.IntervalSet | None:
        """
        Get or set the epochs to restrict to, ``None`` uses every epoch of the object's
        ``time_support``. Setting it re-renders the current frame.
        """
        return self.slicer.ep

    @ep.setter
    def ep(self, ep: nap.IntervalSet | None):
        self.slicer.ep = ep
        # force a render
        run_sync(self._set_indices_())

    async def _set_indices_(self, indices: dict[str, Any] = None):
        if self.graphic is None:
            return

        if indices is None:
            indices = self.indices

        self.graphic.visible = self.slicer.in_ep(indices)

        if not self.graphic.visible:
            # no frame exists at this time, do not read one
            self._last_indices = indices
            return

        await super()._set_indices_(indices)


# the NDGraphic each slicer pairs with, so that the slicer-specific mutable properties live on a
# class that actually has them. Assigned here rather than in the class bodies because the graphics
# are defined after the slicers they take as a default, and a subclass inherits the pairing.
TsdFrameSlicer.nd_graphic_type = NDPynappleTimeseries
TsGroupRateSlicer.nd_graphic_type = NDPynappleRate
TsGroupSpikesSlicer.nd_graphic_type = NDPynappleSpikes
IntervalSetSlicer.nd_graphic_type = NDPynappleEthogram
TsdTensorSlicer.nd_graphic_type = NDPynappleImage


# the slicer and color helper each pynapple type gets by default. The types are mutually exclusive
# siblings, none is a subclass of another, so an exact lookup is unambiguous. A `TsGroup` defaults
# to rates; pass ``slicer=PynappleSlicer.TsGroupSpikes`` for the individual spikes instead.
_DISPATCH: dict[type, tuple[type, Callable | None]] = {
    nap.Tsd: (TsdFrameSlicer, tsdframe_colors),
    nap.TsdFrame: (TsdFrameSlicer, tsdframe_colors),
    nap.TsdTensor: (TsdTensorSlicer, None),
    nap.TsGroup: (TsGroupRateSlicer, tsgroup_colors),
    nap.IntervalSet: (IntervalSetSlicer, intervalset_colors),
}


def dispatch(data: Any) -> tuple[type, Callable | None]:
    """
    The default slicer and color helper for a pynapple object.

    Parameters
    ----------
    data: pynapple object
        A ``Tsd``, ``TsdFrame``, ``TsdTensor``, ``TsGroup`` or ``IntervalSet``.

    Returns
    -------
    (type, Callable | None)
        ``(slicer, colors_helper)``. The helper is ``None`` for a type whose graphic has no
        per-graphic colors, i.e. an image.

    """
    try:
        return _DISPATCH[type(data)]
    except KeyError:
        pass

    if isinstance(data, nap.Ts):
        raise TypeError(
            "a bare `Ts` has no values to draw, wrap it as a group of one: "
            "`nap.TsGroup({0: ts})`"
        )

    raise TypeError(
        f"no slicer for a {type(data).__name__}, the supported pynapple types are: "
        f"{', '.join(t.__name__ for t in _DISPATCH)}"
    )


class PynappleSlicer:
    """
    The pynapple slicers, graphics and helpers, available as ``nds_extras.Pynapple`` when pynapple
    is installed.

    Use ``NDWSubplot.add_pynapple_obj()`` rather than constructing these directly. It picks the
    slicer and the graphic for the object it is given, so the two cannot be mismatched.

    Attributes
    ----------
    TsdFrame : type
        :class:`TsdFrameSlicer`, for a ``Tsd`` or a ``TsdFrame``.

    TsdTensor : type
        :class:`TsdTensorSlicer`, for a ``TsdTensor``.

    TsGroupRate : type
        :class:`TsGroupRateSlicer`, binned firing rates of a ``TsGroup``.

    TsGroupSpikes : type
        :class:`TsGroupSpikesSlicer`, the individual spikes of a ``TsGroup``.

    IntervalSet : type
        :class:`IntervalSetSlicer`, an ``IntervalSet`` rasterized into an ethogram.

    """

    TsdFrame = TsdFrameSlicer
    TsdTensor = TsdTensorSlicer
    TsGroupRate = TsGroupRateSlicer
    TsGroupSpikes = TsGroupSpikesSlicer
    IntervalSet = IntervalSetSlicer

    NDPynappleTimeseries = NDPynappleTimeseries
    NDPynappleRate = NDPynappleRate
    NDPynappleSpikes = NDPynappleSpikes
    NDPynappleEthogram = NDPynappleEthogram
    NDPynappleImage = NDPynappleImage

    dispatch = staticmethod(dispatch)
    ranges_from_time_support = staticmethod(ranges_from_time_support)
    sort_order = staticmethod(sort_order)
    metadata_codes = staticmethod(metadata_codes)
    metadata_categories = staticmethod(metadata_categories)
    tsgroup_colors = staticmethod(tsgroup_colors)
    tsdframe_colors = staticmethod(tsdframe_colors)
    intervalset_colors = staticmethod(intervalset_colors)
