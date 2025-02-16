from copy import deepcopy
from typing import Callable
from warnings import warn

import numpy as np

from rendercanvas import BaseRenderCanvas

from ...layouts import ImguiFigure as Figure
from ...graphics import ImageGraphic
from ...utils import calculate_figure_shape, quick_min_max
from ...tools import HistogramLUTTool
from ._sliders import ImageWidgetSliders


# Number of dimensions that represent one image/one frame
# For grayscale shape will be [n_rows, n_cols], i.e. 2 dims
# For RGB(A) shape will be [n_rows, n_cols, c] where c is of size 3 (RGB) or 4 (RGBA)
IMAGE_DIM_COUNTS = {"gray": 2, "rgb": 3}

# Map boolean (indicating whether we use RGB or grayscale) to the string. Used to index RGB_DIM_MAP
RGB_BOOL_MAP = {False: "gray", True: "rgb"}

# Dimensions that can be scrolled from a given data array
SCROLLABLE_DIMS_ORDER = {
    0: "",
    1: "t",
    2: "tz",
}

ALLOWED_SLIDER_DIMS = {0: "t", 1: "z"}

ALLOWED_WINDOW_DIMS = {"t", "z"}


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

    def __init__(self, image_widget, func: callable, window_size: int):
        self._image_widget = image_widget
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

        # force update
        self._image_widget.current_index = self._image_widget.current_index

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

        self._image_widget.current_index = self._image_widget.current_index

    def __repr__(self):
        return f"func: {self.func}, window_size: {self.window_size}"


