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
    return index


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

        self._index_mappings = tuple(self._validate_index_mappings(index_mappings))

        self.window_funcs = window_funcs
        self.window_order = window_funcs_order

    @property
    def data(self) -> xr.DataArray:
        return self._data

    @data.setter
    def data(self, data: ArrayProtocol):
        self._data = self._validate_data(data, self.dims)

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
        for dim in tuple(sdims):
            if dim not in self.dims:
                raise KeyError

        self._spatial_dims = tuple(sdims)

    def _validate_data(self, data: ArrayProtocol, dims):
        if not isinstance(data, ArrayProtocol):
            raise TypeError("`data` must implement the ArrayProtocol")

        return xr.DataArray(data, dims=dims)

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
    def slider_dims(self):
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
            dict[Hashable, tuple[WindowFuncCallable | None, int | float | None]] | None
        ),
    ):
        if window_funcs is None:
            self._window_funcs = {d: None for d in self.data.dims}
            return

        for k in window_funcs.keys():
            if k not in self.dims:
                raise KeyError
            if k in self.spatial_dims:
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

            if not isinstance(size, Real):
                raise TypeError
            elif size < 0:
                raise ValueError

        self._window_funcs = window_funcs

    @property
    def window_order(self) -> tuple[Hashable, ...] | None:
        """get or set dimension order in which window functions are applied"""
        return self._window_order

    @window_order.setter
    def window_order(self, order: tuple[Hashable] | None):
        for d in order:
            if d not in self.dims:
                raise KeyError
            if d in self.spatial_dims:
                raise KeyError

        self._window_order = tuple(order)

    @property
    def spatial_func(self) -> Callable[[ArrayProtocol], ArrayProtocol] | None:
        pass

    @property
    def index_mappings(self) -> tuple[Callable[[Any], int]]:
        return self._index_mappings

    @index_mappings.setter
    def index_mappings(self, maps: dict[Hashable, Callable[[Any], int] | ArrayLike]):
        for d in maps.keys():
            if d not in self.dims:
                raise KeyError
            if d in self.spatial_dims:
                raise KeyError
            if isinstance(maps[d], ArrayProtocol):
                # create a searchsorted mapping function automatically
                maps[d] = maps[d].searchsorted
            elif maps[d] is None:
                # assign identity mapping
                maps[d] = identity

        self._index_mappings = maps

    def get(self, indices: dict[Hashable, Any]):
        pass


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
