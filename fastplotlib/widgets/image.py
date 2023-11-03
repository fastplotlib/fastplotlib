from typing import *
from warnings import warn

import numpy as np


from ..layouts import GridPlot
from ..graphics import ImageGraphic
from ..utils import calculate_gridshape
from .histogram_lut import HistogramLUT
from ..layouts._utils import CANVAS_OPTIONS_AVAILABLE


if CANVAS_OPTIONS_AVAILABLE["jupyter"]:
    from ..layouts._frame._ipywidget_toolbar import IpywidgetImageWidgetToolbar

if CANVAS_OPTIONS_AVAILABLE["qt"]:
    from ..layouts._frame._qt_toolbar import QToolbarImageWidget


DEFAULT_DIMS_ORDER = {
    2: "xy",
    3: "txy",
    4: "tzxy",
    5: "tzcxy",
}


def _is_arraylike(obj) -> bool:
    """
    Checks if the object is array-like.
    For now just checks if obj has `__getitem__()`
    """
    for attr in ["__getitem__", "shape", "ndim"]:
        if not hasattr(obj, attr):
            return False

    return True


class _WindowFunctions:
    """Stores window function and window size"""
    def __init__(self, func: callable, window_size: int):
        self._func = None
        self.func = func

        self._window_size = 0
        self.window_size = window_size

    @property
    def func(self) -> callable:
        """Get or set the function"""
        return self._func

    @func.setter
    def func(self, func: callable):
        self._func = func

    @property
    def window_size(self) -> int:
        """Get or set window size"""
        return self._window_size

    @window_size.setter
    def window_size(self, ws: int):
        if ws is None:
            self._window_size = None
            return

        if not isinstance(ws, int):
            raise TypeError("window size must be an int")

        if ws < 3:
            warn(
                f"Invalid 'window size' value for function: {self.func}, "
                f"setting 'window size' = None for this function. "
                f"Valid values are integers >= 3."
            )
            self.window_size = None
            return

        if ws % 2 == 0:
            ws += 1

        self._window_size = ws

    def __repr__(self):
        return f"func: {self.func}, window_size: {self.window_size}"


