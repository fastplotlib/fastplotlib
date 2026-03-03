from collections.abc import Callable, Hashable, Sequence
from contextlib import contextmanager
import inspect
from numbers import Real
from typing import Literal, Any
from warnings import warn

import xarray as xr
import numpy as np
from numpy.typing import ArrayLike

from ...utils import subsample_array, ArrayProtocol
from ...graphics import Graphic

# must take arguments: array-like, `axis`: int, `keepdims`: bool
WindowFuncCallable = Callable[[ArrayLike, int, bool], ArrayLike]


def identity(index: int) -> int:
    return round(index)


class BaseNDProcessor:
    @property
    def data(self) -> Any:
        pass

    @property
    def shape(self) -> dict[Hashable, int]:
        pass

    @property
    def ndim(self):
        pass

    @property
    def spatial_dims(self) -> tuple[Hashable, ...]:
        pass

    @property
    def slider_dims(self):
        pass

    @property
    def window_funcs(
        self,
    ) -> dict[Hashable, tuple[WindowFuncCallable | None, int | float | None]]:
        # {dim: (func, size)}
        pass

    @property
    def window_funcs_order(self) -> tuple[Hashable]:
        pass

    @property
    def index_mappings(self) -> dict[Hashable, Callable[[Any], int] | ArrayLike]:
        pass

    def get(self, **indices):
        raise NotImplementedError


class NDProcessor:
    def __init__(
        self,
        data,
        dims: Sequence[Hashable],
        spatial_dims: Sequence[Hashable] | None,
        index_mappings: dict[Hashable, Callable[[Any], int] | ArrayLike] = None,
        window_funcs: dict[
            Hashable, tuple[WindowFuncCallable | None, int | float | None]
        ] = None,
        window_funcs_order: tuple[Hashable, ...] = None,
        spatial_func: Callable[[ArrayProtocol], ArrayProtocol] | None = None,
    ):
        self._data = self._validate_data(data, dims)
        self.spatial_dims = spatial_dims

        self.index_mappings = index_mappings

        self.window_funcs = window_funcs
        self.window_order = window_funcs_order

    @property
    def data(self) -> xr.DataArray:
        return self._data

    @data.setter
    def data(self, data: ArrayProtocol):
        self._data = self._validate_data(data, self.dims)

    def _validate_data(self, data: ArrayProtocol, dims):
        if not isinstance(data, ArrayProtocol):
            raise TypeError("`data` must implement the ArrayProtocol")

        if data.ndim != len(dims):
            raise IndexError("must specify a dim for every dimension in the data array")

        return xr.DataArray(data, dims=dims)

    @property
    def shape(self) -> dict[Hashable, int]:
        """interpreted shape of the data"""
        return {d: n for d, n in zip(self.dims, self.data.shape)}

    @property
    def ndim(self) -> int:
        """number of dims"""
        return self.data.ndim

    @property
    def dims(self) -> tuple[Hashable, ...]:
        """dim names"""
        return self.data.dims

    @property
    def spatial_dims(self) -> tuple[Hashable, ...]:
        return self._spatial_dims

    @spatial_dims.setter
    def spatial_dims(self, sdims: Sequence[Hashable]):
        for dim in sdims:
            if dim not in self.dims:
                raise KeyError

        self._spatial_dims = tuple(sdims)

    @property
    def tooltip(self) -> bool:
        """
        whether or not a custom tooltip formatter method exists
        """
        return False

    def tooltip_format(self, *args) -> str | None:
        """
        Override in subclass to format custom tooltips
        """
        return None

    @property
    def slider_dims(self) -> set[Hashable]:
        return set(self.dims) - set(self.spatial_dims)

    @property
    def n_slider_dims(self):
        return len(self.slider_dims)

    @property
    def window_funcs(
        self,
    ) -> dict[Hashable, tuple[WindowFuncCallable | None, int | float | None]]:
        """get or set window functions, see docstring for details"""
        return self._window_funcs

    @window_funcs.setter
    def window_funcs(
        self,
        window_funcs: (
            dict[Hashable, tuple[WindowFuncCallable | None, int | float | None] | None]
            | None
        ),
    ):
        if window_funcs is None:
            # tuple of (None, None) makes the checks easier in _apply_window_funcs
            self._window_funcs = {d: (None, None) for d in self.slider_dims}
            return

        for k in window_funcs.keys():
            if k not in self.slider_dims:
                raise KeyError

            func = window_funcs[k][0]
            size = window_funcs[k][1]

            if func is None:
                pass
            elif callable(func):
                sig = inspect.signature(func)

                if "axis" not in sig.parameters or "keepdims" not in sig.parameters:
                    raise TypeError(
                        f"Each window function must take an `axis` and `keepdims` argument, "
                        f"you passed: {func} with the following function signature: {sig}"
                    )
            else:
                raise TypeError(
                    f"`window_funcs` must be a dict mapping dim names to a tuple of the window function callable and "
                    f"window size, {'name': (func, size), ...}.\nYou have passed: {window_funcs}"
                )

            if size is None:
                pass

            elif not isinstance(size, Real):
                raise TypeError

            elif size < 0:
                raise ValueError

        # fill in rest with None
        for d in self.slider_dims:
            if d not in window_funcs.keys():
                window_funcs[d] = (None, None)

        self._window_funcs = window_funcs

    @property
    def window_order(self) -> tuple[Hashable, ...]:
        """get or set dimension order in which window functions are applied"""
        return self._window_order

    @window_order.setter
    def window_order(self, order: tuple[Hashable] | None):
        if order is None:
            self._window_order = tuple()
            return

        if not set(order).issubset(self.slider_dims):
            raise ValueError(
                f"each dimension in `window_order` must be a slider dim. You passed order: {order} "
                f"and the slider dims are: {self.slider_dims}"
            )

        self._window_order = tuple(order)

    @property
    def spatial_func(self) -> Callable[[ArrayProtocol], ArrayProtocol] | None:
        pass

    @property
    def index_mappings(self) -> dict[Hashable, Callable[[Any], int]]:
        return self._index_mappings

    @index_mappings.setter
    def index_mappings(self, maps: dict[Hashable, Callable[[Any], int] | ArrayLike | None] | None):
        if maps is None:
            self._index_mappings = {d: identity for d in self.dims}
            return

        for d in maps.keys():
            if d not in self.slider_dims:
                raise KeyError

            if isinstance(maps[d], ArrayProtocol):
                # create a searchsorted mapping function automatically
                maps[d] = maps[d].searchsorted

            elif maps[d] is None:
                # assign identity mapping
                maps[d] = identity

        for d in self.dims:
            # fill in any unspecified maps with identity
            if d not in maps.keys():
                maps[d] = identity

        self._index_mappings = maps

    def _ref_index_to_array_index(self, dim: str, ref_index: Any) -> int:
        # wraps index mappings, clamps between 0 and max array index for this dimension
        index = self.index_mappings[dim](ref_index)

        return max(min(index, self.shape[dim] - 1), 0)

    def _get_slider_dims_indexer(self, indices) -> dict:
        if set(indices.keys()) != set(self.slider_dims):
            raise IndexError(
                f"Must provide an index for all slider dims: {self.slider_dims}, you have provided: {indices.keys()}"
            )

        indexer = dict()
        # get only slider dims which are not also spatial dims (example: p dim for positional data)
        # since that is dealt with separately
        slider_dims = set(self.slider_dims) - set(self.spatial_dims)
        # go through each slider dim and accumulate slice objects
        for dim in slider_dims:
            # index for this dim in reference space
            index_ref = indices[dim]

            # get window func and size in reference units
            wf, ws = self.window_funcs[dim]

            # if a window function exists for this dim, and it's specified in the window order
            if (wf is not None) and (ws is not None) and (dim in self.window_order):
                # half window in reference units
                hw = ws / 2

                # start in reference units
                start_ref = index_ref - hw
                # stop in ref units
                stop_ref = index_ref + hw

                # map start and stop ref to array indices
                start = self.index_mappings[dim](start_ref)
                stop = self.index_mappings[dim](stop_ref)

                # clamp within array bounds
                start = max(min(self.shape[dim] - 1, start), 0)
                stop = max(min(self.shape[dim] - 1, stop), 0)
                indexer[dim] = slice(start, stop, 1)
            else:
                # no window func for this dim, direct indexing
                # index mapped to array index
                index = self.index_mappings[dim](index_ref)

                # clamp within the bounds
                start = max(min(self.shape[dim] - 1, index), 0)

                # stop index is just the start index + 1
                indexer[dim] = slice(start, start + 1, 1)

        return indexer

    def _apply_window_functions(self, indices) -> xr.DataArray:
        """slice with windows at given indices and apply window functions"""
        indexer = self._get_slider_dims_indexer(indices)

        # there is significant overhead with passing xarray objects to numpy for things like np.mean()
        # so convert to numpy, apply window functions, then convert back to xarray
        # creating an xarray object from a numpy array has very little overhead, ~10 microseconds
        array = self.data.isel(indexer).values

        # apply window funcs in the specified order
        for dim in self.window_order:
            if self.window_funcs[dim] is None:
                continue

            func, _ = self.window_funcs[dim]

            array = func(array, axis=self.dims.index(dim), keepdims=True)

        return xr.DataArray(array, dims=self.dims)

    def get(self, indices: dict[Hashable, Any]):
        raise NotImplementedError


