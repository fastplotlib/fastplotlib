from ..plot import Plot
from ..layouts import GridPlot
from ..graphics import Image
from ipywidgets.widgets import IntSlider, VBox, HBox, Layout
import numpy as np
from typing import *
from warnings import warn
from functools import partial

DEFAULT_DIMS_ORDER = \
    {
        2: "xy",
        3: "txy",
        4: "tzxy",
        # 5: "tczxy",  # no 5 dim stuff for now
    }


def calc_gridshape(n):
    sr = np.sqrt(n)
    return (
        int(np.ceil(sr)),
        int(np.round(sr))
    )


def is_arraylike(obj) -> bool:
    """
    Checks if the object is array-like.
    For now just checks if obj has `__getitem__()`
    """
    for attr in [
        "__getitem__",
        "shape",
        "ndim"
    ]:
        if not hasattr(obj, attr):
            return False

    return True


class ImageWidget:
    def __init__(
            self,
            data: Union[np.ndarray, List[np.ndarray]],
            dims_order: Union[str, Dict[np.ndarray, str]] = None,
            slider_dims: Union[str, int, List[Union[str, int]]] = None,
            slice_avg: Union[int, Dict[str, int]] = None,
            frame_apply: Union[callable, Dict[Union[int, str], callable]] = None,
            grid_shape: Tuple[int, int] = None,
            **kwargs
    ):
        """
        A high level for displaying n-dimensional image data in conjunction with automatically generated sliders for
        navigating through 1-2 selected dimensions within the image data.

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
            | ``dict`` mapping of ``{array: axis_order}`` if specific arrays have a non-default axes order.
            | examples: "xyt", "tzxy"

        slider_dims: Optional[Union[str, int, List[Union[str, int]]]]
            | The dimensions for which to create a slider
            | can be a single ``str`` such as **"t"**, **"z"** or a numerical ``int`` that indexes the desired dimension
            | can also be a list of ``str`` or ``int`` if multiple sliders are desired for multiple dimensions
            | examples: "t", ["t", "z"]

        slice_avg: Dict[Union[int, str], int]
            | average one or more dimensions using a given window
            | if a slider exists for only one dimension this can be an ``int``.
            | if multiple sliders exist, then it must be a `dict`` mapping in the form of: ``{dimension: window_size}``
            | dimension/axes can be specified using ``str`` such as "t", "z" etc. or ``int`` that indexes the dimension
            | if window_size is not an odd number, adds 1
            | use ``None`` to disable averaging for a dimension, example: ``{"t": 5, "z": None}``

        frame_apply
        grid_shape: Optional[Tuple[int, int]]
            manually provide the shape for a gridplot, otherwise a square gridplot is approximated.

        kwargs: Any
            passed to fastplotlib.graphics.Image
        """
        if isinstance(data, list):
            # verify that it's a list of np.ndarray
            if all([is_arraylike(d) for d in data]):
                if grid_shape is None:
                    grid_shape = calc_gridshape(len(data))

                # verify that user-specified grid shape is large enough for the number of image arrays passed
                elif grid_shape[0] * grid_shape[1] < len(data):
                    grid_shape = calc_gridshape(len(data))
                    warn(f"Invalid `grid_shape` passed, setting grid shape to: {grid_shape}")

                _ndim = [d.ndim for d in data]

                # verify that all image arrays have same number of dimensions
                # sliders get messy otherwise
                if not len(set(_ndim)) == 1:
                    raise ValueError(
                        f"Number of dimensions of all data arrays must match, your ndims are: {_ndim}"
                    )

                self.data: List[np.ndarray] = data
                self.ndim = self.data[0].ndim  # all ndim must be same

                self.plot_type = "grid"

            else:
                raise TypeError(
                    f"If passing a list to `data` all elements must be an "
                    f"array-like type representing an n-dimensional image"
                )

        elif is_arraylike(data):
            self.data = [data]
            self.ndim = self.data[0].ndim

            self.plot_type = "single"
        else:
            raise TypeError(
                f"`data` must be an array-like type representing an n-dimensional image "
                f"or a list of array-like representing a grid of n-dimensional images"
            )

        # default dims order if not passed
        if dims_order is None:
            self.dims_order: List[str] = [DEFAULT_DIMS_ORDER[self.ndim]] * len(self.data)

        elif isinstance(dims_order, str):
            self.dims_order: List[str] = [dims_order] * len(self.data)
        elif isinstance(dims_order, dict):
            self.dims_order: List[str] = [DEFAULT_DIMS_ORDER[self.ndim]] * len(self.data)

            # dict of {array: dims_order_str}
            for array in list(dims_order.keys()):
                # get index of corresponding array in data list
                try:
                    data_ix = None
                    for i in range(len(self.data)):
                        if self.data[i] is array:
                            data_ix = i
                            break
                    if data_ix is None:
                        raise ValueError(
                            f"Given `array` not found in `self.data`"
                        )
                except Exception:
                    raise TypeError(
                        f"`dims_order` must be a <str> or <Dict[array: str]>, "
                        f"with the same array object(s) passed to `data`"
                    )
                # set corresponding dims order from passed `dims_order` dict
                if not set(dims_order[array]) == set(DEFAULT_DIMS_ORDER[self.ndim]):
                    raise ValueError(
                        f"Invalid `dims_order` passed for one of your arrays, "
                        f"valid `dims_order` for given number of dimensions "
                        f"can only contain the following characters: "
                        f"{DEFAULT_DIMS_ORDER[self.ndim]}"
                    )
                self.dims_order[data_ix] = dims_order[array]
        else:
            raise TypeError(f"`dims_order` must be a <str> or <Dict[array: str]>, you have passed a: <{type(dims_order)}>")

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

        # by default slider is only made for "t" - time dimension
        if slider_dims is None:
            slider_dims = "t"

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
                self.slider_dims: List[str] = [self.dims_order[0][slider_dims]]

            # if dimension specified by str
            elif isinstance(slider_dims, str):
                if slider_dims not in self.dims_order[0]:
                    raise ValueError(
                        f"if `slider_dims` is a <str>, it must be a character found in `dims_order`. "
                        f"Your `dims_order` characters are: {set(self.dims_order[0])}."
                    )
                self.slider_dims: List[str] = [slider_dims]

        # multiple sliders, one for each dimension
        elif isinstance(slider_dims, list):
            self.slider_dims: List[str] = list()

            # make sure slice_avg and frame_apply are dicts if multiple sliders are desired
            if (not isinstance(slice_avg, dict)) and (slice_avg is not None):
                raise TypeError(
                    f"`slice_avg` must be a <dict> if multiple `slider_dims` are provided. You must specify the "
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
            raise TypeError(f"`slider_dims` must a <int>, <str> or <list>, you have passed a: {type(slider_dims)}")

        self._slice_avg = None
        self.slice_avg = slice_avg

        self.sliders = list()
        self.vertical_sliders = list()
        self.horizontal_sliders = list()

        # current_index stores {dimension_index: slice_index} for every dimension
        self.current_index: Dict[str, int] = {sax: 0 for sax in self.slider_dims}

        # get max bound for all data arrays for all dimensions
        self.dims_max_bounds: Dict[str, int] = {k: np.inf for k in self.slider_dims}
        for _dim in list(self.dims_max_bounds.keys()):
            for array, order in zip(self.data, self.dims_order):
                self.dims_max_bounds[_dim] = min(self.dims_max_bounds[_dim], array.shape[order.index(_dim)])

        if self.plot_type == "single":
            self.plot: Plot = Plot()

            if slice_avg is not None:
                pass

            frame = self.get_2d_slice(self.data[0], slice_indices=self.current_index)

            self.image_graphics: List[Image] = [self.plot.image(data=frame, **kwargs)]

        elif self.plot_type == "grid":
            self.plot: GridPlot = GridPlot(shape=grid_shape, controllers="sync")

            self.image_graphics = list()
            for d, subplot in zip(self.data, self.plot):
                frame = self.get_2d_slice(d, slice_indices=self.current_index)
                ig = Image(frame, **kwargs)
                subplot.add_graphic(ig)
                self.image_graphics.append(ig)

        self.plot.renderer.add_event_handler(self.set_slider_layout, "resize")

        for sdm in self.slider_dims:
            if sdm == "z":
                # TODO: once ipywidgets plays nicely with HBox and jupyter-rfb can use vertical
                # orientation = "vertical"
                orientation = "horizontal"
            else:
                orientation = "horizontal"

            slider = IntSlider(
                min=0,
                max=self.dims_max_bounds[sdm] - 1,
                step=1,
                value=0,
                description=f"dimension: {sdm}",
                orientation=orientation
            )

            slider.observe(
                partial(self.slider_value_changed, sdm),
                names="value"
            )

            self.sliders.append(slider)
            if orientation == "horizontal":
                self.horizontal_sliders.append(slider)
            elif orientation == "vertical":
                self.vertical_sliders.append(slider)

        # TODO: So just stack everything vertically for now
        self.widget = VBox([
            self.plot.canvas,
            *self.sliders
        ])

        # TODO: there is currently an issue with ipywidgets or jupyter-rfb and HBox doesn't work with RFB canvas
        # self.widget = None
        # hbox = None
        # if len(self.vertical_sliders) > 0:
        #     hbox = HBox(self.vertical_sliders)
        #
        # if len(self.horizontal_sliders) > 0:
        #     if hbox is not None:
        #         self.widget = VBox([
        #             HBox([self.plot.canvas, hbox]),
        #             *self.horizontal_sliders,
        #         ])
        #
        #     else:
        #         self.widget = VBox([self.plot.canvas, *self.horizontal_sliders])

    @property
    def slice_avg(self) -> Union[int, Dict[str, int]]:
        return self._slice_avg

    @slice_avg.setter
    def slice_avg(self, sa: Union[int, Dict[str, int]]):
        if sa is None:
            self._slice_avg = None
            return

        # for a single dim
        elif isinstance(sa, int):
            if sa < 3:
                self._slice_avg = None
                warn(f"Invalid ``slice_avg`` value, setting ``slice_avg = None``. Valid values are integers >= 3.")
                return
            if sa % 2 == 0:
                self._slice_avg = sa + 1
            else:
                self._slice_avg = sa
        # for multiple dims
        elif isinstance(sa, dict):
            self._slice_avg = dict()
            for k in list(sa.keys()):
                if sa[k] is None:
                    self._slice_avg[k] = None
                elif (sa[k] < 3):
                    warn(
                        f"Invalid ``slice_avg`` value, setting ``slice_avg = None``. Valid values are integers >= 3."
                    )
                    self._slice_avg[k] = None
                elif sa[k] % 2 == 0:
                    self._slice_avg[k] = sa[k] + 1
                else:
                    self._slice_avg[k] = sa[k]
        else:
            raise TypeError(
                f"`slice_avg` must be of type `int` if using a single slider or a dict if using multiple sliders. "
                f"You have passed a {type(sa)}. See the docstring."
            )

    def get_2d_slice(
            self,
            array: np.ndarray,
            slice_indices: dict[Union[int, str], int]
    ) -> np.ndarray:
        """
        Get the 2D array from the given slice indices.

        Parameters
        ----------
        array: np.ndarray
            array-like to get a 2D slice from

        slice_indices: dict[int, int]
            dict in form of {dimension_index: slice_index}
            For example if an array has shape [1000, 30, 512, 512] corresponding to [t, z, x, y]:
                To get the 100th timepoint and 3rd z-plane pass:
                    {"t": 100, "z": 3}, or {0: 100, 1: 3}

        Returns
        -------
        np.ndarray
            array-like, 2D slice

        Examples
        --------
        img = get_2d_slice(a, {"t": 50, "z": 4})
        # img is a 2d plane at time index 50 and z-plane 4

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
                    raise ValueError(
                        f"Given `array` not found in `self.data`"
                    )
                # get axes order for that specific array
                numerical_dim = self.dims_order[data_ix].index(dim)
            else:
                numerical_dim = dim

            indices_dim = slice_indices[dim]

            # takes care of averaging if it was specified
            indices_dim = self._process_dim_index(data_ix, numerical_dim, indices_dim)

            # set the indices for this dimension
            indexer[numerical_dim] = indices_dim

            numerical_dims.append(numerical_dim)

        if self.slice_avg is not None:
            a = array
            for i, dim in enumerate(sorted(numerical_dims)):
                dim = dim - i  # since we loose a dimension every iteration
                _indexer = [slice(None)] * (self.ndim - i)
                _indexer[dim] = indexer[dim + i]
                if isinstance(_indexer[dim], int):
                    a = a[tuple(_indexer)]
                else:
                    a = np.mean(a[tuple(_indexer)], axis=dim)
            return a
        else:
            return array[tuple(indexer)]

    def _process_dim_index(self, data_ix, dim, indices_dim):
        if self.slice_avg is None:
            return indices_dim

        else:
            ix = indices_dim

            # if there is only a single dimension for averaging
            if isinstance(self.slice_avg, int):
                sa = self.slice_avg
                dim_str = self.dims_order[0][dim]

            # if there are multiple dims to average, get the avg for the current dim in the loop
            elif isinstance(self.slice_avg, dict):
                dim_str = self.dims_order[data_ix][dim]
                sa = self.slice_avg[dim_str]
                if (sa == 0) or (sa is None):
                    return indices_dim

            hw = int((sa - 1) / 2)  # half-window size
            # get the max bound for that dimension
            max_bound = self.dims_max_bounds[dim_str]
            indices_dim = range(max(0, ix - hw), min(max_bound, ix + hw))
            return indices_dim

    def slider_value_changed(
            self,
            dimension: int,
            change: dict
    ):
        self.current_index[dimension] = change["new"]

        for ig, data in zip(self.image_graphics, self.data):
            frame = self.get_2d_slice(data, self.current_index)
            ig.update_data(frame)

    def set_slider_layout(self, *args):
        w, h = self.plot.renderer.logical_size
        for hs in self.horizontal_sliders:
            hs.layout = Layout(width=f"{w}px")

        for vs in self.vertical_sliders:
            vs.layout = Layout(height=f"{h}px")

    def show(self):
        # start render loop
        self.plot.show()

        return self.widget
