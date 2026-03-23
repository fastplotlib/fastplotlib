from collections.abc import Callable, Hashable, Sequence
from contextlib import contextmanager
import inspect
from numbers import Real
from pprint import pformat
import textwrap
from typing import Literal, Any, Type
from warnings import warn

import xarray as xr
import numpy as np
from numpy.typing import ArrayLike

from ...layouts import Subplot
from ...utils import subsample_array, ArrayProtocol
from ...graphics import Graphic
from ._repr_formatter import ndp_fmt_text, ndg_fmt_text, ndp_fmt_html, ndg_fmt_html
from ._index import ReferenceIndex

# must take arguments: array-like, `axis`: int, `keepdims`: bool
WindowFuncCallable = Callable[[ArrayLike, int, bool], ArrayLike]


def identity(index: int) -> int:
    return round(index)


class NDProcessor:
    def __init__(
        self,
        data: Any,
        dims: Sequence[Hashable],
        spatial_dims: Sequence[Hashable] | None,
        slider_dim_transforms: dict[Hashable, Callable[[Any], int] | ArrayLike] = None,
        window_funcs: dict[
            Hashable, tuple[WindowFuncCallable | None, int | float | None]
        ] = None,
        window_order: tuple[Hashable, ...] = None,
        spatial_func: Callable[[ArrayProtocol], ArrayProtocol] | None = None,
    ):
        """
        Base class for managing n-dimensional data and producing array slices.

        By default, wraps input data into an ``xarray.DataArray`` and provides an interface
        for indexing slider dimensions, applying window functions, spatial functions, and mapping
        reference-space values to local array indices. Subclasses must implement
        :meth:`get`, which is called whenever the :class:`ReferenceIndex` updates.

        Subclasses can implement any type of data representation, they do not necessarily need to be compatible with
        (they dot not have to be xarray compatible). However their ``get()`` method must still return a data slice that
        corresponds to the graphical representation they map to.

        Every dimension that is *not* listed in ``spatial_dims`` becomes a slider
        dimension. Each slider dim must have a ``ReferenceRange`` defined in the
        ``ReferenceIndex`` of the parent ``NDWidget``. The widget uses this to direct
        a change in the ``ReferenceIndex`` and update the graphics.

        Parameters
        ----------
        data: Any
            data object that is managed, usually uses the ArrayProtocol. Custom subclasses can manage any kind of data
            object but the corresponding :meth:`get` must return an array-like that maps to a graphical representation.

        dims: Sequence[str]
            names for each dimension in ``data``. Dimensions not listed in
            ``spatial_dims`` are treated as slider dimensions and **must** appear as
            keys in the parent ``NDWidget``'s ``ref_ranges``
                Examples::
                 ``("time", "depth", "row", "col")``
                 ``("channels", "time", "xy")``
                 ``("keypoints", "time", "xyz")``

            A custom subclass's ``data`` object doesn't necessarily need to have these dims, but the ``get()`` method
            must operate as if these dimensions exist and return an array that matches the spatial dimensions.

        spatial_dims: Sequence[str]
            Subset of ``dims`` that are spatial (rendered) dimensions **in order**. All remaining dims are treated as
            slider dims. See subclass for specific info.

        slider_dim_transforms: dict mapping dim_name -> Callable, an ArrayLike, or None
            Per-slider-dim mapping from reference-space values to local array indices.

            You may also provide an array of reference values for the slider dims, ``searchsorted`` is then used
            as the transform (ex: a timestamps array).

            If ``None`` and identity mapping is used, i.e. rounds the current reference index value to the nearest
            integer for array indexing.

            If a transform is not provided for a dim then the identity mapping is used.

        window_funcs: dict[
            Hashable, tuple[WindowFuncCallable | None, int | float | None]
        ]
            Per-slider-dim window functions applied around the current slider position. Ex: {"time": (np.mean, 2.5)}.
            Each value is a ``(func, window_size)`` pair where:

            * *func* must accept ``axis: int`` and ``keepdims: bool`` kwargs
              (ex: ``np.mean``, ``np.max``). The window function **must** return an array that has the same dimensions
              as specified in the NDProcessor, therefore the size of any dim along which a window_func was applied
              should reduce to ``1``. These dims must not be removed by the window_func.

            * *window_size* is in reference-space units (ex: 2.5 seconds).


        window_order: tuple[Hashable, ...]
            Order in which window functions are applied across dims. Only dims listed
            here have their window function applied. window_funcs are ignored for any
            dims not specified in ``window_order``

        spatial_func:
            A function applied to the spatial slice *after* window_funcs right before rendering.

        """
        self._dims = tuple(dims)
        self._data = self._validate_data(data)
        self.spatial_dims = spatial_dims

        self.slider_dim_transforms = slider_dim_transforms

        self.window_funcs = window_funcs
        self.window_order = window_order
        self.spatial_func = spatial_func

    @property
    def data(self) -> xr.DataArray:
        """
        get or set managed data. If setting with new data, the new data is interpreted
        to have the same dims (i.e. same dim names and ordering of dims).
        """
        return self._data

    @data.setter
    def data(self, data: ArrayProtocol):
        self._data = self._validate_data(data)

    def _validate_data(self, data: ArrayProtocol):
        # does some basic validation
        if data is None:
            # we allow data to be None, in this case no ndgraphic is rendered
            # useful when we want to initialize an NDWidget with no traces for example
            # and populate it as components/channels are selected
            return None

        if not isinstance(data, ArrayProtocol):
            # This is required for xarray compatibility and general array-like requirements
            raise TypeError("`data` must implement the ArrayProtocol")

        if data.ndim != len(self.dims):
            raise IndexError("must specify a dim for every dimension in the data array")

        # data can be set, but the dims must still match/have the same meaning
        return xr.DataArray(data, dims=self.dims)

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
        # these are read-only and cannot be set after it's created
        # the user should create a new NDGraphic if they need different dims
        # I can't think of a usecase where we'd want to change the dims, and
        # I think that would be complicated and probably and anti-pattern
        return self._dims

    @property
    def spatial_dims(self) -> tuple[Hashable, ...]:
        """Spatial dims, **in order**"""
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
        """Slider dim names, ``set(dims) - set(spatial_dims)"""
        return set(self.dims) - set(self.spatial_dims)

    @property
    def n_slider_dims(self):
        """number of slider dims, i.e. len(slider_dims)"""
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
    def spatial_func(self) -> Callable[[xr.DataArray], xr.DataArray] | None:
        """get or set the spatial function which is applied on the data slice after the window functions"""
        return self._spatial_func

    @spatial_func.setter
    def spatial_func(
        self, func: Callable[[xr.DataArray], xr.DataArray]
    ) -> Callable | None:
        if not callable(func) and func is not None:
            raise TypeError

        self._spatial_func = func

    @property
    def slider_dim_transforms(self) -> dict[Hashable, Callable[[Any], int]]:
        """get or set the slider_dim_transforms, see docstring for details"""
        return self._index_mappings

    @slider_dim_transforms.setter
    def slider_dim_transforms(
        self, maps: dict[Hashable, Callable[[Any], int] | ArrayLike | None] | None
    ):
        if maps is None:
            self._index_mappings = {d: identity for d in self.dims}
            return

        for d in maps.keys():
            if d not in self.dims:
                raise KeyError(
                    f"`index_mapping` provided for non-existent dimension: {d}, existing dims are: {self.dims}"
                )

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
        # wraps slider_dim_transforms, clamps between 0 and the array size in this dim

        # ref-space -> local-array-index transform
        index = self.slider_dim_transforms[dim](ref_index)

        # clamp between 0 and array size in this dim
        return max(min(index, self.shape[dim] - 1), 0)

    def _get_slider_dims_indexer(self, indices: dict[Hashable, Any]) -> dict[Hashable, slice]:
        """
        Creates an xarray-compatible indexer dict mapping each slider_dim -> slice object.

        - If a window_func is defined for a dim and the dim appears in ``window_order``,
        the slice is defined as:
            start: index - half_window
            stop: index + half_window
            step: 1

            It then applies the slider_dim_transform to the start and stop to map these values from reference-space to
            the local array index, and then finally produces the slice object in local array indices.

            ex: if we have indices = {"time": 50.0}, a window size of 5.0s and the ``slider_dim_transform``
            for time is based on a sampling rate of 10Hz, the window in ref units is [45.0, 55.0], and the final
            slice object would be ``slice(450, 550, 1)``.

        - If no window func is specified, the final slice just corresponds to that index as an int array-index.

        This exists separate from ``_apply_window_functions()`` because it is useful for debugging purposes.

        Parameters
        ----------
        indices : dict[Hashable, Any], {dim: ref_value}
            Reference-space values for each slider dim. Must contain an entry
            for every slider dim; raises ``IndexError`` otherwise.
            ex: {"time": 46.397, "depth": 23.24}

        Returns
        -------
        dict[Hashable, slice]
            Indexer compatible for ``xr.DataArray.isel()``, with one ``slice`` per
            slider dim. These are array indices mapped from the reference space using
            the given ``slider_dim_transform``.

        Raises
        ------
        IndexError
            If ``indices`` are not provided for every ``slider_dim``
        """

        if set(indices.keys()) != set(self.slider_dims):
            raise IndexError(
                f"Must provide an index for all slider dims: {self.slider_dims}, you have provided: {indices.keys()}"
            )

        indexer = dict()

        # get only slider dims which are not also spatial dims (example: p dim for positional data)
        # since `p` dim windowing is dealt with separately for positional data
        slider_dims = set(self.slider_dims) - set(self.spatial_dims)
        # go through each slider dim and accumulate slice objects
        for dim in slider_dims:
            # index for this dim in reference space
            index_ref = indices[dim]

            if dim not in self.window_funcs.keys():
                wf, ws = None, None
            else:
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
                start = self.slider_dim_transforms[dim](start_ref)
                stop = self.slider_dim_transforms[dim](stop_ref)

                # clamp within array bounds
                start = max(min(self.shape[dim] - 1, start), 0)
                stop = max(min(self.shape[dim] - 1, stop), 0)
                indexer[dim] = slice(start, stop, 1)
            else:
                # no window func for this dim, direct indexing
                # index mapped to array index
                index = self.slider_dim_transforms[dim](index_ref)

                # clamp within the bounds
                start = max(min(self.shape[dim] - 1, index), 0)

                # stop index is just the start index + 1
                indexer[dim] = slice(start, start + 1, 1)

        return indexer

    def _apply_window_functions(self, indices: dict[Hashable, Any]) -> xr.DataArray:
        """
        Slice the data at the given indices and apply window functions in the order specified by
         ``window_order``.

        Parameters
        ----------
        indices : dict[Hashable, Any], {dim: ref_value}
            Reference-space values for each slider dim.
            ex: {"time": 46.397, "depth": 23.24}

        Returns
        -------
        xr.DataArray
            Data slice after windowed indexing and window function application,
            with the same dims as the original data. Dims of size ``1`` are not
            squeezed.

        """
        indexer = self._get_slider_dims_indexer(indices)

        # get the data slice w.r.t. the desired windows, and get the underlying numpy array
        # ``.values`` gives the numpy array
        # there is significant overhead with passing xarray objects to numpy for things like np.mean()
        # so convert to numpy, apply window functions, then convert back to xarray
        # creating an xarray object from a numpy array has very little overhead, ~10 microseconds
        array = self.data.isel(indexer).values

        # apply window funcs in the specified order
        for dim in self.window_order:
            if self.window_funcs[dim] is None:
                continue

            func, _ = self.window_funcs[dim]
            # ``keepdims=True`` is critical, any "collapsed" dims will be of size ``1``.
            # Ex: if `array` is of shape [10, 512, 512] and we applied the np.mean() window  func on the first dim
            # ``keepdims`` means the resultant shape is [1, 512, 512] and NOT [512, 512]
            # this is necessary for applying window functions on multiple dims separately and so that the
            # dims names correspond after all the window funcs are applied.
            array = func(array, axis=self.dims.index(dim), keepdims=True)

        return xr.DataArray(array, dims=self.dims)

    def get(self, indices: dict[Hashable, Any]):
        raise NotImplementedError

    # TODO: html and pretty text repr    #
    # def _repr_html_(self) -> str:
    #     return ndp_fmt_html(self)
    #
    # def _repr_mimebundle_(self, **kwargs) -> dict:
    #     return {
    #         "text/plain": self._repr_text_(),
    #         "text/html": self._repr_html_(),
    #     }

    def _repr_text_(self):
        if self.data is None:
            return (
                f"{self.__class__.__name__}\n"
                f"data is None, dims: {self.dims}"
            )
        tab = "\t"

        wf = {k: v for k, v in self.window_funcs.items() if v != (None, None)}

        r = (
            f"{self.__class__.__name__}\n"
            f"shape:\n\t{self.shape}\n"
            f"dims:\n\t{self.dims}\n"
            f"spatial_dims:\n\t{self.spatial_dims}\n"
            f"slider_dims:\n\t{self.slider_dims}\n"
            f"slider_dim_transforms:\n{textwrap.indent(pformat(self.slider_dim_transforms, width=120), prefix=tab)}\n"
        )

        if len(wf) > 0:
            r += (
                f"window_funcs:\n{textwrap.indent(pformat(wf, width=120), prefix=tab)}\n"
                f"window_order:\n\t{self.window_order}\n"
            )

        if self.spatial_func is not None:
            r += f"spatial_func:\n\t{self.spatial_func}\n"

        return r


