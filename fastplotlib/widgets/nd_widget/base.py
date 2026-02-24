from contextlib import contextmanager
import inspect
from typing import Literal, Callable, Any
from warnings import warn

import numpy as np
from numpy.typing import ArrayLike

from ...utils import subsample_array, ArrayProtocol
from ...graphics import Graphic

# must take arguments: array-like, `axis`: int, `keepdims`: bool
WindowFuncCallable = Callable[[ArrayLike, int, bool], ArrayLike]


def identity(index: int) -> int:
    return index


class NDProcessor:
    def __init__(
        self,
        data,
        n_display_dims: Literal[2, 3] = 2,
        index_mappings: tuple[Callable[[Any], int] | None, ...] | None = None,
        window_funcs: tuple[WindowFuncCallable | None] | None = None,
        window_sizes: tuple[int | None] | None = None,
        window_order: tuple[int, ...] = None,
        spatial_func: Callable[[ArrayProtocol], ArrayProtocol] | None = None,
    ):
        self._data = self._validate_data(data)
        self._index_mappings = tuple(self._validate_index_mappings(index_mappings))

        self.window_funcs = window_funcs
        self.window_sizes = window_sizes
        self.window_order = window_order

    @property
    def data(self) -> ArrayProtocol:
        return self._data

    @data.setter
    def data(self, data: ArrayProtocol):
        self._data = self._validate_data(data)

    @property
    def shape(self) -> tuple[int, ...]:
        return self.data.shape

    @property
    def ndim(self) -> int:
        return len(self.shape)

    def _validate_data(self, data: ArrayProtocol):
        if not isinstance(data, ArrayProtocol):
            raise TypeError("`data` must implement the ArrayProtocol")

        return data

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
        raise NotImplementedError

    @property
    def n_slider_dims(self):
        raise NotImplementedError

    @property
    def window_funcs(
        self,
    ) -> tuple[WindowFuncCallable | None, ...] | None:
        """get or set window functions, see docstring for details"""
        return self._window_funcs

    @window_funcs.setter
    def window_funcs(
        self,
        window_funcs: tuple[WindowFuncCallable | None, ...] | WindowFuncCallable | None,
    ):
        if window_funcs is None:
            self._window_funcs = tuple([None] * self.n_slider_dims)
            return

        if callable(window_funcs):
            window_funcs = (window_funcs,)

        # if all are None
        # if all([f is None for f in window_funcs]):
        #     self._window_funcs = tuple(window_funcs)
        #     return

        self._validate_window_func(window_funcs)

        self._window_funcs = tuple(window_funcs)
        # self._recompute_histogram()

    def _validate_window_func(self, funcs):
        if isinstance(funcs, (tuple, list)):
            for f in funcs:
                if f is None:
                    pass
                elif callable(f):
                    sig = inspect.signature(f)

                    if "axis" not in sig.parameters or "keepdims" not in sig.parameters:
                        raise TypeError(
                            f"Each window function must take an `axis` and `keepdims` argument, "
                            f"you passed: {f} with the following function signature: {sig}"
                        )
                else:
                    raise TypeError(
                        f"`window_funcs` must be of type: tuple[Callable | None, ...], you have passed: {funcs}"
                    )

        if not (len(funcs) == self.n_slider_dims or self.n_slider_dims == 0):
            raise IndexError(
                f"number of `window_funcs` must be the same as the number of slider dims: {self.n_slider_dims}, "
                f"and you passed {len(funcs)} `window_funcs`: {funcs}"
            )

    @property
    def window_sizes(self) -> tuple[int | None, ...] | None:
        """get or set window sizes used for the corresponding window functions, see docstring for details"""
        return self._window_sizes

    @window_sizes.setter
    def window_sizes(self, window_sizes: tuple[int | None, ...] | int | None):
        if window_sizes is None:
            self._window_sizes = tuple([None] * self.n_slider_dims)
            return

        if isinstance(window_sizes, int):
            window_sizes = (window_sizes,)

        # if all are None
        if all([w is None for w in window_sizes]):
            self._window_sizes = None
            return

        if not all([isinstance(w, (int)) or w is None for w in window_sizes]):
            raise TypeError(
                f"`window_sizes` must be of type: tuple[int | None, ...] | int | None, you have passed: {window_sizes}"
            )

        # if not (len(window_sizes) == self.n_slider_dims or self.n_slider_dims == 0):
        #     raise IndexError(
        #         f"number of `window_sizes` must be the same as the number of slider dims, "
        #         f"i.e. `data.ndim` - n_display_dims, your data array has {self.ndim} dimensions "
        #         f"and you passed {len(window_sizes)} `window_sizes`: {window_sizes}"
        #     )

        # make all window sizes are valid numbers
        _window_sizes = list()
        for i, w in enumerate(window_sizes):
            if w is None:
                _window_sizes.append(None)
                continue

            if w < 0:
                raise ValueError(
                    f"negative window size passed, all `window_sizes` must be positive "
                    f"integers or `None`, you passed: {_window_sizes}"
                )

            if w == 0 or w == 1:
                # this is not a real window, set as None
                w = None

            elif w % 2 == 0:
                # odd window sizes makes most sense
                warn(
                    f"provided even window size: {w} in dim: {i}, adding `1` to make it odd"
                )
                w += 1

            _window_sizes.append(w)

        self._window_sizes = tuple(_window_sizes)

    @property
    def window_order(self) -> tuple[int, ...] | None:
        """get or set dimension order in which window functions are applied"""
        return self._window_order

    @window_order.setter
    def window_order(self, order: tuple[int] | None):
        if order is None:
            self._window_order = None
            return

        if order is not None:
            if not all([d <= self.n_slider_dims for d in order]):
                raise IndexError(
                    f"all `window_order` entries must be <= n_slider_dims\n"
                    f"`n_slider_dims` is: {self.n_slider_dims}, you have passed `window_order`: {order}"
                )

            if not all([d >= 0 for d in order]):
                raise IndexError(
                    f"all `window_order` entires must be >= 0, you have passed: {order}"
                )

        self._window_order = tuple(order)

    @property
    def spatial_func(self) -> Callable[[ArrayProtocol], ArrayProtocol] | None:
        pass

    # @property
    # def slider_dims(self) -> tuple[int, ...] | None:
    #     pass

    @property
    def index_mappings(self) -> tuple[Callable[[Any], int]]:
        return self._index_mappings

    @index_mappings.setter
    def index_mappings(self, maps: tuple[Callable[[Any], int] | None] | None):
        self._index_mappings = tuple(self._validate_index_mappings(maps))

    def _validate_index_mappings(self, maps):
        if maps is None:
            return tuple([identity] * self.n_slider_dims)

        if len(maps) != self.n_slider_dims:
            raise IndexError

        _maps = list()
        for m in maps:
            if m is None:
                _maps.append(identity)
            elif callable(m):
                _maps.append(identity)
            else:
                raise TypeError

        return tuple(maps)

    def __getitem__(self, item: tuple[Any, ...]) -> ArrayProtocol:
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
