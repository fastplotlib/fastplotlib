from collections.abc import Callable
from functools import partial
from typing import Any, Sequence
import numpy as np
from ._protocols import SelectorProtocol, MultiSelectorProtocol

def identity(val: Any) -> Any:
    return val

class SelectionVector:
    """
    A class for performing coordinated selections across multiple selectors.
    For each selector in the selection vector, the user specifies how the global indices (shared across selectors)
    maps to the local indices.

    The SelectionVector manages everything else, including the coordinated updating of indices whenever a selection changes
    """
    def __init__(self, max_size: int = None):
        # selector -> (map, map_inv)
        self._selectors: dict[
            SelectorProtocol | MultiSelectorProtocol, tuple[Callable, Callable, list]
        ] = dict()
        self._selection: list[Any] = list()
        self._block_reentrance = False

    @property
    def selection(self) -> tuple[Any]:
        return tuple(self._selection)

    @selection.setter
    def selection(self, new: Sequence[Any]):
        if self._block_reentrance:
            return
        else:
            self._block_reentrance = True
            # iterate through each selector that operates in its own "local" space
            for selector_local, (map_, map_inv) in self._selectors.items():
                indices_local = map_(new)
                selector_local.selection = indices_local
            self._block_reentrance = False

    def append(self, index):
        self._selection.append(index)
        for selector, (map_, map_inv, handler_list) in self._selectors.items():
            if not isinstance(selector, MultiSelectorProtocol):
                continue

            index_local = map_([index])
            selector.append(index_local)

    def add_selector(
        self,
        new: (
            SelectorProtocol
            | tuple[SelectorProtocol, np.ndarray | dict[int, int]]
        ),
    ):
        """
        User specifies (1) the selector and (2) The master --> local index mapping. This
        mapping is given either as:
            - A 1D np.ndarray of integers. The array index is the global index, and the array value is the local index
            - A dictionary where keys (master indices) and values (local indices) are both integers
        """
        selector: SelectorProtocol
        if isinstance(new, (tuple, list)):
            if not isinstance(new[0], SelectorProtocol):
                raise TypeError

            if len(new) != 2:
                raise TypeError

            selector = new[0]
            master_to_local = new[1]
            if isinstance(master_to_local, np.ndarray):
                if not master_to_local.ndim == 1:
                    raise ValueError("If you pass in an array mapping, it must be 1-D")
                master_to_local = dict(enumerate(master_to_local))

            ## Construct inverse mapping
            inverse_dict = dict()
            for key, val in master_to_local.items():
                inverse_dict[val] = key

            ## Define the partial functions
            master_to_local_map = lambda x:master_to_local[x] if x in master_to_local else None
            local_to_master_map = lambda x:inverse_dict[x] if x in inverse_dict else None

        elif isinstance(new, SelectorProtocol):
            selector, master_to_local_map, local_to_master_map = new, identity, identity

        else:
            raise ValueError

        handler = selector.add_event_handler(partial(self._inv_handler, local_to_master_map))
        self._selectors[selector] = (master_to_local_map, local_to_master_map, [handler])

    def _inv_handler(self, map_inv: Callable, local_selection):
        self._selection = map_inv(local_selection)

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