class ImageWidget:
    @property
    def figure(self) -> Figure:
        """
        ``Figure`` used by `ImageWidget`.
        """
        return self._figure

    @property
    def managed_graphics(self) -> list[ImageGraphic]:
        """List of ``ImageWidget`` managed graphics."""
        iw_managed = list()
        for subplot in self.figure:
            # empty subplots will not have any image widget data
            if len(subplot.graphics) > 0:
                iw_managed.append(subplot["image_widget_managed"])
        return iw_managed

    @property
    def cmap(self) -> list[str]:
        cmaps = list()
        for g in self.managed_graphics:
            cmaps.append(g.cmap)

        return cmaps

    @cmap.setter
    def cmap(self, names: str | list[str]):
        if isinstance(names, list):
            if not all([isinstance(n, str) for n in names]):
                raise TypeError(
                    f"Must pass cmap name as a `str` of list of `str`, you have passed:\n{names}"
                )

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
    def data(self) -> list[np.ndarray]:
        """data currently displayed in the widget"""
        return self._data

    @property
    def ndim(self) -> int:
        """Number of dimensions of grayscale data displayed in the widget (it will be 1 more for RGB(A) data)"""
        return self._ndim

    @property
    def n_scrollable_dims(self) -> list[int]:
        """
        list indicating the number of dimenensions that are scrollable for each data array
        All other dimensions are frame/image data, i.e. [rows, cols] or [rows, cols, rgb(a)]
        """
        return self._n_scrollable_dims

    @property
    def slider_dims(self) -> list[str]:
        """the dimensions that the sliders index"""
        return self._slider_dims

    @property
    def current_index(self) -> dict[str, int]:
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
    def current_index(self, index: dict[str, int]):
        if not self._initialized:
            return

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

        for i, (ig, data) in enumerate(zip(self.managed_graphics, self.data)):
            frame = self._process_indices(data, self._current_index)
            frame = self._process_frame_apply(frame, i)
            ig.data = frame

        # call any event handlers
        for handler in self._current_index_changed_handlers:
            handler(self.current_index)

    @property
    def n_img_dims(self) -> list[int]:
        """
        list indicating the number of dimensions that contain image/single frame data for each data array.
        if 2: data are grayscale, i.e. [x, y] dims, if 3: data are [x, y, c] where c is RGB or RGBA,
        this is the complement of `n_scrollable_dims`
        """
        return self._n_img_dims

    def _get_n_scrollable_dims(self, curr_arr: np.ndarray, rgb: bool) -> list[int]:
        """
        For a given ``array`` displayed in the ImageWidget, this function infers how many of the dimensions are
        supported by sliders (aka scrollable). Ex: "xy" data has 0 scrollable dims, "txy" has 1, "tzxy" has 2.

        Parameters
        ----------
        curr_arr: np.ndarray
            np.ndarray or a list of array-like

        rgb: bool
            True if we view this as RGB(A) and False if grayscale

        Returns
        -------
        int
            Number of scrollable dimensions for each ``array`` in the dataset.
        """

        n_img_dims = IMAGE_DIM_COUNTS[RGB_BOOL_MAP[rgb]]
        # Make sure each image stack at least ``n_img_dims`` dimensions
        if len(curr_arr.shape) < n_img_dims:
            raise ValueError(
                f"Your array has shape {curr_arr.shape} "
                f"but you specified that each image in your array is {n_img_dims}D "
            )

        # If RGB(A), last dim must be 3 or 4
        if n_img_dims == 3:
            if not (curr_arr.shape[-1] == 3 or curr_arr.shape[-1] == 4):
                raise ValueError(
                    f"Expected size 3 or 4 for last dimension of RGB(A) array, got: {curr_arr.shape[-1]}."
                )

        n_scrollable_dims = len(curr_arr.shape) - n_img_dims

        if n_scrollable_dims not in SCROLLABLE_DIMS_ORDER.keys():
            raise ValueError(f"Array had shape {curr_arr.shape} which is not supported")

        return n_scrollable_dims

    def __init__(
        self,
        data: np.ndarray | list[np.ndarray],
        window_funcs: dict[str, tuple[Callable, int]] = None,
        frame_apply: Callable | dict[int, Callable] = None,
        figure_shape: tuple[int, int] = None,
        names: list[str] = None,
        figure_kwargs: dict = None,
        histogram_widget: bool = True,
        rgb: bool | list[bool] = None,
        cmap: str = "plasma",
        graphic_kwargs: dict = None,
    ):
        """
        This widget facilitates high-level navigation through image stacks, which are arrays containing one or more
        images. It includes sliders for key dimensions such as "t" (time) and "z", enabling users to smoothly navigate
        through one or multiple image stacks simultaneously.

        Allowed dimensions orders for each image stack: Note that each has a an optional (c) channel which refers to
        RGB(A) a channel. So this channel should be either 3 or 4.

        ======= ==========
        n_dims  dims order
        ======= ==========
        2       "xy(c)"
        3       "txy(c)"
        4       "tzxy(c)"
        ======= ==========

        Parameters
        ----------
        data: Union[np.ndarray, List[np.ndarray]
            array-like or a list of array-like

        window_funcs: dict[str, tuple[Callable, int]], i.e. {"t" or "z": (callable, int)}
            | Apply function(s) with rolling windows along "t" and/or "z" dimensions of the `data` arrays.
            | Pass a dict in the form: {dimension: (func, window_size)}, `func` must take a slice of the data array as
            | the first argument and must take `axis` as a kwarg.
            | Ex: mean along "t" dimension: {"t": (np.mean, 11)}, if `current_index` of "t" is 50, it will pass frames
            | 45 to 55 to `np.mean` with `axis=0`.
            | Ex: max along z dim: {"z": (np.max, 3)}, passes current, previous & next frame to `np.max` with `axis=1`

        frame_apply: Union[callable, Dict[int, callable]]
            | Apply function(s) to `data` arrays before to generate final 2D image that is displayed.
            | Ex: apply a spatial gaussian filter
            | Pass a single function or a dict of functions to apply to each array individually
            | examples: ``{array_index: to_grayscale}``, ``{0: to_grayscale, 2: threshold_img}``
            | "array_index" is the position of the corresponding array in the data list.
            | if `window_funcs` is used, then this function is applied after `window_funcs`
            | this function must be a callable that returns a 2D array
            | example use case: converting an RGB frame from video to a 2D grayscale frame

        figure_shape: Optional[Tuple[int, int]]
            manually provide the shape for the Figure, otherwise the number of rows and columns is estimated

        figure_kwargs: dict, optional
            passed to `GridPlot`

        names: Optional[str]
            gives names to the subplots

        histogram_widget: bool, default False
            make histogram LUT widget for each subplot

        rgb: bool | list[bool], default None
            bool or list of bool for each input data array in the ImageWidget, indicating whether the corresponding
            data arrays are grayscale or RGB(A).

        graphic_kwargs: Any
            passed to each ImageGraphic in the ImageWidget figure subplots

        """
        self._initialized = False

        if figure_kwargs is None:
            figure_kwargs = dict()

        if _is_arraylike(data):
            data = [data]

        if isinstance(data, list):
            # verify that it's a list of np.ndarray
            if all([_is_arraylike(d) for d in data]):
                # Grid computations
                if figure_shape is None:
                    if "shape" in figure_kwargs:
                        figure_shape = figure_kwargs["shape"]
                    else:
                        figure_shape = calculate_figure_shape(len(data))

                # Regardless of how figure_shape is computed, below code
                # verifies that figure shape is large enough for the number of image arrays passed
                if figure_shape[0] * figure_shape[1] < len(data):
                    original_shape = (figure_shape[0], figure_shape[1])
                    figure_shape = calculate_figure_shape(len(data))
                    warn(
                        f"Original `figure_shape` was: {original_shape} "
                        f" but data length is {len(data)}"
                        f" Resetting figure shape to: {figure_shape}"
                    )

                self._data: list[np.ndarray] = data

                # Establish number of image dimensions and number of scrollable dimensions for each array
                if rgb is None:
                    rgb = [False] * len(self.data)
                if isinstance(rgb, bool):
                    rgb = [rgb] * len(self.data)
                if not isinstance(rgb, list):
                    raise TypeError(
                        f"`rgb` parameter must be a bool or list of bool, a <{type(rgb)}> was provided"
                    )
                if not len(rgb) == len(self.data):
                    raise ValueError(
                        f"len(rgb) != len(data), {len(rgb)} != {len(self.data)}. These must be equal"
                    )

                self._rgb = rgb

                self._n_img_dims = [
                    IMAGE_DIM_COUNTS[RGB_BOOL_MAP[self._rgb[i]]]
                    for i in range(len(self.data))
                ]

                self._n_scrollable_dims = [
                    self._get_n_scrollable_dims(self.data[i], self._rgb[i])
                    for i in range(len(self.data))
                ]

                # Define ndim of ImageWidget instance as largest number of scrollable dims + 2 (grayscale dimensions)
                self._ndim = (
                    max(
                        [
                            self.n_scrollable_dims[i]
                            for i in range(len(self.n_scrollable_dims))
                        ]
                    )
                    + IMAGE_DIM_COUNTS[RGB_BOOL_MAP[False]]
                )

                if names is not None:
                    if not all([isinstance(n, str) for n in names]):
                        raise TypeError(
                            "optional argument `names` must be a list of str"
                        )

                    if len(names) != len(self.data):
                        raise ValueError(
                            "number of `names` for subplots must be same as the number of data arrays"
                        )

            else:
                raise TypeError(
                    f"If passing a list to `data` all elements must be an "
                    f"array-like type representing an n-dimensional image. "
                    f"You have passed the following types:\n"
                    f"{[type(a) for a in data]}"
                )
        else:
            raise TypeError(
                f"`data` must be an array-like type or a list of array-like."
                f"You have passed the following type {type(data)}"
            )

        # Sliders are made for all dimensions except the image dimensions
        self._slider_dims = list()
        max_scrollable = max(
            [self.n_scrollable_dims[i] for i in range(len(self.n_scrollable_dims))]
        )
        for dim in range(max_scrollable):
            if dim in ALLOWED_SLIDER_DIMS.keys():
                self.slider_dims.append(ALLOWED_SLIDER_DIMS[dim])

        self._frame_apply: dict[int, callable] = dict()

        if frame_apply is not None:
            if callable(frame_apply):
                self._frame_apply = frame_apply

            elif isinstance(frame_apply, dict):
                self._frame_apply: dict[int, callable] = dict.fromkeys(
                    list(range(len(self.data)))
                )

                # dict of {array: dims_order_str}
                for data_ix in list(frame_apply.keys()):
                    if not isinstance(data_ix, int):
                        raise TypeError("`frame_apply` dict keys must be <int>")
                    try:
                        self._frame_apply[data_ix] = frame_apply[data_ix]
                    except Exception:
                        raise IndexError(
                            f"key index {data_ix} out of bounds for `frame_apply`, the bounds are 0 - {len(self.data)}"
                        )
            else:
                raise TypeError(
                    f"`frame_apply` must be a callable or <Dict[int: callable]>, "
                    f"you have passed a: <{type(frame_apply)}>"
                )

        # current_index stores {dimension_index: slice_index} for every dimension
        self._current_index: dict[str, int] = {sax: 0 for sax in self.slider_dims}

        self._window_funcs = None
        self.window_funcs = window_funcs

        # get max bound for all data arrays for all slider dimensions and ensure compatibility across slider dims
        self._dims_max_bounds: dict[str, int] = {k: 0 for k in self.slider_dims}
        for i, _dim in enumerate(list(self._dims_max_bounds.keys())):
            for array, partition in zip(self.data, self.n_scrollable_dims):
                if partition <= i:
                    continue
                else:
                    if 0 < self._dims_max_bounds[_dim] != array.shape[i]:
                        raise ValueError(f"Two arrays differ along dimension {_dim}")
                    else:
                        self._dims_max_bounds[_dim] = max(
                            self._dims_max_bounds[_dim], array.shape[i]
                        )

        figure_kwargs_default = {"controller_ids": "sync", "names": names}

        # update the default kwargs with any user-specified kwargs
        # user specified kwargs will overwrite the defaults
        figure_kwargs_default.update(figure_kwargs)
        figure_kwargs_default["shape"] = figure_shape

        if graphic_kwargs is None:
            graphic_kwargs = dict()

        graphic_kwargs.update({"cmap": cmap})

        vmin_specified, vmax_specified = None, None
        if "vmin" in graphic_kwargs.keys():
            vmin_specified = graphic_kwargs.pop("vmin")
        if "vmax" in graphic_kwargs.keys():
            vmax_specified = graphic_kwargs.pop("vmax")

        self._figure: Figure = Figure(**figure_kwargs_default)

        self._histogram_widget = histogram_widget
        for data_ix, (d, subplot) in enumerate(zip(self.data, self.figure)):

            frame = self._process_indices(d, slice_indices=self._current_index)
            frame = self._process_frame_apply(frame, data_ix)

            if (vmin_specified is None) or (vmax_specified is None):
                # if either vmin or vmax are not specified, calculate an estimate by subsampling
                vmin_estimate, vmax_estimate = quick_min_max(d)

                # decide vmin, vmax passed to ImageGraphic constructor based on whether it's user specified or now
                if vmin_specified is None:
                    # user hasn't specified vmin, use estimated value
                    vmin = vmin_estimate
                else:
                    # user has provided a specific value, use that
                    vmin = vmin_specified

                if vmax_specified is None:
                    vmax = vmax_estimate
                else:
                    vmax = vmax_specified
            else:
                # both vmin and vmax are specified
                vmin, vmax = vmin_specified, vmax_specified

            ig = ImageGraphic(
                frame,
                name="image_widget_managed",
                vmin=vmin,
                vmax=vmax,
                **graphic_kwargs,
            )
            subplot.add_graphic(ig)

            if self._histogram_widget:
                hlut = HistogramLUTTool(data=d, image_graphic=ig, name="histogram_lut")

                subplot.docks["right"].add_graphic(hlut)
                subplot.docks["right"].size = 80
                subplot.docks["right"].auto_scale(maintain_aspect=False)
                subplot.docks["right"].controller.enabled = False

        # hard code the expected height so that the first render looks right in tests, docs etc.
        if len(self.slider_dims) == 0:
            ui_size = 57
        if len(self.slider_dims) == 1:
            ui_size = 106
        elif len(self.slider_dims) == 2:
            ui_size = 155

        self._image_widget_sliders = ImageWidgetSliders(
            figure=self.figure,
            size=ui_size,
            location="bottom",
            title="ImageWidget Controls",
            image_widget=self,
        )

        self.figure.add_gui(self._image_widget_sliders)

        self._initialized = True

        self._current_index_changed_handlers = set()

    @property
    def frame_apply(self) -> dict | None:
        return self._frame_apply

    @frame_apply.setter
    def frame_apply(self, frame_apply: dict[int, callable]):
        if frame_apply is None:
            frame_apply = dict()

        self._frame_apply = frame_apply
        # force update image graphic
        self.current_index = self.current_index

    @property
    def window_funcs(self) -> dict[str, _WindowFunctions]:
        """
        Get or set the window functions

        Returns
        -------
        Dict[str, _WindowFunctions]

        """
        return self._window_funcs

    @window_funcs.setter
    def window_funcs(self, callable_dict: dict[str, int]):
        if callable_dict is None:
            self._window_funcs = None
            # force frame to update
            self.current_index = self.current_index
            return

        elif isinstance(callable_dict, dict):
            if not set(callable_dict.keys()).issubset(ALLOWED_WINDOW_DIMS):
                raise ValueError(
                    f"The only allowed keys to window funcs are {list(ALLOWED_WINDOW_DIMS)} "
                    f"Your window func passed in these keys: {list(callable_dict.keys())}"
                )
            if not all(
                [
                    isinstance(_callable_dict, tuple)
                    for _callable_dict in callable_dict.values()
                ]
            ):
                raise TypeError(
                    "dict argument to `window_funcs` must be in the form of: "
                    "`{dimension: (func, window_size)}`. "
                    "See the docstring."
                )
            for v in callable_dict.values():
                if not callable(v[0]):
                    raise TypeError(
                        "dict argument to `window_funcs` must be in the form of: "
                        "`{dimension: (func, window_size)}`. "
                        "See the docstring."
                    )
                if not isinstance(v[1], int):
                    raise TypeError(
                        f"dict argument to `window_funcs` must be in the form of: "
                        "`{dimension: (func, window_size)}`. "
                        f"where window_size is integer. you passed in {v[1]} for window_size"
                    )

            if not isinstance(self._window_funcs, dict):
                self._window_funcs = dict()

            for k in list(callable_dict.keys()):
                self._window_funcs[k] = _WindowFunctions(self, *callable_dict[k])

        else:
            raise TypeError(
                f"`window_funcs` must be either Nonetype or dict."
                f"You have passed a {type(callable_dict)}. See the docstring."
            )

        # force frame to update
        self.current_index = self.current_index

    def _process_indices(
        self, array: np.ndarray, slice_indices: dict[str, int]
    ) -> np.ndarray:
        """
        Get the 2D array from the given slice indices. If not returning a 2D slice (such as due to window_funcs)
        then `frame_apply` must take this output and return a 2D array

        Parameters
        ----------
        array: np.ndarray
            array-like to get a 2D slice from

        slice_indices: Dict[str, int]
            dict in form of {dimension_index: current_index}
            For example if an array has shape [1000, 30, 512, 512] corresponding to [t, z, x, y]:
                To get the 100th timepoint and 3rd z-plane pass:
                    {"t": 100, "z": 3}

        Returns
        -------
        np.ndarray
            array-like, 2D slice

        """

        data_ix = None
        for i in range(len(self.data)):
            if self.data[i] is array:
                data_ix = i
                break

        numerical_dims = list()

        # Totally number of dimensions for this specific array
        curr_ndim = self.data[data_ix].ndim

        # Initialize slices for each dimension of array
        indexer = [slice(None)] * curr_ndim

        # Maps from n_scrollable_dims to one of "", "t", "tz", etc.
        curr_scrollable_format = SCROLLABLE_DIMS_ORDER[self.n_scrollable_dims[data_ix]]
        for dim in list(slice_indices.keys()):
            if dim not in curr_scrollable_format:
                continue
            # get axes order for that specific array
            numerical_dim = curr_scrollable_format.index(dim)

            indices_dim = slice_indices[dim]

            # takes care of index selection (window slicing) for this specific axis
            indices_dim = self._get_window_indices(data_ix, numerical_dim, indices_dim)

            # set the indices for this dimension
            indexer[numerical_dim] = indices_dim

            numerical_dims.append(numerical_dim)

        # apply indexing to the array
        # use window function is given for this dimension
        if self.window_funcs is not None:
            a = array
            for i, dim in enumerate(sorted(numerical_dims)):
                dim_str = curr_scrollable_format[dim]
                dim = dim - i  # since we loose a dimension every iteration
                _indexer = [slice(None)] * (curr_ndim - i)
                _indexer[dim] = indexer[dim + i]

                # if the indexer is an int, this dim has no window func
                if isinstance(_indexer[dim], int):
                    a = a[tuple(_indexer)]
                else:
                    # if the indices are from `self._get_window_indices`
                    func = self.window_funcs[dim_str].func
                    window = a[tuple(_indexer)]
                    a = func(window, axis=dim)
            return a
        else:
            return array[tuple(indexer)]

    def _get_window_indices(self, data_ix, dim, indices_dim):
        if self.window_funcs is None:
            return indices_dim

        else:
            ix = indices_dim

            dim_str = SCROLLABLE_DIMS_ORDER[self.n_scrollable_dims[data_ix]][dim]

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
        if callable(self._frame_apply):
            return self._frame_apply(array)

        if data_ix not in self._frame_apply.keys():
            return array

        elif self._frame_apply[data_ix] is not None:
            return self._frame_apply[data_ix](array)

        return array

    def add_event_handler(self, handler: callable, event: str = "current_index"):
        """
        Register an event handler.

        Currently the only event that ImageWidget supports is "current_index". This event is
        emitted whenever the index of the ImageWidget changes.

        Parameters
        ----------
        handler: callable
            callback function, must take a dict as the only argument. This dict will be the `current_index`

        event: str, "current_index"
            the only supported event is "current_index"

        Example
        -------

        .. code-block:: py

            def my_handler(index):
                print(index)
                # example prints: {"t": 100} if data has only time dimension
                # "z" index will be another key if present in the data, ex: {"t": 100, "z": 5}

            # create an image widget
            iw = ImageWidget(...)

            # add event handler
            iw.add_event_handler(my_handler)

        """
        if event != "current_index":
            raise ValueError(
                "`current_index` is the only event supported by `ImageWidget`"
            )

        self._current_index_changed_handlers.add(handler)

    def remove_event_handler(self, handler: callable):
        """Remove a registered event handler"""
        self._current_index_changed_handlers.remove(handler)

    def clear_event_handlers(self):
        """Clear all registered event handlers"""
        self._current_index_changed_handlers.clear()

    def reset_vmin_vmax(self):
        """
        Reset the vmin and vmax w.r.t. the full data
        """
        for data, subplot in zip(self.data, self.figure):
            if "histogram_lut" not in subplot.docks["right"]:
                continue
            hlut = subplot.docks["right"]["histogram_lut"]
            hlut.set_data(data, reset_vmin_vmax=True)

    def reset_vmin_vmax_frame(self):
        """
        Resets the vmin vmax and HistogramLUT widgets w.r.t. the current data shown in the
        ImageGraphic instead of the data in the full data array. For example, if a post-processing
        function is used, the range of values in the ImageGraphic can be very different from the
        range of values in the full data array.

        TODO: We could think of applying the frame_apply funcs to a subsample of the entire array to get a better estimate of vmin vmax?
        """

        for subplot in self.figure:
            if "histogram_lut" not in subplot.docks["right"]:
                continue

            hlut = subplot.docks["right"]["histogram_lut"]
            # set the data using the current image graphic data
            hlut.set_data(subplot["image_widget_managed"].data.value)

    def set_data(
        self,
        new_data: np.ndarray | list[np.ndarray],
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

        # set slider max according to new data
        max_lengths = dict()
        for scroll_dim in self.slider_dims:
            max_lengths[scroll_dim] = np.inf

        if _is_arraylike(new_data):
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

            # Computes the number of scrollable dims and also validates new_array
            new_scrollable_dims = self._get_n_scrollable_dims(new_array, self._rgb[i])

            if self.n_scrollable_dims[i] != new_scrollable_dims:
                raise ValueError(
                    f"number of dimensions of data arrays must match number of dimensions of "
                    f"existing data arrays"
                )

        # if checks pass, update with new data
        for i, (new_array, current_array, subplot) in enumerate(
            zip(new_data, self._data, self.figure)
        ):
            # check last two dims (x and y) to see if data shape is changing
            old_data_shape = self._data[i].shape[-self.n_img_dims[i] :]
            self._data[i] = new_array

            if old_data_shape != new_array.shape[-self.n_img_dims[i] :]:
                frame = self._process_indices(
                    new_array, slice_indices=self._current_index
                )
                frame = self._process_frame_apply(frame, i)

                # make new graphic first
                new_graphic = ImageGraphic(data=frame, name="image_widget_managed")

                # set hlut tool to use new graphic
                subplot.docks["right"]["histogram_lut"].image_graphic = new_graphic
                # delete old graphic after setting hlut tool to new graphic
                # this ensures gc
                subplot.delete_graphic(graphic=subplot["image_widget_managed"])
                subplot.insert_graphic(graphic=new_graphic)

            # Returns "", "t", or "tz"
            curr_scrollable_format = SCROLLABLE_DIMS_ORDER[self.n_scrollable_dims[i]]

            for scroll_dim in self.slider_dims:
                if scroll_dim in curr_scrollable_format:
                    new_length = new_array.shape[
                        curr_scrollable_format.index(scroll_dim)
                    ]
                    if max_lengths[scroll_dim] == np.inf:
                        max_lengths[scroll_dim] = new_length
                    elif max_lengths[scroll_dim] != new_length:
                        raise ValueError(
                            f"New arrays have differing values along dim {scroll_dim}"
                        )

                    self._dims_max_bounds[scroll_dim] = max_lengths[scroll_dim]

            # set histogram widget
            if self._histogram_widget:
                subplot.docks["right"]["histogram_lut"].set_data(
                    new_array, reset_vmin_vmax=reset_vmin_vmax
                )

        # force graphics to update
        self.current_index = self.current_index

    def show(self, **kwargs):
        """
        Show the widget.

        Parameters
        ----------

        kwargs: Any
            passed to `Figure.show()`

        Returns
        -------
        BaseRenderCanvas
            In Qt or GLFW, the canvas window containing the Figure will be shown.
            In jupyter, it will display the plot in the output cell or sidecar.

        """

        return self.figure.show(**kwargs)

    def close(self):
        """Close Widget"""
        self.figure.close()
