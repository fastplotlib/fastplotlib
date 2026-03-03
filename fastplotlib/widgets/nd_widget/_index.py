from dataclasses import dataclass
from typing import Sequence, Any, Callable

from .base import NDGraphic


@dataclass
class ReferenceRangeContinuous:
    name: str
    unit: str
    start: int | float
    stop: int | float
    step: int | float

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
class ReferenceRangeDiscrete:
    name: str
    unit: str
    options: Sequence[Any]

    def __getitem__(self, index: int):
        if index > len(self.options):
            raise IndexError

        return self.options[index]

    def __len__(self):
        return len(self.options)


class GlobalIndex:
    def __init__(self, ref_ranges: dict[str, tuple], get_ndgraphics: Callable[[], tuple[NDGraphic]]):
        self._ref_ranges = dict()

        for r in ref_ranges.values():
            if len(r) == 5:
                # assume name, unit, start, stop, step
                rr = ReferenceRangeContinuous(*r)
            elif len(r) == 3:
                rr = ReferenceRangeDiscrete(*r)
            else:
                raise ValueError

            self._ref_ranges[rr.name] = rr

        self._get_ndgraphics = get_ndgraphics

        # starting index for all dims
        self._indices: dict[str, int | float | Any] = {rr.name: rr.start for rr in self._ref_ranges.values()}

    def set(self, indices: dict[str, Any]):
        for k in self._indices:
            self._indices[k] = indices[k]

        self._render_indices()

    def _render_indices(self):
        for g in self._get_ndgraphics():
            g.indices = {d: self._indices[d] for d in g.processor.slider_dims}

    @property
    def ref_ranges(self) -> dict[str, ReferenceRangeContinuous | ReferenceRangeDiscrete]:
        return self._ref_ranges

    def __getitem__(self, dim):
        return self._indices[dim]

    def __setitem__(self, dim, value):
        # set index for given dim and render

        # clamp within reference range
        if isinstance(self.ref_ranges[dim], ReferenceRangeContinuous):
            value = max(min(value, self.ref_ranges[dim].stop - self.ref_ranges[dim].step), self.ref_ranges[dim].start)

        self._indices[dim] = value
        self._render_indices()

    def pop_dim(self):
        pass

    def push_dim(self, ref_range: ReferenceRangeContinuous):
        # TODO: implement pushing and popping dims
        pass

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
