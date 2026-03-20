from __future__ import annotations

from dataclasses import dataclass
from numbers import Number
from typing import Sequence, Any, Callable

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ._ndwidget import NDWidget


@dataclass
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

    start: int | float
    stop: int | float
    step: int | float

    def __post_init__(self):
        if self.start >= self.stop:
            raise IndexError(
                f"start must be less than stop, {self.start} !< {self.stop}"
            )

    def __getitem__(self, index: int):
        """return the value at the index w.r.t. the step size"""
        # if index is negative, turn to positive index
        if index < 0:
            raise ValueError("negative indexing not supported")

        val = self.start + (self.step * index)
        if not self.start <= val <= self.stop:
            raise IndexError(
                f"index: {index} value: {val} out of bounds: [{self.start}, {self.stop}]"
            )

        return val

    @property
    def range(self) -> int | float:
        return self.stop - self.start


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
            ri["time"] = 500          # update one dim and re-render
            ri.set({"time": 500, "depth": 10})  # update several dims atomically

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

    def set(self, indices: dict[str, Any]):
        for dim, value in indices.items():
            self._indices[dim] = self._clamp(dim, value)

        self._render_indices()

    def _clamp(self, dim, value):
        if isinstance(self.ref_ranges[dim], RangeContinuous):
            return max(
                min(value, self.ref_ranges[dim].stop - self.ref_ranges[dim].step),
                self.ref_ranges[dim].start,
            )

        return value

    def _render_indices(self):
        for ndw in self._ndwidgets:
            for g in ndw.ndgraphics:
                if g.data is None or g.pause:
                    continue
                # only provide slider indices to the graphic
                g.indices = {d: self._indices[d] for d in g.processor.slider_dims}

    def __getitem__(self, dim):
        self._check_has_dim(dim)
        return self._indices[dim]

    def __setitem__(self, dim, value):
        self._check_has_dim(dim)
        # set index for given dim and render
        self._indices[dim] = self._clamp(dim, value)
        self._render_indices()

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