class NDGraphic:
    def __init__(
        self,
        subplot: Subplot,
        name: str | None,
    ):
        self._subplot = subplot
        self._name = name
        self._graphic: Graphic | None = None

        # used to indicate that the NDGraphic should ignore any requests to update the indices
        # used by block_indices_ctx context manager, usecase is when the LinearSelector on timeseries
        # NDGraphic changes the selection, it shouldn't change the graphic that it is on top of! Would
        # also cause recursion
        # It is also used by the @block_reentrance decorator which is on the ``NDGraphic.indices`` property setter
        # this is also to block recursion
        self._block_indices = False

        # user settable bool to make the graphic unresponsive to change in the ReferenceIndex
        self._pause = False


    def _create_graphic(self):
        raise NotImplementedError

    @property
    def pause(self) -> bool:
        """if True, changes in the reference until it is set back to False"""
        return self._pause

    @pause.setter
    def pause(self, val: bool):
        self._pause = bool(val)

    @property
    def name(self) -> str | None:
        """name given to the NDGraphic"""
        return self._name

    @property
    def processor(self) -> NDProcessor:
        raise NotImplementedError

    @property
    def graphic(self) -> Graphic:
        raise NotImplementedError

    @property
    def indices(self) -> dict[Hashable, Any]:
        raise NotImplementedError

    @indices.setter
    def indices(self, new: dict[Hashable, Any]):
        raise NotImplementedError

    # aliases for easier access to processor properties
    @property
    def data(self) -> Any:
        """
        get or set managed data. If setting with new data, the new data is interpreted
        to have the same dims (i.e. same dim names and ordering of dims).
        """
        return self.processor.data

    @data.setter
    def data(self, data: Any):
        self.processor.data = data
        # create a new graphic when data has changed
        if self.graphic is not None:
            # it is already None if NDGraphic was initialized with no data
            self._subplot.delete_graphic(self.graphic)
            self._graphic = None

        self._create_graphic()

        # force a render
        self.indices = self.indices

    @property
    def shape(self) -> dict[Hashable, int]:
        """interpreted shape of the data"""
        return self.processor.shape

    @property
    def ndim(self) -> int:
        """number of dims"""
        return self.processor.ndim

    @property
    def dims(self) -> tuple[Hashable, ...]:
        """dim names"""
        return self.processor.dims

    @property
    def spatial_dims(self) -> tuple[str, ...]:
        # number of spatial dims for positional data is always 3
        # for image is 2 or 3, so it must be implemented in subclass
        raise NotImplementedError

    @property
    def slider_dims(self) -> set[Hashable]:
        """the slider dims"""
        return self.processor.slider_dims

    @property
    def slider_dim_transforms(self) -> dict[Hashable, Callable[[Any], int]]:
        return self.processor.slider_dim_transforms

    @slider_dim_transforms.setter
    def slider_dim_transforms(
        self, maps: dict[Hashable, Callable[[Any], int] | ArrayLike | None] | None
    ):
        """get or set the slider_dim_transforms, see docstring for details"""
        self.processor.slider_dim_transforms = maps
        # force a render
        self.indices = self.indices

    @property
    def window_funcs(
        self,
    ) -> dict[Hashable, tuple[WindowFuncCallable | None, int | float | None]]:
        """get or set window functions, see docstring for details"""
        return self.processor.window_funcs

    @window_funcs.setter
    def window_funcs(
        self,
        window_funcs: (
            dict[Hashable, tuple[WindowFuncCallable | None, int | float | None] | None]
            | None
        ),
    ):
        self.processor.window_funcs = window_funcs
        # force a render
        self.indices = self.indices

    @property
    def window_order(self) -> tuple[Hashable, ...]:
        """get or set dimension order in which window functions are applied"""
        return self.processor.window_order

    @window_order.setter
    def window_order(self, order: tuple[Hashable] | None):
        self.processor.window_order = order
        # force a render
        self.indices = self.indices

    @property
    def spatial_func(self) -> Callable[[xr.DataArray], xr.DataArray] | None:
        return self.processor.spatial_func

    @spatial_func.setter
    def spatial_func(
        self, func: Callable[[xr.DataArray], xr.DataArray]
    ) -> Callable | None:
        """get or set the spatial_func, see docstring for details"""
        self.processor.spatial_func = func
        # force a render
        self.indices = self.indices

    # def _repr_text_(self) -> str:
    #     return ndg_fmt_text(self)
    #
    # def _repr_html_(self) -> str:
    #     return ndg_fmt_html(self)
    #
    # def _repr_mimebundle_(self, **kwargs) -> dict:
    #     return {
    #         "text/plain": self._repr_text_(),
    #         "text/html": self._repr_html_(),
    #     }

    def _repr_text_(self):
        return f"graphic: {self.graphic.__class__.__name__}\n" f"processor:\n{self.processor}"


@contextmanager
def block_indices_ctx(ndgraphic: NDGraphic):
    """
    Context manager for pausing an NDGraphic from updating indices
    """
    ndgraphic._block_indices = True

    try:
        yield
    except Exception as e:
        raise e from None  # indices setter has raised, the line above and the lines below are probably more relevant!
    finally:
        ndgraphic._block_indices = False


def block_reentrance(setter):
    # decorator to block re-entrance of indices setter
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