class ImageWidget:
    @property
    def gridplot(self) -> GridPlot:
        """
        ``GridPlot`` instance within the `ImageWidget`.
        """
        return self._gridplot

    @property
    def widget(self):
        """
        Output context, either an ipywidget or QWidget
        """
        return self.gridplot.widget

    @property
    def managed_graphics(self) -> List[ImageGraphic]:
        """List of ``ImageWidget`` managed graphics."""
        iw_managed = list()
        for subplot in self.gridplot:
            # empty subplots will not have any image widget data
            if len(subplot.graphics) > 0:
                iw_managed.append(subplot["image_widget_managed"])
        return iw_managed

    @property
    def cmap(self) -> List[str]:
        cmaps = list()
        for g in self.managed_graphics:
            cmaps.append(g.cmap.name)

        return cmaps

    @cmap.setter
    def cmap(self, names: Union[str, List[str]]):
        if isinstance(names, list):
            if not all([isinstance(n, str) for n in names]):
                raise TypeError(f"Must pass cmap name as a `str` of list of `str`, you have passed:\n{names}")

            if not len(names) == len(self.managed_graphics):
                raise IndexError(
                    f"If passing a list of cmap names, the length of the list must be the same as the number of "
                    f"image widget subplots. You have passed: {len(names)} cmap names and have "
                    f"{len(self.managed_graphics)} image widget subplots"
                )

            for name, g in zip(names, self.managed_graphics):
                g.cmap = name

        elif isinstance(names, str):
            for g in self.managed_graphics:
                g.cmap = names

    @property
    def data(self) -> List[np.ndarray]:
        """data currently displayed in the widget"""
        return self._data

    @property
    def ndim(self) -> int:
        """number of dimensions in the image data displayed in the widget"""
        return self._ndim

    @property
    def dims_order(self) -> List[str]:
        """dimension order of the data displayed in the widget"""
        return self._dims_order

    @property
    def sliders(self) -> Dict[str, Any]:
        """the ipywidget IntSlider or QSlider instances used by the widget for indexing the desired dimensions"""
        return self._image_widget_toolbar.sliders

    @property
    def slider_dims(self) -> List[str]:
        """the dimensions that the sliders index"""
        return self._slider_dims

    @property
    def current_index(self) -> Dict[str, int]:
        """
        Get or set the current index

        Returns
        -------
        index: Dict[str, int]
            | ``dict`` for indexing each dimension, provide a ``dict`` with indices for all dimensions used by sliders
            or only a subset of dimensions used by the sliders.
            | example: if you have sliders for dims "t" and "z", you can pass either ``{"t": 10}`` to index to position
            10 on dimension "t" or ``{"t": 5, "z": 20}`` to index to position 5 on dimension "t" and position 20 on
            dimension "z" simultaneously.

        """
        return self._current_index

    @current_index.setter
    def current_index(self, index: Dict[str, int]):
        if not set(index.keys()).issubset(set(self._current_index.keys())):
            raise KeyError(
                f"All dimension keys for setting `current_index` must be present in the widget sliders. "
                f"The dimensions currently used for sliders are: {list(self.current_index.keys())}"
            )

        for k, val in index.items():
            if not isinstance(val, int):
                raise TypeError("Indices for all dimensions must be int")
            if val < 0:
                raise IndexError("negative indexing is not supported for ImageWidget")
            if val > self._dims_max_bounds[k]:
                raise IndexError(
                    f"index {val} is out of bounds for dimension '{k}' "
                    f"which has a max bound of: {self._dims_max_bounds[k]}"
                )

        self._current_index.update(index)

        # can make a callback_block decorator later
        self.block_sliders = True
        for k in index.keys():
            self.sliders[k].value = index[k]
        self.block_sliders = False

        for i, (ig, data) in enumerate(zip(self.managed_graphics, self.data)):
            frame = self._process_indices(data, self._current_index)
            frame = self._process_frame_apply(frame, i)
            ig.data = frame

    def __init__(
        self,
        data: Union[np.ndarray, List[np.ndarray]],
        dims_order: Union[str, Dict[int, str]] = None,
        slider_dims: Union[str, int, List[Union[str, int]]] = None,
        window_funcs: Union[int, Dict[str, int]] = None,
        frame_apply: Union[callable, Dict[int, callable]] = None,
        grid_shape: Tuple[int, int] = None,
        names: List[str] = None,
        grid_plot_kwargs: dict = None,
        histogram_widget: bool = True,
        **kwargs,
    ):
        """
        A high level widget for displaying n-dimensional image data in conjunction with automatically generated
        sliders for navigating through 1-2 selected dimensions within image data.

        Can display a single n-dimensional image array or a grid of n-dimensional images.

        Default dimension orders:

        ======= ==========
        n_dims  dims order
        ======= ==========
        2       "xy"
        3       "txy"
        4       "tzxy"
        ======= ==========

        Parameters
        ----------
        data: Union[np.ndarray, List[np.ndarray]
            array-like or a list of array-like

        dims_order: Optional[Union[str, Dict[np.ndarray, str]]]
            | ``str`` or a dict mapping to indicate dimension order
            | a single ``str`` if ``data`` is a single array, or a list of arrays with the same dimension order
            | examples: ``"xyt"``, ``"tzxy"``
            | ``dict`` mapping of ``{array_index: axis_order}`` if specific arrays have a non-default axes order.
            | "array_index" is the position of the corresponding array in the data list.
            | examples: ``{array_index: "tzxy", another_array_index: "xytz"}``

        slider_dims: Optional[Union[str, int, List[Union[str, int]]]]
            | The dimensions for which to create a slider
            | can be a single ``str`` such as **"t"**, **"z"** or a numerical ``int`` that indexes the desired dimension
            | can also be a list of ``str`` or ``int`` if multiple sliders are desired for multiple dimensions
            | examples: ``"t"``, ``["t", "z"]``

        window_funcs: Dict[Union[int, str], int]
            | average one or more dimensions using a given window
            | if a slider exists for only one dimension this can be an ``int``.
            | if multiple sliders exist, then it must be a `dict`` mapping in the form of: ``{dimension: window_size}``
            | dimension/axes can be specified using ``str`` such as "t", "z" etc. or ``int`` that indexes the dimension
            | if window_size is not an odd number, adds 1
            | use ``None`` to disable averaging for a dimension, example: ``{"t": 5, "z": None}``

        frame_apply: Union[callable, Dict[int, callable]]
            | apply a function to slices of the array before displaying the frame
            | pass a single function or a dict of functions to apply to each array individually
            | examples: ``{array_index: to_grayscale}``, ``{0: to_grayscale, 2: threshold_img}``
            | "array_index" is the position of the corresponding array in the data list.
            | if `window_funcs` is used, then this function is applied after `window_funcs`
            | this function must be a callable that returns a 2D array
            | example use case: converting an RGB frame from video to a 2D grayscale frame

        grid_shape: Optional[Tuple[int, int]]
            manually provide the shape for a gridplot, otherwise a square gridplot is approximated.

        grid_plot_kwargs: dict, optional
            passed to `GridPlot`

        names: Optional[str]
            gives names to the subplots

        histogram_widget: bool, default False
            make histogram LUT widget for each subplot

        kwargs: Any
            passed to fastplotlib.graphics.Image

        """

        self._names = None

        if isinstance(data, list):
            # verify that it's a list of np.ndarray
            if all([_is_arraylike(d) for d in data]):
                if grid_shape is None:
                    grid_shape = calculate_gridshape(len(data))

                # verify that user-specified grid shape is large enough for the number of image arrays passed
                elif grid_shape[0] * grid_shape[1] < len(data):
                    grid_shape = calculate_gridshape(len(data))
                    warn(
                        f"Invalid `grid_shape` passed, setting grid shape to: {grid_shape}"
                    )

                _ndim = [d.ndim for d in data]

                # verify that all image arrays have same number of dimensions
                # sliders get messy otherwise
                if not len(set(_ndim)) == 1:
                    raise ValueError(
                        f"Number of dimensions of all data arrays must match, your ndims are: {_ndim}"
                    )

                self._data: List[np.ndarray] = data
                self._ndim = self.data[0].ndim  # all ndim must be same

                if names is not None:
                    if not all([isinstance(n, str) for n in names]):
                        raise TypeError(
                            "optional argument `names` must be a list of str"
                        )

                    if len(names) != len(self.data):
                        raise ValueError(
                            "number of `names` for subplots must be same as the number of data arrays"
                        )
                    self._names = names

            else:
                raise TypeError(
                    f"If passing a list to `data` all elements must be an "
                    f"array-like type representing an n-dimensional image. "
                    f"You have passed the following types:\n"
                    f"{[type(a) for a in data]}"
                )

        elif _is_arraylike(data):
            self._data = [data]
            self._ndim = self.data[0].ndim

            grid_shape = calculate_gridshape(len(self._data))
        else:
            raise TypeError(
                f"`data` must be an array-like type representing an n-dimensional image "
                f"or a list of array-like representing a grid of n-dimensional images. "
                f"You have passed the following type {type(data)}"
            )

        # default dims order if not passed
        # updated later if passed
        self._dims_order: List[str] = [DEFAULT_DIMS_ORDER[self.ndim]] * len(self.data)

        if dims_order is not None:
            if isinstance(dims_order, str):
                dims_order = dims_order.lower()
                if len(dims_order) != self.ndim:
                    raise ValueError(
                        f"number of dims '{len(dims_order)} passed to `dims_order` "
                        f"does not match ndim '{self.ndim}' of data"
                    )
                self._dims_order: List[str] = [dims_order] * len(self.data)
            elif isinstance(dims_order, dict):
                self._dims_order: List[str] = [DEFAULT_DIMS_ORDER[self.ndim]] * len(
                    self.data
                )

                # dict of {array_ix: dims_order_str}
                for data_ix in list(dims_order.keys()):
                    if not isinstance(data_ix, int):
                        raise TypeError("`dims_order` dict keys must be <int>")
                    if len(dims_order[data_ix]) != self.ndim:
                        raise ValueError(
                            f"number of dims '{len(dims_order)} passed to `dims_order` "
                            f"does not match ndim '{self.ndim}' of data"
                        )
                    _do = dims_order[data_ix].lower()
                    # make sure the same dims are present
                    if not set(_do) == set(DEFAULT_DIMS_ORDER[self.ndim]):
                        raise ValueError(
                            f"Invalid `dims_order` passed for one of your arrays, "
                            f"valid `dims_order` for given number of dimensions "
                            f"can only contain the following characters: "
                            f"{DEFAULT_DIMS_ORDER[self.ndim]}"
                        )
                    try:
                        self.dims_order[data_ix] = _do
                    except Exception:
                        raise IndexError(
                            f"index {data_ix} out of bounds for `dims_order`, the bounds are 0 - {len(self.data)}"
                        )
            else:
                raise TypeError(
                    f"`dims_order` must be a <str> or <Dict[int: str]>, you have passed a: <{type(dims_order)}>"
                )

        if not len(self.dims_order[0]) == self.ndim:
            raise ValueError(
                f"Number of dims specified by `dims_order`: {len(self.dims_order[0])} does not"
                f" match number of dimensions in the `data`: {self.ndim}"
            )

        ao = np.array([sorted(v) for v in self.dims_order])

        if not np.all(ao == ao[0]):
            raise ValueError(
                f"`dims_order` for all arrays must contain the same combination of dimensions, your `dims_order` are: "
                f"{self.dims_order}"
            )

        # if slider_dims not provided
        if slider_dims is None:
            # by default sliders are made for all dimensions except the last 2
            default_dim_names = {0: "t", 1: "z", 2: "c"}
            slider_dims = list()
            for dim in range(self.ndim - 2):
                if dim in default_dim_names.keys():
                    slider_dims.append(default_dim_names[dim])
                else:
                    slider_dims.append(f"{dim}")

        # slider for only one of the dimensions
        if isinstance(slider_dims, (int, str)):
            # if numerical dimension is specified
            if isinstance(slider_dims, int):
                ao = np.array([v for v in self.dims_order])
                if not np.all(ao == ao[0]):
                    raise ValueError(
                        f"`dims_order` for all arrays must be identical if passing in a <int> `slider_dims` argument. "
                        f"Pass in a <str> argument if the `dims_order` are different for each array."
                    )
                self._slider_dims: List[str] = [self.dims_order[0][slider_dims]]

            # if dimension specified by str
            elif isinstance(slider_dims, str):
                if slider_dims not in self.dims_order[0]:
                    raise ValueError(
                        f"if `slider_dims` is a <str>, it must be a character found in `dims_order`. "
                        f"Your `dims_order` characters are: {set(self.dims_order[0])}."
                    )
                self._slider_dims: List[str] = [slider_dims]

        # multiple sliders, one for each dimension
        elif isinstance(slider_dims, list):
            self._slider_dims: List[str] = list()

            # make sure window_funcs and frame_apply are dicts if multiple sliders are desired
            if (not isinstance(window_funcs, dict)) and (window_funcs is not None):
                raise TypeError(
                    f"`window_funcs` must be a <dict> if multiple `slider_dims` are provided. You must specify the "
                    f"window for each dimension."
                )
            if (not isinstance(frame_apply, dict)) and (frame_apply is not None):
                raise TypeError(
                    f"`frame_apply` must be a <dict> if multiple `slider_dims` are provided. You must specify a "
                    f"function for each dimension."
                )

            for sdm in slider_dims:
                if isinstance(sdm, int):
                    ao = np.array([v for v in self.dims_order])
                    if not np.all(ao == ao[0]):
                        raise ValueError(
                            f"`dims_order` for all arrays must be identical if passing in a <int> `slider_dims` argument. "
                            f"Pass in a <str> argument if the `dims_order` are different for each array."
                        )
                    # parse int to a str
                    self.slider_dims.append(self.dims_order[0][sdm])

                elif isinstance(sdm, str):
                    if sdm not in self.dims_order[0]:
                        raise ValueError(
                            f"if `slider_dims` is a <str>, it must be a character found in `dims_order`. "
                            f"Your `dims_order` characters are: {set(self.dims_order[0])}."
                        )
                    self.slider_dims.append(sdm)

                else:
                    raise TypeError(
                        "If passing a list for `slider_dims` each element must be either an <int> or <str>"
                    )

        else:
            raise TypeError(
                f"`slider_dims` must a <int>, <str> or <list>, you have passed a: {type(slider_dims)}"
            )

        self.frame_apply: Dict[int, callable] = dict()

        if frame_apply is not None:
            if callable(frame_apply):
                self.frame_apply = {0: frame_apply}

            elif isinstance(frame_apply, dict):
                self.frame_apply: Dict[int, callable] = dict.fromkeys(
                    list(range(len(self.data)))
                )

                # dict of {array: dims_order_str}
                for data_ix in list(frame_apply.keys()):
                    if not isinstance(data_ix, int):
                        raise TypeError("`frame_apply` dict keys must be <int>")
                    try:
                        self.frame_apply[data_ix] = frame_apply[data_ix]
                    except Exception:
                        raise IndexError(
                            f"key index {data_ix} out of bounds for `frame_apply`, the bounds are 0 - {len(self.data)}"
                        )
            else:
                raise TypeError(
                    f"`frame_apply` must be a callable or <Dict[int: callable]>, "
                    f"you have passed a: <{type(frame_apply)}>"
                )

        self._window_funcs = None
        self.window_funcs = window_funcs

        self._sliders: Dict[str, Any] = dict()

        # current_index stores {dimension_index: slice_index} for every dimension
        self._current_index: Dict[str, int] = {sax: 0 for sax in self.slider_dims}

        # get max bound for all data arrays for all dimensions
        self._dims_max_bounds: Dict[str, int] = {k: np.inf for k in self.slider_dims}
        for _dim in list(self._dims_max_bounds.keys()):
            for array, order in zip(self.data, self.dims_order):
                self._dims_max_bounds[_dim] = min(
                    self._dims_max_bounds[_dim], array.shape[order.index(_dim)]
                )

        grid_plot_kwargs_default = {"controllers": "sync"}
        if grid_plot_kwargs is None:
            grid_plot_kwargs = dict()

        # update the default kwargs with any user-specified kwargs
        # user specified kwargs will overwrite the defaults
        grid_plot_kwargs_default.update(grid_plot_kwargs)

        self._gridplot: GridPlot = GridPlot(shape=grid_shape, **grid_plot_kwargs_default)

        for data_ix, (d, subplot) in enumerate(zip(self.data, self.gridplot)):
            if self._names is not None:
                name = self._names[data_ix]
            else:
                name = None

            frame = self._process_indices(d, slice_indices=self._current_index)
            frame = self._process_frame_apply(frame, data_ix)
            ig = ImageGraphic(frame, name="image_widget_managed", **kwargs)
            subplot.add_graphic(ig)
            subplot.name = name
            subplot.set_title(name)

            if histogram_widget:
                hlut = HistogramLUT(
                    data=d,
                    image_graphic=ig,
                    name="histogram_lut"
                )

                subplot.docks["right"].add_graphic(hlut)
                subplot.docks["right"].size = 80
                subplot.docks["right"].auto_scale(maintain_aspect=False)
                subplot.docks["right"].controller.enabled = False

        self.block_sliders = False
        self._image_widget_toolbar = None

    @property
    def window_funcs(self) -> Dict[str, _WindowFunctions]:
        """
        Get or set the window functions

        Returns
        -------
        Dict[str, _WindowFunctions]

        """
        return self._window_funcs

    @window_funcs.setter
    def window_funcs(self, sa: Union[int, Dict[str, int]]):
        if sa is None:
            self._window_funcs = None
            return

        # for a single dim
        elif isinstance(sa, tuple):
            if len(self.slider_dims) > 1:
                raise TypeError(
                    "Must pass dict argument to window_funcs if using multiple sliders. See the docstring."
                )
            if not callable(sa[0]) or not isinstance(sa[1], int):
                raise TypeError(
                    "Tuple argument to `window_funcs` must be in the form of (func, window_size). See the docstring."
                )

            dim_str = self.slider_dims[0]
            self._window_funcs = dict()
            self._window_funcs[dim_str] = _WindowFunctions(*sa)

        # for multiple dims
        elif isinstance(sa, dict):
            if not all(
                [isinstance(_sa, tuple) or (_sa is None) for _sa in sa.values()]
            ):
                raise TypeError(
                    "dict argument to `window_funcs` must be in the form of: "
                    "`{dimension: (func, window_size)}`. "
                    "See the docstring."
                )
            for v in sa.values():
                if v is not None:
                    if not callable(v[0]) or not (
                        isinstance(v[1], int) or v[1] is None
                    ):
                        raise TypeError(
                            "dict argument to `window_funcs` must be in the form of: "
                            "`{dimension: (func, window_size)}`. "
                            "See the docstring."
                        )

            if not isinstance(self._window_funcs, dict):
                self._window_funcs = dict()

            for k in list(sa.keys()):
                if sa[k] is None:
                    self._window_funcs[k] = None
                else:
                    self._window_funcs[k] = _WindowFunctions(*sa[k])

        else:
            raise TypeError(
                f"`window_funcs` must be of type `int` if using a single slider or a dict if using multiple sliders. "
                f"You have passed a {type(sa)}. See the docstring."
            )

    def _process_indices(
        self, array: np.ndarray, slice_indices: Dict[Union[int, str], int]
    ) -> np.ndarray:
        """
        Get the 2D array from the given slice indices. If not returning a 2D slice (such as due to window_funcs)
        then `frame_apply` must take this output and return a 2D array

        Parameters
        ----------
        array: np.ndarray
            array-like to get a 2D slice from

        slice_indices: Dict[int, int]
            dict in form of {dimension_index: slice_index}
            For example if an array has shape [1000, 30, 512, 512] corresponding to [t, z, x, y]:
                To get the 100th timepoint and 3rd z-plane pass:
                    {"t": 100, "z": 3}, or {0: 100, 1: 3}

        Returns
        -------
        np.ndarray
            array-like, 2D slice

        """
        indexer = [slice(None)] * self.ndim

        numerical_dims = list()
        for dim in list(slice_indices.keys()):
            if isinstance(dim, str):
                data_ix = None
                for i in range(len(self.data)):
                    if self.data[i] is array:
                        data_ix = i
                        break
                if data_ix is None:
                    raise ValueError(f"Given `array` not found in `self.data`")
                # get axes order for that specific array
                numerical_dim = self.dims_order[data_ix].index(dim)
            else:
                numerical_dim = dim

            indices_dim = slice_indices[dim]

            # takes care of averaging if it was specified
            indices_dim = self._get_window_indices(data_ix, numerical_dim, indices_dim)

            # set the indices for this dimension
            indexer[numerical_dim] = indices_dim

            numerical_dims.append(numerical_dim)

        # apply indexing to the array
        # use window function is given for this dimension
        if self.window_funcs is not None:
            a = array
            for i, dim in enumerate(sorted(numerical_dims)):
                dim_str = self.dims_order[data_ix][dim]
                dim = dim - i  # since we loose a dimension every iteration
                _indexer = [slice(None)] * (self.ndim - i)
                _indexer[dim] = indexer[dim + i]

                # if the indexer is an int, this dim has no window func
                if isinstance(_indexer[dim], int):
                    a = a[tuple(_indexer)]
                else:
                    # if the indices are from `self._get_window_indices`
                    func = self.window_funcs[dim_str].func
                    window = a[tuple(_indexer)]
                    a = func(window, axis=dim)
                    # a = np.mean(a[tuple(_indexer)], axis=dim)
            return a
        else:
            return array[tuple(indexer)]

    def _get_window_indices(self, data_ix, dim, indices_dim):
        if self.window_funcs is None:
            return indices_dim

        else:
            ix = indices_dim

            dim_str = self.dims_order[data_ix][dim]

            # if no window stuff specified for this dim
            if dim_str not in self.window_funcs.keys():
                return indices_dim

            # if window stuff is set to None for this dim
            # example: {"t": None}
            if self.window_funcs[dim_str] is None:
                return indices_dim

            window_size = self.window_funcs[dim_str].window_size

            if (window_size == 0) or (window_size is None):
                return indices_dim

            half_window = int((window_size - 1) / 2)  # half-window size
            # get the max bound for that dimension
            max_bound = self._dims_max_bounds[dim_str]
            indices_dim = range(
                max(0, ix - half_window), min(max_bound, ix + half_window)
            )
            return indices_dim

    def _process_frame_apply(self, array, data_ix) -> np.ndarray:
        if callable(self.frame_apply):
            return self.frame_apply(array)

        if data_ix not in self.frame_apply.keys():
            return array

        elif self.frame_apply[data_ix] is not None:
            return self.frame_apply[data_ix](array)

        return array

    def _slider_value_changed(self, dimension: str, change: Union[dict, int]):
        if self.block_sliders:
            return
        if isinstance(change, dict):
            value = change["new"]
        else:
            value = change
        self.current_index = {dimension: value}

    def reset_vmin_vmax(self):
        """
        Reset the vmin and vmax w.r.t. the full data
        """
        for ig in self.managed_graphics:
            ig.cmap.reset_vmin_vmax()

    def reset_vmin_vmax_frame(self):
        """
        Resets the vmin vmax and HistogramLUT widgets w.r.t. the current data shown in the
        ImageGraphic instead of the data in the full data array. For example, if a post-processing
        function is used, the range of values in the ImageGraphic can be very different from the
        range of values in the full data array.
        """
        for subplot in self.gridplot:
            hlut = subplot.docks["right"]["histogram_lut"]
            # set the data using the current image graphic data
            hlut.set_data(subplot["image_widget_managed"].data())

    def set_data(
        self,
        new_data: Union[np.ndarray, List[np.ndarray]],
        reset_vmin_vmax: bool = True,
        reset_indices: bool = True,
    ):
        """
        Change data of widget. Note: sliders max currently update only for ``txy`` and ``tzxy`` data.

        Parameters
        ----------
        new_data: array-like or list of array-like
            The new data to display in the widget

        reset_vmin_vmax: bool, default ``True``
            reset the vmin vmax levels based on the new data

        reset_indices: bool, default ``True``
            reset the current index for all dimensions to 0

        """

        if reset_indices:
            for key in self.current_index:
                self.current_index[key] = 0
            for key in self.sliders:
                self.sliders[key].value = 0

        # set slider max according to new data
        max_lengths = {"t": np.inf, "z": np.inf}

        if isinstance(new_data, np.ndarray):
            new_data = [new_data]

        if len(self._data) != len(new_data):
            raise ValueError(
                f"number of new data arrays {len(new_data)} must match"
                f" current number of data arrays {len(self._data)}"
            )
        # check all arrays
        for i, (new_array, current_array) in enumerate(zip(new_data, self._data)):
            if new_array.ndim != current_array.ndim:
                raise ValueError(
                    f"new data ndim {new_array.ndim} at index {i} "
                    f"does not equal current data ndim {current_array.ndim}"
                )

        # if checks pass, update with new data
        for i, (new_array, current_array, subplot) in enumerate(
            zip(new_data, self._data, self.gridplot)
        ):
            # check last two dims (x and y) to see if data shape is changing
            old_data_shape = self._data[i].shape[-2:]
            self._data[i] = new_array

            if old_data_shape != new_array.shape[-2:]:
                # delete graphics at index zero
                subplot.delete_graphic(graphic=subplot["image_widget_managed"])
                # insert new graphic at index zero
                frame = self._process_indices(
                    new_array, slice_indices=self._current_index
                )
                frame = self._process_frame_apply(frame, i)
                new_graphic = ImageGraphic(data=frame, name="image_widget_managed")
                subplot.insert_graphic(graphic=new_graphic)

            if new_array.ndim > 2:
                # to set max of time slider, txy or tzxy
                max_lengths["t"] = min(max_lengths["t"], new_array.shape[0] - 1)

            if new_array.ndim > 3:  # tzxy
                max_lengths["z"] = min(max_lengths["z"], new_array.shape[1] - 1)

            # set histogram widget
            subplot.docks["right"]["histogram_lut"].set_data(new_array, reset_vmin_vmax=reset_vmin_vmax)

        # set slider maxes
        # TODO: maybe make this stuff a property, like ndims, n_frames etc. and have it set the sliders
        for key in self.sliders.keys():
            self.sliders[key].max = max_lengths[key]
            self._dims_max_bounds[key] = max_lengths[key]

        # force graphics to update
        self.current_index = self.current_index

    def show(self, toolbar: bool = True, sidecar: bool = False, sidecar_kwargs: dict = None):
        """
        Show the widget

        Returns
        -------
        OutputContext
        """
        if self.gridplot.canvas.__class__.__name__ == "JupyterWgpuCanvas":
            self._image_widget_toolbar = IpywidgetImageWidgetToolbar(self)

        elif self.gridplot.canvas.__class__.__name__ == "QWgpuCanvas":
            self._image_widget_toolbar = QToolbarImageWidget(self)

        return self.gridplot.show(
            toolbar=toolbar,
            sidecar=sidecar,
            sidecar_kwargs=sidecar_kwargs,
            add_widgets=[self._image_widget_toolbar]
        )

    def close(self):
        """Close Widget"""
        self.gridplot.close()
