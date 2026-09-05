from __future__ import annotations

from collections import deque
from concurrent.futures import CancelledError
from dataclasses import dataclass
from numbers import Number
from typing import Sequence, Any, Callable, Iterator

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ._ndwidget import NDWidget
    from ._base import NDGraphic

from ...utils import loop


class RangeContinuous:
    """
    A continuous reference range for a single slider dimension.

    Stores the (start, stop, step) in scientific units (ex: seconds, micrometers,
    Hz). The imgui slider for this dimension uses these values to determine its
    minimum and maximum bounds. The step size is used for the "next" and "previous" buttons.

    Parameters
    ----------
    start : int or float
        Minimum value of the range, inclusive.

    stop : int or float
        Maximum value of the range, exclusive upper bound.

    step : int or float
        Step size used for imgui step next/previous buttons

    Raises
    ------
    IndexError
        If ``start >= stop``.

    Examples
    --------
    A time axis sampled at 1 ms resolution over 10 seconds:

        RangeContinuous(start=0, stop=10_000, step=1)

    A depth axis in micrometers with 0.5 µm steps:

        RangeContinuous(start=0.0, stop=500.0, step=0.5)
    """

    def __init__(self, start: int | float, stop: int | float, step: int | float):
        if start >= stop:
            raise IndexError(
                f"start must be less than stop, {self.start} !< {self.stop}"
            )

        self._start = start
        self._stop = stop
        self._step = step
        self._throttle = 0.05

    @property
    def start(self) -> int | float:
        """get or set the start boundary of the reference range"""
        return self._start

    @start.setter
    def start(self, val: int | float):
        self._start = val

    @property
    def stop(self) -> int | float:
        """get or set the stop boundary of the reference range"""
        return self._stop

    @stop.setter
    def stop(self, val: int | float):
        self._stop = val

    @property
    def step(self) -> int | float:
        """get or set the step size of the range, only used for UI elements"""
        return self._step

    @property
    def throttle(self) -> float:
        """get or set the minimum time in seconds between slider-drag renders"""
        return self._throttle

    @throttle.setter
    def throttle(self, val: float):
        if val < 0:
            raise ValueError("throttle value must be >= 0.0")
        self._throttle = val

    @property
    def size(self) -> int | float:
        """the size of the reference range"""
        return self.stop - self.start

    def __getitem__(self, index: int):
        """return the value at the index w.r.t. the step size"""
        if index < 0:
            raise ValueError("negative indexing not supported")

        val = self.start + (self.step * index)
        if not self.start <= val <= self.stop:
            raise IndexError(
                f"index: {index} value: {val} out of bounds: [{self.start}, {self.stop}]"
            )

        return val


class AutoRangeContinuous(RangeContinuous):
    """
    A continuous reference range that was auto-generated for a slider dimension
    which had no explicit ``RangeContinuous``.
    """


@dataclass
class RangeDiscrete:
    """
    A discrete reference range for a single slider dimension, where the reference-space values are arbitrary
    objects (ex: gene names, experimental conditions) rather than a numerical range.

    .. important::
        Not implemented yet, this is a placeholder. The imgui slider is only drawn for a
        :class:`RangeContinuous`.

    Parameters
    ----------
    options: Sequence[Any]
        The reference-space values of this dimension, in order.

    """

    # TODO: not implemented yet, placeholder until we have a clear usecase
    options: Sequence[Any]

    def __getitem__(self, index: int):
        if index > len(self.options):
            raise IndexError

        return self.options[index]

    def __len__(self):
        return len(self.options)