def block_reentrance(setter):
    # decorator to block re-entrant indices setter
    def set_indices_wrapper(self: NDGraphic, new_indices):
        """
        wraps NDGraphic.indices

        self: NDGraphic instance

        new_indices: new indices to set
        """
        # set_value is already in the middle of an execution, block re-entrance
        if self._block_indices:
            return
        try:
            # block re-execution of set_value until it has *fully* finished executing
            self._block_indices = True
            setter(self, new_indices)
        except Exception as exc:
            # raise original exception
            raise exc  # set_value has raised. The line above and the lines 2+ steps below are probably more relevant!
        finally:
            # set_value has finished executing, now allow future executions
            self._block_indices = False

    return set_indices_wrapper


class NDGraphic:
    def __init__(self, name: str | None):
        self._name = name
        self._block_indices = False

    @property
    def name(self) -> str | None:
        return self._name

    @property
    def processor(self) -> NDProcessor:
        raise NotImplementedError

    @property
    def graphic(self) -> Graphic:
        raise NotImplementedError

    @property
    def indices(self) -> tuple[Any]:
        raise NotImplementedError

    @indices.setter
    def indices(self, new: tuple):
        raise NotImplementedError


@contextmanager
def block_indices(ndgraphic: NDGraphic):
    """
    Context manager for pausing Graphic events.

    Optionally pass in only specific event handlers which are blocked. Other events for the graphic will not be blocked.

    Examples
    --------

    .. code-block::

        # pass in any number of graphics
        with fpl.pause_events(graphic1, graphic2, graphic3):
            # enter context manager
            # all events are blocked from graphic1, graphic2, graphic3

        # context manager exited, event states restored.

    """
    ndgraphic._block_indices = True

    try:
        yield
    except Exception as e:
        raise e from None  # indices setter has raised, the line above and the lines below are probably more relevant!
    finally:
        ndgraphic._block_indices = False
