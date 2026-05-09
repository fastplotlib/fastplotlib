from __future__ import annotations

import asyncio
from dataclasses import dataclass
from numbers import Number
from typing import Sequence, Any, Callable

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ._ndwidget import NDWidget
    from ._base import NDGraphic

from ...utils import loop as _loop
from ._async import run_sync


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


@dataclass
class RangeDiscrete:
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
        ``NDGraphic``, every dimension listed in ``dims`` must be either a spatial
        dimension (listed in ``spatial_dims``) or a key in ``ref_ranges``.
        If a dim is not spatial, it must have a corresponding reference range,
        otherwise an error will be raised.

        You can also define conceptually identical but *independent* reference spaces
        by using distinct names, ex: ``"time-1"`` and ``"time-2"`` for two recordings
        that should be sycned independently. Each ``NDGraphic`` then declares the
        specific "time-n" space that corresponds to its data, so the widget keeps the
        two timelines decoupled.

        Parameters
        ----------
        ref_ranges : dict[str, tuple], or a RangeContinuous
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
        self.push_dims(ref_ranges)

        # starting index for all dims
        self._indices: dict[str, int | float | Any] = {
            name: rr.start for name, rr in self._ref_ranges.items()
        }

        self._indices_changed_handlers = set()

        self._ndwidgets: list[NDWidget] = list()

        # tracks in-flight throttled render tasks so they can be cancelled when a newer
        # slider position arrives before the previous one has finished loading
        self._awaiting: dict[NDGraphic, asyncio.Task] = dict()

    @property
    def ref_ranges(self) -> dict[str, RangeContinuous | RangeDiscrete]:
        return self._ref_ranges

    @property
    def dims(self) -> set[str]:
        return set(self.ref_ranges.keys())

    def _add_ndwidget_(self, ndw: NDWidget):
        from ._ndwidget import NDWidget

        if not isinstance(ndw, NDWidget):
            raise TypeError

        self._ndwidgets.append(ndw)

    def set(self, indices: dict[str, Any], throttle: bool = False):
        for dim, value in indices.items():
            self._indices[dim] = self._clamp(dim, value)

        self._render_indices(throttle=throttle)
        self._indices_changed()

    def set_dim_index(self, dim: str, index, throttle: bool = False):
        """
        Set the index for a single dimension and trigger a render.

        Parameters
        ----------
        dim : str
            Dimension name.
        index : int or float
            New reference-space value for this dimension.
        throttle : bool, default False
            If True, cancel any in-flight render tasks before scheduling a new one.
            Use this only for rapid-fire inputs such as an imgui slider drag where
            intermediate positions are disposable. All other callers (play advance,
            step buttons, LinearSelector, programmatic updates) should leave this False.
        """
        self._check_has_dim(dim)
        self._indices[dim] = self._clamp(dim, index)
        self._render_indices(throttle=throttle)
        self._indices_changed()

    def _clamp(self, dim, value):
        if isinstance(self.ref_ranges[dim], RangeContinuous):
            return max(
                min(value, self.ref_ranges[dim].stop - self.ref_ranges[dim].step),
                self.ref_ranges[dim].start,
            )

        return value

    def _render_indices(self, throttle: bool = False):
        """
        Schedule a render for every affected NDGraphic via the rendercanvas event loop.

        When ``throttle=True``, any in-flight tasks from a previous throttled call are
        cancelled before new ones are scheduled, so rapid slider drags never queue up
        stale window_func/spatial_func work. Falls back to a synchronous drain when no
        event loop is running yet (figure not shown).
        """
        if throttle:
            for task in self._awaiting.values():
                task.cancel()
            self._awaiting.clear()

        for ndw in self._ndwidgets:
            for g in ndw.ndgraphics:
                if g.data is None or g.pause or g._block_indices:
                    continue
                indices = {d: self._indices[d] for d in g.processor.slider_dims}

                try:
                    asyncio.get_running_loop()
                except RuntimeError:
                    run_sync(g._set_indices_(indices))
                    continue

                _loop.add_task(self._render_request, g, indices, throttle, name="ndw-render")

    async def _render_request(
        self, graphic: "NDGraphic", indices: dict[str, Any], throttle: bool
    ):
        """Run the data pipeline for one graphic and write the result."""
        if throttle:
            self._awaiting[graphic] = asyncio.current_task()
        try:
            await graphic._set_indices_(indices)
        except asyncio.CancelledError:
            pass
        finally:
            if throttle and self._awaiting.get(graphic) is asyncio.current_task():
                del self._awaiting[graphic]

    def __getitem__(self, dim):
        self._check_has_dim(dim)
        return self._indices[dim]

    def _check_has_dim(self, dim):
        if dim not in self.dims:
            raise KeyError(
                f"provided dimension: {dim} has no associated ReferenceRange in this ReferenceIndex, valid dims in this ReferenceIndex are: {self.dims}"
            )

    def pop_dim(self):
        pass

    def push_dims(self, ref_ranges: dict[
            str,
            tuple[Number, Number, Number] | tuple[Any] | RangeContinuous,
        ],):

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
