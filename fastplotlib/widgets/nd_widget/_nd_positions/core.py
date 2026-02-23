from functools import partial
from typing import Literal, Callable, Any, Type
from warnings import warn

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

from ....utils import subsample_array, ArrayProtocol

from ....graphics import (
    Graphic,
    ImageGraphic,
    LineGraphic,
    LineStack,
    LineCollection,
    ScatterGraphic,
    ScatterCollection,
)
from ....graphics.utils import pause_events
from ....graphics.selectors import LinearSelector
from ..base import NDProcessor, NDGraphic, WindowFuncCallable


# TODO: Maybe get rid of n_display_dims in NDProcessor,
#  we will know the display dims automatically here from the last dim
#  so maybe we only need it for images?
class NDPositionsProcessor(NDProcessor):
    def __init__(
        self,
        data: Any,
        multi: bool = False,  # TODO: interpret [n - 2] dimension as n_lines or n_points
        display_window: int | float | None = 100,  # window for n_datapoints dim only
        max_display_datapoints: int = 1_000,
        datapoints_window_func: Callable | None = None,
        datapoints_window_size: int | None = None,
        **kwargs,
    ):
        self._display_window = display_window
        self._max_display_datapoints = max_display_datapoints

        # TOOD: this does data validation twice and is a bit messy, cleanup
        self._data = self._validate_data(data)
        self.multi = multi

        super().__init__(data=data, **kwargs)

        self._datapoints_window_func = datapoints_window_func
        self._datapoints_window_size = datapoints_window_size

    def _validate_data(self, data: ArrayProtocol):
        # TODO: determine right validation shape etc.
        return data

    @property
    def display_window(self) -> int | float | None:
        """display window in the reference units for the n_datapoints dim"""
        return self._display_window

    @display_window.setter
    def display_window(self, dw: int | float | None):
        if dw is None:
            self._display_window = None

        elif not isinstance(dw, (int, float)):
            raise TypeError

        self._display_window = dw

    @property
    def max_display_datapoints(self) -> int:
        return self._max_display_datapoints

    @max_display_datapoints.setter
    def max_display_datapoints(self, n: int):
        if not isinstance(n, (int, np.integer)):
            raise TypeError
        if n < 2:
            raise ValueError

        self._max_display_datapoints = n

    @property
    def multi(self) -> bool:
        return self._multi

    @multi.setter
    def multi(self, m: bool):
        if m and self.data.ndim < 3:
            # p is p-datapoints, n is how many lines to show simultaneously (for line collection/stack)
            raise ValueError(
                "ndim must be >= 3 for multi, shape must be [s1..., sn, n, p, 2 | 3]"
            )

        self._multi = m

    @property
    def slider_dims(self) -> tuple[int, ...]:
        """slider dimensions"""
        return tuple(range(self.ndim - 2 - int(self.multi))) + (self.ndim - 2,)

    @property
    def n_slider_dims(self) -> int:
        return self.ndim - 1 - int(self.multi)

    # TODO: validation for datapoints_window_func and size
    @property
    def datapoints_window_func(self) -> tuple[Callable, str] | None:
        """
        Callable and str indicating which dims to apply window function along:
            'all', 'x', 'y', 'z', 'xyz', 'xy', 'xz', 'yz'
        '"""
        return self._datapoints_window_func

    @property
    def datapoints_window_size(self) -> Callable | None:
        return self._datapoints_window_size

    def _apply_window_functions(self, indices: tuple[int, ...]):
        """applies the window functions for each dimension specified"""
        # window size for each dim
        winds = self._window_sizes
        # window function for each dim
        funcs = self._window_funcs

        # TODO: use tuple of None for window funcs and sizes to indicate all None, instead of just None
        # print(winds)
        # print(funcs)
        #
        # if winds is None or funcs is None:
        #     # no window funcs or window sizes, just slice data and return
        #     # clamp to max bounds
        #     indexer = list()
        #     print(indices)
        #     print(self.shape)
        #     for dim, i in enumerate(indices):
        #         i = min(self.shape[dim] - 1, i)
        #         indexer.append(i)
        #
        #     return self.data[tuple(indexer)]

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
                stop = min(self.shape[dim_index], i + hw)

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

    def _get_dw_slices(self, indices) -> tuple[slice] | tuple[slice, slice]:
        # given indices, return slice using display window

        # display window is interpreted using the index mapping for the `p` dim
        dw = self.display_window

        if dw is None:
            # just return everything
            return (slice(None),)

        if dw == 0:
            # just map p dimension at this index and return
            index_p = self.index_mappings[-1](indices[-1])
            return (slice(index_p, index_p + 1),)

        # display window is in reference units, apply display window and then map to array indices
        # clamp w.r.t. 0 and processor shape `p` dim
        hw = dw / 2
        index_p_start = max(self.index_mappings[-1](indices[-1] - hw), 0)
        index_p_stop = min(self.index_mappings[-1](indices[-1] + hw), self.shape[-2])
        if index_p_start >= index_p_stop:
            index_p_stop = index_p_start + 1

        # round to the nearest integer since to use as arra indices
        slices = [slice(round(index_p_start), round(index_p_stop))]

        if self.multi:
            slices.insert(0, slice(None))

        return tuple(slices)

    def get(self, indices: tuple[Any, ...]):
        """
        slices through all slider dims and outputs an array that can be used to set graphic data

        Note that we do not use __getitem__ here since the index is a tuple specifying a single integer
        index for each dimension. Slices are not allowed, therefore __getitem__ is not suitable here.
        """
        # apply any slider index mappings
        array_indices = tuple([m(i) for m, i in zip(self.index_mappings, indices)])

        if len(array_indices) > 1:
            # there are dims in addition to the n_datapoints dim
            # apply window funcs
            # window_output array should be of shape [n_datapoints, 2 | 3]
            window_output = self._apply_window_functions(array_indices[:-1]).squeeze()
        else:
            window_output = self.data

        if self.display_window is not None:
            # display_window is in reference units
            slices = self._get_dw_slices(indices)

        # if self.display_window is not None:
        #     # display window is interpreted using the index mapping for the `p` dim
        #     dw = self.index_mappings[-1](self.display_window)
        #
        #     if dw == 1:
        #         slices = [slice(indices[-1], indices[-1] + 1)]
        #
        #     else:
        #         # half window size
        #         hw = dw // 2
        #
        #         # for now assume just a single index provided that indicates x axis value
        #         start = max(indices[-1] - hw, 0)
        #         stop = start + dw
        #         # also add window size of `p` dim so window_func output has the same number of datapoints
        #         if (
        #             self.datapoints_window_func is not None
        #             and self.datapoints_window_size is not None
        #         ):
        #             stop += self.datapoints_window_size - 1
        #             # TODO: pad with constant if we're using a window func and the index is near the end
        #
        #         # TODO: uncomment this once we have resizeable buffers!!
        #         # stop = min(indices[-1] + hw, self.shape[-2])
        #
        #         slices = [slice(start, stop)]
        #
        #     if self.multi:
        #         # n - 2 dim is n_lines or n_scatters
        #         slices.insert(0, slice(None))

        # data that will be used for the graphical representation
        # a copy is made, if there were no window functions then this is a view of the original data
        graphic_data = window_output[tuple(slices)]

        dw = self.index_mappings[-1](self.display_window)

        # apply window function on the `p` n_datapoints dim
        if (
            self.datapoints_window_func is not None
            and self.datapoints_window_size is not None
            # if there are too many points to efficiently compute the window func
            # applying a window func also requires making a copy so that's a further performance hit
            and (dw < self.max_display_datapoints * 2)
        ):
            # get windows

            # graphic_data will be of shape: [n, p + (ws - 1), 2 | 3]
            # where:
            #   n - number of lines, scatters, heatmap rows
            #   p - number of datapoints/samples

            wf = self.datapoints_window_func[0]
            apply_dims = self.datapoints_window_func[1]
            ws = self.datapoints_window_size

            # apply user's window func
            # result will be of shape [n, p, 2 | 3]
            if apply_dims == "all":
                # windows will be of shape [n, p, 1 | 2 | 3, ws]
                windows = sliding_window_view(graphic_data, ws, axis=-2)
                return wf(windows, axis=-1)

            # map user dims str to tuple of numerical dims
            dims = tuple(map({"x": 0, "y": 1, "z": 2}.get, apply_dims))

            # windows will be of shape [n, p, 1 | 2 | 3, ws]
            windows = sliding_window_view(
                graphic_data[..., dims], ws, axis=-2
            ).squeeze()

            # make a copy because we need to modify it
            graphic_data = graphic_data.copy()

            # this reshape is required to reshape wf outputs of shape [n, p] -> [n, p, 1] only when necessary
            # we need to slice upto dw since we add the `datapoints_window_size` above
            graphic_data[..., :dw, dims] = wf(windows, axis=-1).reshape(
                graphic_data.shape[0], dw, len(dims)
            )

            return graphic_data[
                ..., : dw : max(1, dw // self.max_display_datapoints), :
            ]

        return graphic_data[
            ...,
            : graphic_data.shape[-2] : max(
                1, graphic_data.shape[-2] // self.max_display_datapoints
            ),
            :,
        ]


class NDPositions:
    def __init__(
        self,
        data: Any,
        *args,
        graphic: Type[
            LineGraphic
            | LineCollection
            | LineStack
            | ScatterGraphic
            | ScatterCollection
            | ImageGraphic
        ],
        processor: type[NDPositionsProcessor] = NDPositionsProcessor,
        multi: bool = False,
        display_window: int = 10,
        window_funcs: tuple[WindowFuncCallable | None] | None = None,
        window_sizes: tuple[int | None] | None = None,
        index_mappings: tuple[Callable[[Any], int] | None] | None = None,
        max_display_datapoints: int = 1_000,
        x_range_mode: Literal[None, "fixed-window", "view-range"] = None,
        linear_selector: bool = False,
        graphic_kwargs: dict = None,
        processor_kwargs: dict = None,
    ):
        if issubclass(graphic, LineCollection):
            multi = True

        if processor_kwargs is None:
            processor_kwargs = dict()

        self._processor = processor(
            data,
            *args,
            multi=multi,
            display_window=display_window,
            max_display_datapoints=max_display_datapoints,
            window_funcs=window_funcs,
            window_sizes=window_sizes,
            index_mappings=index_mappings,
            **processor_kwargs,
        )

        self._processor.p_max = 1_000

        self._indices = tuple([0] * self._processor.n_slider_dims)

        self._create_graphic(graphic)

        self._x_range_mode = None
        self._last_x_range = np.array([0.0, 0.0], dtype=np.float32)
        self._block_update_indices = False

        if linear_selector:
            self._linear_selector = LinearSelector(0, limits=(-np.inf, np.inf), edge_color="cyan")
        else:
            self._linear_selector = None

        self._pause = False

    @property
    def processor(self) -> NDPositionsProcessor:
        return self._processor

    @property
    def graphic(
        self,
    ) -> (
        LineGraphic
        | LineCollection
        | LineStack
        | ScatterGraphic
        | ScatterCollection
        | ImageGraphic
    ):
        """LineStack or ImageGraphic for heatmaps"""
        return self._graphic

    @graphic.setter
    def graphic(self, graphic_type):
        if type(self.graphic) is graphic_type:
            return

        plot_area = self._graphic._plot_area
        plot_area.delete_graphic(self._graphic)

        self._create_graphic(graphic_type)
        plot_area.add_graphic(self._graphic)

    @property
    def indices(self) -> tuple:
        return self._indices

    @indices.setter
    def indices(self, indices):
        if self._block_update_indices:
            return

        # this update must be non-reentrant
        self._block_update_indices = True

        data_slice = self.processor.get(indices)

        if isinstance(self.graphic, (LineGraphic, ScatterGraphic)):
            self.graphic.data[:, : data_slice.shape[-1]] = data_slice

        elif isinstance(self.graphic, (LineCollection, ScatterCollection)):
            for g, new_data in zip(self.graphic.graphics, data_slice):
                if g.data.value.shape[0] != new_data.shape[0]:
                    # will replace buffer internally
                    g.data = new_data
                else:
                    # if data are only xy, set only xy
                    g.data[:, : new_data.shape[1]] = new_data

        elif isinstance(self.graphic, ImageGraphic):
            image_data, x0, x_scale = self._create_heatmap_data(data_slice)
            self.graphic.data = image_data
            self.graphic.offset = (x0, *self.graphic.offset[1:])
            self.graphic.scale = (x_scale, *self.graphic.scale[1:])

        # x range of the data
        xr = data_slice[0, 0, 0], data_slice[0, -1, 0]
        if self._x_range_mode is not None:
            self.graphic._plot_area.x_range = xr

        self._last_x_range[:] = xr  # if the update_from_view is polling, prevents it

        if self._linear_selector is not None:
            with pause_events(self._linear_selector):
                self._linear_selector.limits = xr
                self._linear_selector.selection = indices[-1]
                # self._set_linear_selector(x_mid, limits=xr)

        self._indices = indices

        self._block_update_indices = False

    # def _set_linear_selector(self, x_mid, limits):
    #     self._linear_selector.selection = x_mid
    #     self._linear_selector.limits = limits

    def _tooltip_handler(self, graphic, pick_info):
        if isinstance(self.graphic, (LineCollection, ScatterCollection)):
            # get graphic within the collection
            n_index = np.argwhere(self.graphic.graphics == graphic).item()
            p_index = pick_info["vertex_index"]
            return self.processor.tooltip_format(n_index, p_index)

    def _create_graphic(
        self,
        graphic_cls: Type[
            LineGraphic
            | LineCollection
            | LineStack
            | ScatterGraphic
            | ScatterCollection
            | ImageGraphic
        ],
    ):
        if not issubclass(graphic_cls, Graphic):
            raise TypeError

        data_slice = self.processor.get(self.indices)

        if issubclass(graphic_cls, ImageGraphic):
            if not self.processor.multi:
                raise ValueError

            if self.processor.shape[-1] != 2:
                raise ValueError

            image_data, x0, x_scale = self._create_heatmap_data(data_slice)
            self._graphic = graphic_cls(
                image_data, offset=(x0, 0, -1), scale=(x_scale, 1, 1)
            )

        else:
            if issubclass(graphic_cls, LineStack):
                kwargs = {"separation": 0.0}
            else:
                kwargs = dict()
            self._graphic = graphic_cls(data_slice, **kwargs)

        if self.processor.tooltip:
            if isinstance(self._graphic, (LineCollection, ScatterCollection)):
                for g in self._graphic.graphics:
                    g.tooltip_format = partial(self._tooltip_handler, g)

    def _create_heatmap_data(self, data_slice) -> tuple[np.ndarray, float, float]:
        """return [n_rows, n_cols] shape data"""
        # assumes x vals in every row is the same, otherwise a heatmap representation makes no sense
        x = data_slice[0, :, 0]  # get x from just the first row

        # check if we need to interpolate
        norm = np.linalg.norm(np.diff(np.diff(x))) / x.size

        if norm > 1e-6:
            # x is not uniform upto float32 precision, must interpolate
            x_uniform = np.linspace(x[0], x[-1], num=x.size)
            y_interp = np.zeros(shape=data_slice[..., 1].shape, dtype=np.float32)

            # this for loop is actually slightly faster than numpy.apply_along_axis()
            for i in range(data_slice.shape[0]):
                y_interp[i] = np.interp(x_uniform, x, data_slice[i, :, 1])

        else:
            # x is sufficiently uniform
            y_interp = data_slice[..., 1]

        x0 = data_slice[0, 0, 0]

        # assume all x values are the same across all lines
        # otherwise a heatmap representation makes no sense anyways
        x_stop = data_slice[:, -1, 0][0]
        x_scale = (x_stop - x0) / data_slice.shape[1]

        return y_interp, x0, x_scale

    @property
    def display_window(self) -> int | float | None:
        """display window in the reference units for the n_datapoints dim"""
        return self.processor.display_window

    @display_window.setter
    def display_window(self, dw: int | float | None):
        self.processor.display_window = dw
        self.indices = self.indices

    @property
    def x_range_mode(self) -> Literal[None, "fixed-window", "view-range"]:
        """x-range using a fixed window from the display window, or by polling the camera (view-range)"""
        return self._x_range_mode

    @x_range_mode.setter
    def x_range_mode(self, mode: Literal[None, "fixed-window", "view-range"]):
        if self._x_range_mode == "view-range":
            # old mode was view-range
            self.graphic._plot_area.remove_animation(
                self._update_from_view_range
            )

        if mode == "view-range":
            self.graphic._plot_area.add_animations(self._update_from_view_range)

        self._x_range_mode = mode

    def _update_from_view_range(self):
        xr = self.graphic._plot_area.x_range

        # the floating point error near zero gets nasty here
        if np.allclose(xr, self._last_x_range, atol=1e-14):
            return

        self._last_x_range[:] = xr

        self.display_window = xr[1] - xr[0]
        new_index = (xr[0] + xr[1]) / 2

        indices = list(self.indices)
        if indices[-1] == new_index:
            return

        indices[-1] = new_index

        self.indices = indices