class ReferenceIndex:
    def __init__(
        self,
        ref_ranges: dict[
            str,
            tuple[Number, Number, Number] | tuple[Any] | RangeContinuous,
        ],
    ):
        """
        Manages the shared reference index for one or more ``NDWidget`` instances.

        Stores the current index for each named slider dimension in reference-space
        units (ex: seconds, depth in µm, Hz). Whenever an index is updated, every
        ``NDGraphic`` in the manged ``NDWidgets`` are requested to render data at
        the new indices.

        Each key in ``ref_ranges`` defines a slider dimension. When adding an
        ``NDGraphic``, every dimension listed in ``dims`` is either a spatial
        dimension (listed in ``spatial_dims``) or a slider dimension. A slider
        dim without a reference range gets an ``AutoRangeContinuous`` sized to the
        data, so an explicit range is only needed when the slider should map
        reference-space units to array indices rather than use a one-to-one
        (identity) mapping.

        You can also define conceptually identical but *independent* reference spaces
        by using distinct names, ex: ``"time-1"`` and ``"time-2"`` for two subsets of data
        that should be sycned independently. Each ``NDGraphic`` then declares the
        specific ``"time-n"`` space that corresponds to its data, so the widget keeps the
        two timelines decoupled.

        Parameters
        ----------
        ref_ranges : dict[str, tuple | RangeContinuous]
            Mapping of dimension names to range specifications. A 3-tuple
            ``(start, stop, step)`` creates a :class:`RangeContinuous`. A 1-tuple
            ``(options,)`` creates a :class:`RangeDiscrete`.

        Attributes
        ----------
        ref_ranges : dict[str, RangeContinuous | RangeDiscrete]
            The reference range for each registered slider dimension.

        dims: set[str]
            the set of "slider dims"

        Examples
        --------
        Single shared time axis:

            ri = ReferenceIndex(ref_ranges={"time": (0, 1000, 1), "depth": (15, 35, 0.5)})
            ri.set_dim_index("time", 500)           # update one dim and re-render
            ri.set({"time": 500, "depth": 10})      # update several dims atomically

        Two independent time axes for data from two different recording sessions:

            ri = ReferenceIndex({
                "time-1": (0, 3600, 1),   # session 1 — 1 h at 1 s resolution
                "time-s": (0, 1800, 1),   # session 2 — 30 min at 1 s resolution
            })

        Each ``NDGraphic`` declares matching names for slider dims to indicate that these should be
        synced across graphics.

            ndw[0, 0].add_nd_image(data_s1, ("time-s1", "row", "col"), ("row", "col"))
            ndw[0, 1].add_nd_image(data_s2, ("time-s2", "row", "col"), ("row", "col"))

        """
        self._ref_ranges = dict()

        # current index for each dim
        self._indices: dict[str, int | float | Any] = dict()

        self._ndwidgets: list[NDWidget] = list()

        self.push_dims(ref_ranges)

        self._indices_changed_handlers = set()

        # per-NDGraphic fetch update revision. Bumped on every ``cancel_awaiting=True``
        # call (display only latest fetch, used during slider drag). A scheduled fetch
        # carries the revision it was created under and skips setting graphic data
        # if a newer revision has been requested
        self._fetch_rev: dict[NDGraphic, int] = dict()

        # per-graphic queue of pending fetch requests for the serial
        # path (i.e. ``cancel_awaiting=False``). Used for play, step, programmatic updates,
        # and LinearSelector. Each entry is ``(indices, rev)``. Emptied by
        # :meth:`_fetch_request`
        self._fetch_request_queue: dict[
            NDGraphic, deque[tuple[dict[str, Any], int]]
        ] = dict()

        # per-graphic flag, indicates whether :meth:`_fetch_request` is currently emptying
        # ``_fetch_request_queue[ndg]``? Ensures only one coroutine is
        # alive per graphic. Subsequent ``cancel_awaiting=False`` calls just
        # append to the queue.
        self._fetch_request_active: dict[NDGraphic, bool] = dict()

    @property
    def ref_ranges(self) -> dict[str, RangeContinuous | RangeDiscrete]:
        """current reference ranges"""
        return self._ref_ranges

    @property
    def dims(self) -> set[str]:
        """reference dimensions"""
        return set(self.ref_ranges.keys())

    def _add_ndwidget_(self, ndw: NDWidget):
        """add an NDWidget instance to be managed by this ReferenceIndex"""
        from ._ndwidget import NDWidget

        if not isinstance(ndw, NDWidget):
            raise TypeError

        self._ndwidgets.append(ndw)

    def set(self, indices: dict[str, Any], cancel_awaiting: bool = False):
        """
        Set the index for each dimension in indices

        Parameters
        ----------
        indices: dict[str, Any]
            indices to set, ``{dim: index}``, in reference-space units. Values are clamped to the reference
            range of that dim.

        cancel_awaiting: bool, default ``False``
            cancel in-progress fetches, i.e. only display the latest fetch request

        """
        for dim, value in indices.items():
            self._indices[dim] = self._clamp(dim, value)

        self._fetch_indices(cancel_awaiting=cancel_awaiting)
        self._indices_changed()

    @property
    def ndgraphics(self) -> Iterator[NDGraphic]:
        """All the NDGraphics that this ReferenceIndex instance manages"""

        for ndw in self._ndwidgets:
            yield from ndw.ndgraphics

    def set_dim_index(self, dim: str, index: int | float, cancel_awaiting: bool = False):
        """
        Set the index for a single dimension and trigger an update.

        Parameters
        ----------
        dim : str
            Dimension name.

        index : int or float
            New reference-space value for this dimension.

        cancel_awaiting : bool, default False
            If True, cancel any in-progress fetch tasks before scheduling a new one.
            Used only for fast inputs, currently only for the imgui slider so every single
            intermediate position during a slider drag isn't fetched & rendered.
            All other methods of fetching data (play, step buttons, LinearSelector,
            programmatic updates) use cancel_awaiting=False to display every data fetch.

        """

        self._check_has_dim(dim)
        self._indices[dim] = self._clamp(dim, index)

        for ndg in self.ndgraphics:
            # set only for NDGraphics that have this dim
            if dim in ndg.dims:
                self._schedule_fetch(ndg, cancel_awaiting=cancel_awaiting)

        self._indices_changed()

    def _clamp(self, dim: str, value: int | float):
        """clamp the given index value within the valid range for this dimension"""

        if isinstance(self.ref_ranges[dim], RangeContinuous):
            return max(
                min(value, self.ref_ranges[dim].stop - self.ref_ranges[dim].step),
                self.ref_ranges[dim].start,
            )

        return value

    def _fetch_indices(self, cancel_awaiting: bool = False):
        """
        Schedule a fetch for every NDGraphic.
        """

        for g in self.ndgraphics:
            self._schedule_fetch(g, cancel_awaiting=cancel_awaiting)

    def _schedule_fetch(self, ndg: NDGraphic, cancel_awaiting: bool = False):
        """
        Schedule fetch for an NDGraphic

        This entry point has 2 paths:

        * ``cancel_awaiting=True`` used for fast inputs, currently only for the imgui slider where
        we don't want to fetch & render every intermediate position during a slider drag. Schedules a new
          ``_set_indices_`` task via :meth:`_render_request_latest`. Any in-progress tasks skip
          setting graphic data. ``_fetch_rev`` is used so only the latest revision is rendered.

        - ``cancel_awaiting=False`` used by play, step button, LinearSelector, programmatic updates.
        Every request will fetch & render. Requests are queued per graphic and processed in sequence
        by :meth:`_render_request`.
        """

        if ndg.data is None or ndg.pause or ndg._block_indices:
            # skip fetch for this graphic
            return

        task_name = f"ndw-fetch:{type(ndg).__name__}"
        if ndg.name is not None:
            task_name = f"{task_name}:{ndg.name}"

        if cancel_awaiting:
            # bump revision so older in-progress fetches skip setting graphic data
            self._fetch_rev[ndg] = self._fetch_rev.get(ndg, 0) + 1
            rev = self._fetch_rev[ndg]

            # add to rendercanvas scheduler
            loop.add_task(
                self._fetch_request_latest, ndg, rev, name=task_name
            )
        else:
            rev = self._fetch_rev.get(ndg, 0)
            # provide index at schedule time so all data is played back sequentially
            indices = {d: self._indices[d] for d in ndg.processor.slider_dims}
            self._fetch_request_queue.setdefault(ndg, deque()).append(
                (indices, rev)
            )
            # one queue per graphic
            # if one is already running the appended entry will be picked up by it
            if not self._fetch_request_active.get(ndg, False):
                self._fetch_request_active[ndg] = True
                loop.add_task(self._fetch_request, ndg, name=task_name)

    async def _fetch_request(self, graphic: "NDGraphic"):
        """
        Process ``_fetch_request_queue[graphic]`` one entry at a time. Each
        ``_set_indices_`` is awaited fully before the next entry is popped,
        so only one ``_set_indices_`` is in-progress per graphic from this
        path.
        A concurrent :meth:`_fetch_request_latest` for the same
        graphic can still cancel an in-progress fetch; the resulting
        :class:`CancelledError` is dropped.
        """
        try:
            queue = self._fetch_request_queue[graphic]
            while queue:
                indices, rev = queue.popleft()
                if rev < self._fetch_rev.get(graphic, 0):
                    # a rapid-fire request superseded this queued entry; skip
                    continue
                try:
                    await graphic._set_indices_(indices)
                except CancelledError:
                    # concurrent _fetch_request_latest canceled our read on ``data``
                    pass
            del self._fetch_request_queue[graphic]
        finally:
            self._fetch_request_active[graphic] = False

    async def _fetch_request_latest(
        self, graphic: "NDGraphic", rev: int
    ):
        """
        Schedule one ``_set_indices_`` task. Older still-running tasks skip
        their graphic data write when ``rev < current``.
        Some ``data`` objects cancel the
        previous in-flight read when a new index is requested; the resulting
        :class:`CancelledError` is dropped.
        """
        if rev < self._fetch_rev.get(graphic, 0):
            # a newer rapid-fire request superseded us; drop the write
            return
        try:
            await graphic._set_indices_()
        except CancelledError:
            # ``data`` cancelled this read in favour of a newer one
            pass

    def __getitem__(self, dim):
        self._check_has_dim(dim)
        return self._indices[dim]

    def _check_has_dim(self, dim):
        if dim not in self.dims:
            raise KeyError(
                f"provided dimension: {dim} has no associated ReferenceRange in this ReferenceIndex, valid dims in this ReferenceIndex are: {self.dims}"
            )

    def pop_dim(self):
        """
        Remove a slider dim and its reference range.

        .. important::
            Not implemented yet, this is a placeholder that does nothing.

        """
        pass

    def push_dims(
        self,
        ref_ranges: dict[
            str,
            tuple[Number, Number, Number] | tuple[Any] | RangeContinuous,
        ],
    ):
        """
        Add reference ranges, i.e. register new slider dims.

        The index of each new dim is initialized to the start of its range, and a slider for it is added to the
        UI of every ``NDWidget`` managed by this ``ReferenceIndex``.

        Parameters
        ----------
        ref_ranges: dict[str, tuple | RangeContinuous | RangeDiscrete]
            Mapping of dim names to range specifications. A 3-tuple ``(start, stop, step)`` creates a
            :class:`RangeContinuous`, a 1-tuple ``(options,)`` creates a :class:`RangeDiscrete`, and a
            ``RangeContinuous`` or ``RangeDiscrete`` instance is used as given. An existing dim of the same name
            is replaced.

        """

        for name, r in ref_ranges.items():
            if isinstance(r, (RangeContinuous, RangeDiscrete)):
                self._ref_ranges[name] = r

            elif len(r) == 3:
                # assume start, stop, step
                self._ref_ranges[name] = RangeContinuous(*r)

            elif len(r) == 1:
                # assume just options
                self._ref_ranges[name] = RangeDiscrete(*r)

            else:
                raise ValueError(
                    f"ref_ranges must be a mapping of dimension names to range specifications, "
                    f"see the docstring, you have passed: {ref_ranges}"
                )

            rr = self._ref_ranges[name]
            if isinstance(rr, AutoRangeContinuous):
                self._indices[name] = 0
            elif isinstance(rr, RangeContinuous):
                self._indices[name] = rr.start
            elif isinstance(rr, RangeDiscrete):
                # start at the first option
                self._indices[name] = rr.options[0]

            # set imgui UI for each NDWidget window
            for ndw in self._ndwidgets:
                ndw._sliders_ui.push_dim(name)

    def add_event_handler(self, handler: Callable, event: str = "indices"):
        """
        Register an event handler that is called whenever the indices change.

        Parameters
        ----------
        handler: Callable
            callback function, must take a tuple of int as the only argument. This tuple will be the `indices`

        event: str, "indices"
            the only supported valid is "indices"

        Example
        -------

        .. code-block:: py

            def my_handler(indices):
                print(indices)
                # example prints: {"t": 100, "z": 15} if the index has 2 reference spaces "t" and "z"

            # create an NDWidget
            ndw = NDWidget(...)

            # add event handler
            ndw.indices.add_event_handler(my_handler)

        """
        if event != "indices":
            raise ValueError("`indices` is the only event supported by `GlobalIndex`")

        self._indices_changed_handlers.add(handler)

    def remove_event_handler(self, handler: Callable):
        """Remove a registered event handler"""
        self._indices_changed_handlers.remove(handler)

    def clear_event_handlers(self):
        """Clear all registered event handlers"""
        self._indices_changed_handlers.clear()

    def _indices_changed(self):
        # calls indices changed handlers
        for f in self._indices_changed_handlers:
            f(self._indices)

    def __iter__(self):
        for index in self._indices.items():
            yield index

    def __len__(self):
        return len(self._indices)

    def __eq__(self, other):
        return self._indices == other

    def __repr__(self):
        return f"Global Index: {self._indices}"

    def __str__(self):
        return str(self._indices)


# TODO: Not sure if we'll actually do this here, just a placeholder for now
class SelectionVector:
    @property
    def selection(self):
        pass

    @property
    def graphics(self):
        pass

    def add_graphic(self):
        pass

    def remove_graphic(self):
        pass
