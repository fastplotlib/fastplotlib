from dataclasses import dataclass
from typing import Sequence, Any, Callable

from .base import NDGraphic


@dataclass
class ReferenceRangeContinuous:
    start: int | float
    stop: int | float
    step: int | float
    unit: str

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
    options: Sequence[Any]
    unit: str

    def __getitem__(self, index: int):
        if index > len(self.options):
            raise IndexError

        return self.options[index]

    def __len__(self):
        return len(self.options)


class GlobalIndexVector:
    def __init__(self, ref_ranges: list, get_ndgraphics: Callable):
        self._ref_ranges = list()

        for r in ref_ranges:
            if len(r) == 4:
                # assume start, stop, step, unit
                refr = ReferenceRangeContinuous(*r)
            elif len(r) == 2:
                refr = ReferenceRangeDiscrete(*r)
            else:
                raise ValueError

            self._ref_ranges.append(refr)

        self._get_ndgraphics = get_ndgraphics

        # starting index for all dims
        self._indices = [refr[0] for refr in self.ref_ranges]

    @property
    def indices(self) -> tuple[Any]:
        # TODO: clamp index to given ref range here
        #  graphics will clamp according to their own array sizes?
        return tuple(self._indices)

    @indices.setter
    def indices(self, new_indices: tuple[Any]):
        self._indices[:] = new_indices
        self._render_indices()

    def _render_indices(self):
        for g in self._get_ndgraphics():
            g.indices = self.indices

    @property
    def dims(self) -> tuple[str]:
        return tuple(ref.unit for ref in self.ref_ranges)

    @property
    def ref_ranges(self) -> tuple[ReferenceRangeContinuous]:
        return tuple(self._ref_ranges)

    def __getitem__(self, item):
        if isinstance(item, int):
            # integer index in the list
            return self._indices[item]

        for i, rr in enumerate(self.ref_ranges):
            if rr.unit == item:
                return self._indices[i]

        raise KeyError

    def __setitem__(self, key, value):
        # TODO: set the index for the given dimension only
        if isinstance(key, str):
            for i, rr in enumerate(self.ref_ranges):
                if rr.unit == key:
                    key = i
                    break
            else:
                raise KeyError

        # set index for given dim
        self._indices[key] = value
        self._render_indices()

    def pop_dim(self):
        pass

    def push_dim(self, ref_range: ReferenceRangeContinuous):
        # TODO: implement pushing and popping dims
        pass

    def __iter__(self):
        for index in self.indices:
            yield index

    def __len__(self):
        return len(self._indices)

    def __eq__(self, other):
        return self._indices == other

    def __repr__(self):
        named = ", ".join([f"{d}: {i}" for d, i in zip(self.dims, self.index)])
        return f"Indices: {named}"


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
