import inspect
from typing import Literal, Callable
from warnings import warn

import numpy as np
from numpy.typing import ArrayLike

from ...utils import subsample_array, ArrayProtocol, ARRAY_LIKE_ATTRS


# must take arguments: array-like, `axis`: int, `keepdims`: bool
WindowFuncCallable = Callable[[ArrayLike, int, bool], ArrayLike]


class NDImageProcessor:
    def __init__(
        self,
        data: ArrayLike | None,
        n_display_dims: Literal[2, 3] = 2,
        rgb: bool = False,
        window_funcs: tuple[WindowFuncCallable | None, ...] | WindowFuncCallable = None,
        window_sizes: tuple[int | None, ...] | int = None,
        window_order: tuple[int, ...] = None,
        spatial_func: Callable[[ArrayLike], ArrayLike] = None,
        compute_histogram: bool = True,
    ):
        """
        An ND image that supports computing window functions, and functions over spatial dimensions.

        Parameters
        ----------
        data: ArrayLike
            array-like data, must have 2 or more dimensions

        n_display_dims: int, 2 or 3, default 2
            number of display dimensions

        rgb: bool, default False
            whether the image data is RGB(A) or not

        window_funcs: tuple[WindowFuncCallable | None, ...] | WindowFuncCallable, optional
            A function or a ``tuple`` of functions that are applied to a rolling window of the data.

            You can provide unique window functions for each dimension. If you want to apply a window function
            only to a subset of the dimensions, put ``None`` to indicate no window function for a given dimension.

            A "window function" must take ``axis`` argument, which is an ``int`` that specifies the axis along which
            the window function is applied. It must also take a ``keepdims`` argument which is a ``bool``. The window
            function **must** return an array that has the same number of dimensions as the original ``data`` array,
            therefore the size of the dimension along which the window was applied will reduce to ``1``.

            The output array-like type from a window function **must** support a ``.squeeze()`` method, but the
            function itself should NOT squeeze the output array.

        window_sizes: tuple[int | None, ...], optional
            ``tuple`` of ``int`` that specifies the window size for each dimension.

        window_order: tuple[int, ...] | None, optional
            order in which to apply the window functions, by default just applies it from the left-most dim to the
            right-most slider dim.

        spatial_func: Callable[[ArrayLike], ArrayLike] | None, optional
            A function that is applied on the _spatial_ dimensions of the data array, i.e. the last 2 or 3 dimensions.
            This function is applied after the window functions (if present).

        compute_histogram: bool, default True
            Compute a histogram of the data, auto re-computes if window function propties or spatial_func changes.
            Disable if slow.

        """
        # set as False until data, window funcs stuff and spatial func is all set
        self._compute_histogram = False

        self.data = data
        self.n_display_dims = n_display_dims
        self.rgb = rgb

        self.window_funcs = window_funcs
        self.window_sizes = window_sizes
        self.window_order = window_order

        self._spatial_func = spatial_func

        self._compute_histogram = compute_histogram
        self._recompute_histogram()

    @property
    def data(self) -> ArrayLike | None:
        """get or set the data array"""
        return self._data

    @data.setter
    def data(self, data: ArrayLike):
        # check that all array-like attributes are present
        if data is None:
            self._data = None
            return

        if not isinstance(data, ArrayProtocol):
            raise TypeError(
                f"`data` arrays must have all of the following attributes to be sufficiently array-like:\n"
                f"{ARRAY_LIKE_ATTRS}, or they must be `None`"
            )

        if data.ndim < 2:
            raise IndexError(
                f"Image data must have a minimum of 2 dimensions, you have passed an array of shape: {data.shape}"
            )

        self._data = data
        self._recompute_histogram()

    @property
    def ndim(self) -> int:
        if self.data is None:
            return 0

        return self.data.ndim

    @property
    def shape(self) -> tuple[int, ...]:
        if self._data is None:
            return tuple()

        return self.data.shape

    @property
    def rgb(self) -> bool:
        """whether or not the data is rgb(a)"""
        return self._rgb

    @rgb.setter
    def rgb(self, rgb: bool):
        if not isinstance(rgb, bool):
            raise TypeError

        if rgb and self.ndim < 3:
            raise IndexError(
                f"require 3 or more dims for RGB, you have: {self.ndim} dims"
            )

        self._rgb = rgb

    @property
    def n_slider_dims(self) -> int:
        """number of slider dimensions"""
        if self._data is None:
            return 0

        return self.ndim - self.n_display_dims - int(self.rgb)

    @property
    def slider_dims(self) -> tuple[int, ...] | None:
        """tuple indicating the slider dimension indices"""
        if self.n_slider_dims == 0:
            return None

        return tuple(range(self.n_slider_dims))

    @property
    def slider_dims_shape(self) -> tuple[int, ...] | None:
        if self.n_slider_dims == 0:
            return None

        return tuple(self.shape[i] for i in self.slider_dims)

    @property
    def n_display_dims(self) -> Literal[2, 3]:
        """get or set the number of display dimensions, `2` for 2D image and `3` for volume images"""
        return self._n_display_dims

    # TODO: make n_display_dims settable, requires thinking about inserting and poping indices in ImageWidget
    @n_display_dims.setter
    def n_display_dims(self, n: Literal[2, 3]):
        if not (n == 2 or n == 3):
            raise ValueError(
                f"`n_display_dims` must be an <int> with a value of 2 or 3, you have passed: {n}"
            )
        self._n_display_dims = n
        self._recompute_histogram()

    @property
    def max_n_display_dims(self) -> int:
        """maximum number of possible display dims"""
        # min 2, max 3, accounts for if data is None and ndim is 0
        return max(2, min(3, self.ndim - int(self.rgb)))

    @property
    def display_dims(self) -> tuple[int, int] | tuple[int, int, int]:
        """tuple indicating the display dimension indices"""
        return tuple(range(self.data.ndim))[self.n_slider_dims :]

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
            self._window_funcs = None
            return

        if callable(window_funcs):
            window_funcs = (window_funcs,)

        # if all are None
        if all([f is None for f in window_funcs]):
            self._window_funcs = None
            return

        self._validate_window_func(window_funcs)

        self._window_funcs = tuple(window_funcs)
        self._recompute_histogram()

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
            self._window_sizes = None
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

        if not (len(window_sizes) == self.n_slider_dims or self.n_slider_dims == 0):
            raise IndexError(
                f"number of `window_sizes` must be the same as the number of slider dims, "
                f"i.e. `data.ndim` - n_display_dims, your data array has {self.ndim} dimensions "
                f"and you passed {len(window_sizes)} `window_sizes`: {window_sizes}"
            )

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
        self._recompute_histogram()

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
        self._recompute_histogram()

    @property
    def spatial_func(self) -> Callable[[ArrayLike], ArrayLike] | None:
        """get or set a spatial_func function, see docstring for details"""
        return self._spatial_func

    @spatial_func.setter
    def spatial_func(self, func: Callable[[ArrayLike], ArrayLike] | None):
        if not (callable(func) or func is not None):
            raise TypeError(
                f"`spatial_func` must be a callable or `None`, you have passed: {func}"
            )

        self._spatial_func = func
        self._recompute_histogram()

    @property
    def compute_histogram(self) -> bool:
        return self._compute_histogram

    @compute_histogram.setter
    def compute_histogram(self, compute: bool):
        if compute:
            if self._compute_histogram is False:
                # compute a histogram
                self._recompute_histogram()
                self._compute_histogram = True
        else:
            self._compute_histogram = False
            self._histogram = None

    @property
    def histogram(self) -> tuple[np.ndarray, np.ndarray] | None:
        """
        an estimate of the histogram of the data, (histogram_values, bin_edges).

        returns `None` if `compute_histogram` is `False`
        """
        return self._histogram

    def _apply_window_function(self, indices: tuple[int, ...]) -> ArrayLike:
        """applies the window functions for each dimension specified"""
        # window size for each dim
        winds = self._window_sizes
        # window function for each dim
        funcs = self._window_funcs

        if winds is None or funcs is None:
            # no window funcs or window sizes, just slice data and return
            # clamp to max bounds
            indexer = list()
            for dim, i in enumerate(indices):
                i = min(self.shape[dim] - 1, i)
                indexer.append(i)

            return self.data[tuple(indexer)]

        # order in which window funcs are applied
        order = self._window_order

        if order is not None:
            # remove any entries in `window_order` where the specified dim
            # has a window function or window size specified as `None`
            # example:
            # window_sizes = (3, 2)
            # window_funcs = (np.mean, None)
            # order = (0, 1)
            # `1` is removed from the order since that window_func is `None`
            order = tuple(
                d for d in order if winds[d] is not None and funcs[d] is not None
            )
        else:
            # sequential order
            order = list()
            for d in range(self.n_slider_dims):
                if winds[d] is not None and funcs[d] is not None:
                    order.append(d)

        # the final indexer which will be used on the data array
        indexer = list()

        for dim_index, (i, w, f) in enumerate(zip(indices, winds, funcs)):
            # clamp i within the max bounds
            i = min(self.shape[dim_index] - 1, i)

            if (w is not None) and (f is not None):
                # specify slice window if both window size and function for this dim are not None
                hw = int((w - 1) / 2)  # half window

                # start index cannot be less than 0
                start = max(0, i - hw)

                # stop index cannot exceed the bounds of this dimension
                stop = min(self.shape[dim_index] - 1, i + hw)

                s = slice(start, stop, 1)
            else:
                s = slice(i, i + 1, 1)

            indexer.append(s)

        # apply indexer to slice data with the specified windows
        data_sliced = self.data[tuple(indexer)]

        # finally apply the window functions in the specified order
        for dim in order:
            f = funcs[dim]

            data_sliced = f(data_sliced, axis=dim, keepdims=True)

        return data_sliced

    def get(self, indices: tuple[int, ...]) -> ArrayLike | None:
        """
        Get the data at the given index, process data through the window functions.

        Note that we do not use __getitem__ here since the index is a tuple specifying a single integer
        index for each dimension. Slices are not allowed, therefore __getitem__ is not suitable here.

        Parameters
        ----------
        indices: tuple[int, ...]
            Get the processed data at this index. Must provide a value for each dimension.
            Example: get((100, 5))

        """
        if self.data is None:
            return None

        if self.n_slider_dims != 0:
            if len(indices) != self.n_slider_dims:
                raise IndexError(
                    f"Must specify index for every slider dim, you have specified an index: {indices}\n"
                    f"But there are: {self.n_slider_dims} slider dims."
                )
            # get output after processing through all window funcs
            # squeeze to remove all dims of size 1
            window_output = self._apply_window_function(indices).squeeze()
        else:
            # data is a static image or volume
            window_output = self.data

        # apply spatial_func
        if self.spatial_func is not None:
            final_output = self.spatial_func(window_output)
            if final_output.ndim != (self.n_display_dims + int(self.rgb)):
                raise IndexError(
                    f"Final output after of the `spatial_func` must match the number of display dims."
                    f"Output after `spatial_func` returned an array with {final_output.ndim} dims and "
                    f"of shape: {final_output.shape}, expected {self.n_display_dims} dims"
                )
        else:
            # check that output ndim after window functions matches display dims
            final_output = window_output
            if final_output.ndim != (self.n_display_dims + int(self.rgb)):
                raise IndexError(
                    f"Final output after of the `window_funcs` must match the number of display dims."
                    f"Output after `window_funcs` returned an array with {window_output.ndim} dims and "
                    f"of shape: {window_output.shape}{' with rgb(a) channels' if self.rgb else ''}, "
                    f"expected {self.n_display_dims} dims"
                )

        return final_output

    def _recompute_histogram(self):
        """

        Returns
        -------
        (histogram_values, bin_edges)

        """
        if not self._compute_histogram or self.data is None:
            self._histogram = None
            return

        if self.spatial_func is not None:
            # don't subsample spatial dims if a spatial function is used
            # spatial functions often operate on the spatial dims, ex: a gaussian kernel
            # so their results require the full spatial resolution, the histogram of a
            # spatially subsampled image will be very different
            ignore_dims = self.display_dims
        else:
            ignore_dims = None

        sub = subsample_array(self.data, ignore_dims=ignore_dims)
        sub_real = sub[~(np.isnan(sub) | np.isinf(sub))]

        self._histogram = np.histogram(sub_real, bins=100)
