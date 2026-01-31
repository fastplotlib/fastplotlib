import inspect
from typing import Literal, Callable, Any, Type
from warnings import warn

import numpy as np
from numpy.typing import ArrayLike

from ...utils import subsample_array, ArrayProtocol

from ...graphics import (
    ImageGraphic,
    LineGraphic,
    LineStack,
    LineCollection,
    ScatterGraphic,
    ScatterCollection,
)
from ._processor_base import NDProcessor


# TODO: Maybe get rid of n_display_dims in NDProcessor,
#  we will know the display dims automatically here from the last dim
#  so maybe we only need it for images?
class NDPositionsProcessor(NDProcessor):
    def __init__(
        self,
        data: ArrayProtocol,
        multi: bool = False,  # TODO: interpret [n - 2] dimension as n_lines or n_points
        display_window: int | float | None = 100,  # window for n_datapoints dim only
        n_slider_dims: int = 0,
    ):
        super().__init__(data=data)

        self._display_window = display_window

        self.multi = multi

        self.n_slider_dims = n_slider_dims

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

    def _apply_window_functions(self, indices: tuple[int, ...]):
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

    def get(self, indices: tuple[Any, ...]):
        """
        slices through all slider dims and outputs an array that can be used to set graphic data

        Note that we do not use __getitem__ here since the index is a tuple specifying a single integer
        index for each dimension. Slices are not allowed, therefore __getitem__ is not suitable here.
        """
        if len(indices) > 1:
            # there are dims in addition to the n_datapoints dim
            # apply window funcs
            # window_output array should be of shape [n_datapoints, 2 | 3]
            window_output = self._apply_window_functions(indices[:-1]).squeeze()
        else:
            window_output = self.data

        # TODO: window function on the `p` n_datapoints dimension

        if self.display_window is not None:
            dw = self.display_window

            if dw == 1:
                slices = [slice(indices[-1], indices[-1] + 1)]

            else:
                # half window size
                hw = dw // 2

                # for now assume just a single index provided that indicates x axis value
                start = max(indices[-1] - hw, 0)
                stop = start + dw

                # TODO: uncomment this once we have resizeable buffers!!
                # stop = min(indices[-1] + hw, self.shape[-2])

                slices = [slice(start, stop)]

            if self.multi:
                # n - 2 dim is n_lines or n_scatters
                slices.insert(0, slice(None))

            return window_output[tuple(slices)]


class NDPositions:
    def __init__(
        self,
        data,
        graphic: Type[LineGraphic | LineCollection | LineStack | ScatterGraphic | ScatterCollection | ImageGraphic],
        multi: bool = False,
        display_window: int = 10,
    ):
        if issubclass(graphic, LineCollection):
            multi = True

        self._processor = NDPositionsProcessor(data, multi=multi, display_window=display_window, n_slider_dims=0)
        self._indices = tuple([0] * (0 + 1))

        self._create_graphic(graphic)

    @property
    def processor(self) -> NDPositionsProcessor:
        return self._processor

    @property
    def graphic(
        self,
    ) -> (
        LineGraphic | LineCollection | LineStack | ScatterGraphic | ScatterCollection | ImageGraphic
    ):
        """LineStack or ImageGraphic for heatmaps"""
        return self._graphic

    @graphic.setter
    def graphic(self, graphic_type):
        if isinstance(self.graphic, graphic_type):
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
        data_slice = self.processor.get(indices)

        if isinstance(self.graphic, (LineGraphic, ScatterGraphic)):
            self.graphic.data[:, : data_slice.shape[-1]] = data_slice

        elif isinstance(self.graphic, (LineCollection, ScatterCollection)):
            for i in range(len(self.graphic)):
                # data_slice shape is [n_lines, n_datapoints, 2 | 3]
                self.graphic[i].data[:, : data_slice.shape[-1]] = data_slice[i]

        elif isinstance(self.graphic, ImageGraphic):
            image_data, x0, x_scale = self._create_heatmap_data(data_slice)
            self.graphic.data = image_data
            self.graphic.offset = (x0, *self.graphic.offset[1:])

    def _create_graphic(
        self,
        graphic_cls: Type[LineGraphic | LineCollection | LineStack | ScatterGraphic | ScatterCollection | ImageGraphic],
    ):
        data_slice = self.processor.get(self.indices)

        if issubclass(graphic_cls, ImageGraphic):
            if not self.processor.multi:
                raise ValueError

            if self.processor.data.shape[-1] != 2:
                raise ValueError

            image_data, x0, x_scale = self._create_heatmap_data(data_slice)
            self._graphic = graphic_cls(image_data, offset=(x0, 0, -1), scale=(x_scale, 1, 1))

        else:
            self._graphic = graphic_cls(data_slice)

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

        # assume all x values are the same
        x_scale = data_slice[:, -1, 0][0] / data_slice.shape[1]

        x0 = data_slice[0, 0, 0]

        return y_interp, x0, x_scale
