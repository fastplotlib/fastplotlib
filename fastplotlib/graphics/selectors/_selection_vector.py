from collections.abc import Callable
from functools import partial
from typing import Any, Sequence, TypeAlias
from numbers import Integral

import numpy as np

from ._protocols import SelectorProtocol, MultiSelectorProtocol

Mapping = np.ndarray | dict[int, int] | Callable

def identity(val: Any) -> Any:
    return val

def array_map(arr: np.ndarray, index: Integral):
    """
    Used to map local to global indices
    """
    return None if np.isnan(arr[index]) else int(arr[index])

def inv_array_map(arr: np.ndarray,
                value: int) -> None | int:
    """
    arr[i] gives the global index
    """
    x = np.flatnonzero(arr == value)
    return None if x.size == 0 else int(x[0])

def dict_map(my_dict: dict, key: Integral):
    if key is None:
        return None
    elif int(key) not in my_dict:
        return None
    else:
        return my_dict[key]


class SelectionVector:
    """
    A class for performing coordinated selections across multiple selectors.
    For each selector in the selection vector, the user specifies how the global indices (shared across selectors)
    maps to the local indices (each selector has its own local index space).

    The SelectionVector coordinates across individual selectors, including the coordinated updating of indices whenever a selection changes
    """
    def __init__(self):
        # selector -> (map, map_inv)

        ## Key is a selector, value is a (1) local to global index map (2) global to local index map (3) list of event handlers
        self._selectors: dict[
            SelectorProtocol | MultiSelectorProtocol, tuple[Callable, Callable, list[Callable]]
        ] = dict()
        self._selection: list[Any] = list()
        self._block_reentrance = False

    @property
    def selection(self) -> tuple[Any]:
        return tuple(self._selection)

    @selection.setter
    def selection(self, new: Integral | Sequence[Any]):
        if self._block_reentrance:
            return
        else:
            self._block_reentrance = True
            if isinstance(new, Integral):
                new = [new]
            self._selection = list(new)
            for value in new:
                if value < 0:
                    raise ValueError("Only nonnegative selection indices are allowed")
            # iterate through each selector that operates in its own "local" space
            for selector_local, (map_, map_inv, handler) in self._selectors.items():
                local_indices = []
                for value in new:
                    curr_indices = map_(value)
                    local_indices.append(curr_indices)
                selector_local.selection = local_indices
            self._block_reentrance = False

    def append(self, index):
        self._selection.append(index)
        for selector, (map_, map_inv, handler_list) in self._selectors.items():
            if not isinstance(selector, MultiSelectorProtocol):
                continue

            index_local = map_(index)
            selector.append(index_local)

    def add_selector(
        self,
        new: (
            SelectorProtocol
            | tuple[SelectorProtocol, dict]
            | tuple[SelectorProtocol, np.ndarray]
            |tuple[SelectorProtocol, Callable, Callable]
        ),
    ):
        """
        User specifies (1) the selector and (2) The master --> local index mapping. This
        mapping is given either as:
            - A 1D np.ndarray of integers. The array index is the global index, and the array value is the local index
            - A dictionary where keys (master indices) and values (local indices) are both integers
            - Two callables. The first callable defines the global index --> local index map, the second specifies the local index --> global index map.
                All callables take as input nonnegative integers and output nonnegative integers. 
        """
        if isinstance(new, (tuple, list)):
            if not isinstance(new[0], SelectorProtocol):
                raise TypeError

            if len(new) == 3:
                if isinstance(new[1], Callable) and isinstance(new[2], Callable):
                    master_to_local = new[1]
                    local_to_master = new[2]
                else:
                    raise ValueError(f"Both index mappings must be Callables, you provided {type(new[1])} and {type(new[2])}")
            elif len(new) == 2:
                if isinstance(new[1], dict):
                    ## Construct inverse mapping
                    inverse_dict = dict()
                    for key, val in new[1].items():
                        inverse_dict[int(val)] = int(key)
                    master_to_local = partial(dict_map, new[1])
                    local_to_master = partial(dict_map, inverse_dict)

                elif isinstance(new[1], np.ndarray):
                    if not new[1].ndim == 1:
                        raise ValueError("If you pass in an array mapping, it must be 1-D")
                    master_to_local = partial(array_map, new[1])
                    local_to_master = partial(inv_array_map, new[1])
                else:
                    raise ValueError(f"Must either provide a single dict or numpy array specifying the local to global index mapping, or two callables"
                                     f"specifying the mapping in both directions")

            selector = new[0]

        elif isinstance(new, SelectorProtocol):
            selector, master_to_local, local_to_master = new, identity, identity

        else:
            raise ValueError

        handler = selector.add_event_handler(partial(self._inv_handler, local_to_master))
        self._selectors[selector] = (master_to_local, local_to_master, [handler])

    def _inv_handler(self, map_inv: Callable, local_selection: dict):
        """
        HighlightSelector and VisibilitySelector emit a dictionary with keys selector and value
        """
        input_to_map = local_selection['value']
        for i in range(len(input_to_map)):
            if input_to_map[i] < 0:
                raise ValueError("You can only provide nonnegative values as local indices to a selector")

        self.selection = [map_inv(input_to_map[i]) for i in range(len(input_to_map))]

    def remove_selector(self, selector: SelectorProtocol | MultiSelectorProtocol):
        if selector in self._selectors:
            map, map_inv, handler_list = self._selectors.pop(selector)
            for handler in handler_list:
                selector.remove_event_handler(handler)
            if isinstance(selector, MultiSelectorProtocol):
                selector.clear()

    def clear_selectors(self):
        for selector in self._selectors.keys():
                if isinstance(selector, MultiSelectorProtocol):
                    selector.clear()