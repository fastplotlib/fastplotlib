from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence, Any, Callable

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ._ndwidget import NDWidget


@dataclass
class RangeContinuous:
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
        ref_ranges: dict[str, tuple],
    ):
        self._ref_ranges = dict()

        for name, r in ref_ranges.items():
            if len(r) == 3:
                # assume start, stop, step
                self._ref_ranges[name] = RangeContinuous(*r)

            elif len(r) == 1:
                # assume just options
                self._ref_ranges[name] = RangeDiscrete(*r)

            else:
                raise ValueError

        # starting index for all dims
        self._indices: dict[str, int | float | Any] = {
            name: rr.start for name, rr in self._ref_ranges.items()
        }

        self._indices_changed_handlers = set()

        self._ndwidgets: list[NDWidget] = list()

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
                if g.data is None:
                    continue
                # only provide slider indices to the graphic
                g.indices = {d: self._indices[d] for d in g.processor.slider_dims}

    @property
    def ref_ranges(self) -> dict[str, RangeContinuous | RangeDiscrete]:
        return self._ref_ranges

    def __getitem__(self, dim):
        return self._indices[dim]

    def __setitem__(self, dim, value):
        # set index for given dim and render
        self._indices[dim] = self._clamp(dim, value)
        self._render_indices()

    def pop_dim(self):
        pass

    def push_dim(self, ref_range: RangeContinuous):
        # TODO: implement pushing and popping dims
        pass

    def add_event_handler(self, handler: Callable, event: str = "indices"):
        """
        Register an event handler.

        Currently the only event that ImageWidget supports is "indices". This event is
        emitted whenever the indices of the ImageWidget changes.

        Parameters
        ----------
        handler: Callable
            callback function, must take a tuple of int as the only argument. This tuple will be the `indices`

        event: str, "indices"
            the only supported event is "indices"

        Example
        -------

        .. code-block:: py

            def my_handler(indices):
                print(indices)
                # example prints: {"t": 100, "z": 15} if the index has 2 slider dimensions "t" and "z"

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
