from dataclasses import dataclass
from typing import Sequence, Any


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
    def __init__(self):
        self._ndgraphics = list()
        self._index = list()
        self._ref_ranges = list()

    @property
    def ndgraphics(self):
        return tuple(self._ndgraphics)

    @property
    def index(self) -> tuple[Any]:
        # TODO: clamp index to given range here
        #  graphics will clamp according to their own array sizes?
        pass

    @property
    def dims(self) -> tuple[str]:
        return tuple(ref.unit for ref in self.ref_ranges)

    @property
    def ref_ranges(self) -> tuple[ReferenceRangeContinuous]:
        pass

    def __getitem__(self, item):
        if isinstance(item, int):
            # integer index in the ordered dict
            return self.ref_ranges[item]

        for rr in self.ref_ranges:
            if rr.unit == item:
                return rr

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

        index = list(self.index)

        # set index for given dim
        index[key] = value

    def __repr__(self):
        return "\n".join([f"{d}: {i}" for d, i in zip(self.dims, self.index)])


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
