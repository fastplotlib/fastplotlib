from collections.abc import Callable
from functools import partial
import numpy as np
from typing import Any, Protocol, runtime_checkable, Sequence


@runtime_checkable
class Selector(Protocol):
    @property
    def selection(self):
        ...

    @selection.setter
    def selection(self, new):
        ...

    def add_event_handler(self, handler: Callable):
        ...

    def remove_event_handler(self, handler: Callable):
        ...


@runtime_checkable
class MultiSelector(Selector, Protocol):
    def append(self, item):
        ...

    def remove(self, item):
        ...

    def clear(self):
        ...


def identity(val: Any) -> Any:
    return val


class SelectionVector:
    def __init__(self, max_size: int = None):
        # selector -> (map, map_inv)
        self._selectors: dict[Selector | MultiSelector, tuple[Callable, Callable]] = dict()
        self._selection: list[Any] = list()

    @property
    def selection(self) -> tuple[Any]:
        return tuple(self._selection)

    @selection.setter
    def selection(self, new: Sequence[Any]):
        for selector, (map_, map_inv) in self._selectors.items():
            index_local = map_(new)
            selector.selection = index_local

    def append(self, index):
        self._selection.append(index)
        for selector, (map_, map_inv) in self._selectors.items():
            if not isinstance(selector, MultiSelector):
                continue

            index_local = map_(index)
            selector.append(index_local)

    def clear(self):
        self._selection.clear()
        # TODO: clear selectors

    def add_selector(
        self,
        new: (
                Selector
                | tuple[Selector, Callable]
                | tuple[Selector, Callable, Callable]
        ),
    ):
        selector: Selector
        map_: Callable
        map_inv: Callable

        if isinstance(new, (tuple, list)):
            if not isinstance(new[0], Selector):
                raise TypeError

            if len(new) not in (2, 3):
                raise TypeError

            if not all(callable(c) for c in new[1:]):
                raise TypeError

            selector = new[0]
            map_ = new[1]
            map_inv = new[2] if len(new) == 3 else identity

        elif isinstance(new, Selector):
            selector, map_, map_inv = new, identity, identity

        else:
            raise ValueError

        selector.add_event_handler(partial(self._inv_handler, map_inv))

        self._selectors[selector] = (map_, map_inv)

    def _inv_handler(self, map_inv: Callable, local_selection):
        # when a selectable changes its selection, set global index change using map inverse
        self._selection = map_inv(local_selection)

    def remove(self):
        pass

    def clear_selectables(self):
        self._selectors.clear()


sv = SelectionVector()
