import inspect
from typing import Literal, Callable, Any
from warnings import warn

import numpy as np
from numpy.typing import ArrayLike

from ...graphics import ImageGraphic, LineStack, LineCollection, ScatterGraphic
from ...utils import subsample_array, ArrayProtocol


# must take arguments: array-like, `axis`: int, `keepdims`: bool
WindowFuncCallable = Callable[[ArrayLike, int, bool], ArrayLike]


class NDProcessor:
    def __init__(
        self,
        data,
        n_display_dims: Literal[2, 3] = 2,
        slider_index_maps: tuple[Callable[[Any], int] | None, ...] | None = None,
        window_funcs: tuple[WindowFuncCallable | None] | None = None,
        window_sizes: tuple[int | None] | None = None,
        spatial_func: Callable[[ArrayProtocol], ArrayProtocol] | None = None,
    ):
        self._data = self._validate_data(data)
        self._slider_index_maps = self._validate_slider_index_maps(slider_index_maps)

    @property
    def data(self) -> ArrayProtocol:
        return self._data

    @data.setter
    def data(self, data: ArrayProtocol):
        self._data = self._validate_data(data)

    def _validate_data(self, data: ArrayProtocol):
        if not isinstance(data, ArrayProtocol):
            raise TypeError("`data` must implement the ArrayProtocol")

        return data

    @property
    def window_funcs(self) -> tuple[WindowFuncCallable | None] | None:
        pass

    @property
    def window_sizes(self) -> tuple[int | None] | None:
        pass

    @property
    def spatial_func(self) -> Callable[[ArrayProtocol], ArrayProtocol] | None:
        pass

    @property
    def slider_dims(self) -> tuple[int, ...] | None:
        pass

    @property
    def slider_index_maps(self) -> tuple[Callable[[Any], int] | None, ...]:
        return self._slider_index_maps

    @slider_index_maps.setter
    def slider_index_maps(self, maps):
        self._maps = self._validate_slider_index_maps(maps)

    def _validate_slider_index_maps(self, maps):
        if maps is not None:
            if not all([callable(m) or m is None for m in maps]):
                raise TypeError

        return maps

    def __getitem__(self, item: tuple[Any, ...]) -> ArrayProtocol:
        pass


class NDImageProcessor(NDProcessor):
    @property
    def n_display_dims(self) -> Literal[2, 3]:
        pass

    def _validate_n_display_dims(self, n_display_dims):
        if n_display_dims not in (2, 3):
            raise ValueError("`n_display_dims` must be")


VALID_TIMESERIES_Y_DATA_SHAPES = (
    "[n_datapoints] for 1D array of y-values, [n_datapoints, 2] "
    "for a 1D array of y and z-values, [n_lines, n_datapoints] for a 2D stack of lines with y-values, "
    "or [n_lines, n_datapoints, 2] for a stack of lines with y and z-values."
)


# Limitation, no heatmap if z-values present, I don't think you can visualize that
class NDTimeSeriesProcessor(NDProcessor):
    def __init__(
        self,
        data: list[
            ArrayProtocol, ArrayProtocol
        ],  # list: [x_vals_array, y_vals_and_z_vals_array]
        x_values: ArrayProtocol = None,
        cmap: str = None,
        cmap_transform: ArrayProtocol = None,
        display_graphic: Literal["line", "heatmap"] = "line",
        n_display_dims: Literal[2, 3] = 2,
        slider_index_maps: tuple[Callable[[Any], int] | None, ...] | None = None,
        display_window: int | float | None = 100,
        window_funcs: tuple[WindowFuncCallable | None] | None = None,
        window_sizes: tuple[int | None] | None = None,
        spatial_func: Callable[[ArrayProtocol], ArrayProtocol] | None = None,
    ):
        super().__init__(
            data=data,
            n_display_dims=n_display_dims,
            slider_index_maps=slider_index_maps,
        )

        self._display_window = display_window

        self._display_graphic = None
        self.display_graphic = display_graphic

        self._uniform_x_values: ArrayProtocol | None = None
        self._interp_yz: ArrayProtocol | None = None

    @property
    def data(self) -> list[ArrayProtocol, ArrayProtocol]:
        return self._data

    @data.setter
    def data(self, data: list[ArrayProtocol, ArrayProtocol]):
        self._data = self._validate_data(data)

    def _validate_data(self, data: list[ArrayProtocol, ArrayProtocol]):
        x_vals, yz_vals = data

        if x_vals.ndim != 1:
            raise ("data x values must be 1D")

        if data[1].ndim > 3:
            raise ValueError(
                f"data yz values must be of shape: {VALID_TIMESERIES_Y_DATA_SHAPES}. You passed data of shape: {yz_vals.shape}"
            )

        return data

    @property
    def display_graphic(self) -> Literal["line", "heatmap"]:
        return self._display_graphic

    @display_graphic.setter
    def display_graphic(self, dg: Literal["line", "heatmap"]):
        dg = self._validate_display_graphic(dg)

        if dg == "heatmap":
            # check if x-vals uniformly spaced
            # this is very fast to do on the fly, especially for typical small display windows
            norm = np.linalg.norm(np.diff(np.diff(self.x_values))) / len(self.x_values)
            if norm > 10 ** -12:
                # need to create evenly spaced x-values
                x0 = self.data[0][0]
                xn = self.data[0][-1]
                self._uniform_x_values = np.linspace(x0, xn, num=len(self.data[0]))

                # TODO: interpolate yz values on the fly only when within the display window

    def _validate_display_graphic(self, dg):
        if dg not in ("line", "heatmap"):
            raise ValueError

        return dg

    @property
    def display_window(self) -> int | float | None:
        """display window in the reference units along the x-axis"""
        return self._display_window

    @display_window.setter
    def display_window(self, dw: int | float | None):
        if dw is None:
            self._display_window = None

        elif not isinstance(dw, (int, float)):
            raise TypeError

        self._display_window = dw

    def __getitem__(self, indices: tuple[Any, ...]) -> ArrayProtocol:
        if self.display_window is not None:
            # map reference units -> array int indices if necessary
            if self.slider_index_maps is not None:
                indices_window = self.slider_index_maps(self.display_window)
            else:
                indices_window = self.display_window

            # half window size
            hw = indices_window // 2

            # for now assume just a single index provided that indicates x axis value
            start = max(indices - hw, 0)
            stop = start + indices_window

            # slice dim would be ndim - 1
            return self.data[0][start:stop], self.data[1][:, start:stop]


class NDTimeSeries:
    def __init__(self, processor: NDTimeSeriesProcessor, graphic):
        self._processor = processor

        self._indices = 0

        if graphic == "line":
            self._create_line_stack()
        elif graphic == "heatmap":
            self._create_heatmap()
        else:
            raise ValueError

    @property
    def processor(self) -> NDTimeSeriesProcessor:
        return self._processor

    @property
    def graphic(self) -> LineStack | ImageGraphic:
        """LineStack or ImageGraphic for heatmaps"""
        return self._graphic

    @graphic.setter
    def graphic(self, g: Literal["line", "heatmap"]):
        if g == "line":
            # TODO: remove existing graphic
            self._create_line_stack()

        elif g == "heatmap":
            # make sure "yz" data is only ys and no z values
            # can't represent y and z vals in a heatmap
            if self.processor.data[1].ndim > 2:
                raise ValueError("Only y-values are supported for heatmaps, not yz-values")
            self._create_heatmap()

    @property
    def display_window(self) ->  int | float | None:
        return self.processor.display_window

    @display_window.setter
    def display_window(self, dw:  int | float | None):
        # create new graphic if it changed
        if dw != self.display_window:
            create_new_graphic = True
        else:
            create_new_graphic = False

        self.processor.display_window = dw

        if create_new_graphic:
            if isinstance(self.graphic, LineStack):
                self.set_index(self._indices)

    def set_index(self, indices: tuple[Any, ...]):
        # set the graphic at the given data indices
        data_slice = self.processor[indices]

        if isinstance(self.graphic, LineStack):
            line_stack_data = self._create_line_stack_data(data_slice)

            for g, line_data in zip(self.graphic.graphics, line_stack_data):
                if line_data.shape[1] == 2:
                    # only x and y values
                    g.data[:, :-1] = line_data
                else:
                    # has z values too
                    g.data[:] = line_data

        elif isinstance(self.graphic, ImageGraphic):
            hm_data, scale = self._create_heatmap_data(data_slice)
            self.graphic.data = hm_data

        self._indices = indices

    def _create_line_stack_data(self, data_slice):
        xs = data_slice[0]  # 1D
        yz = data_slice[1]  # [n_lines, n_datapoints] for y-vals or [n_lines, n_datapoints, 2] for yz-vals

        # need to go from x_vals and yz_vals arrays to an array of shape: [n_lines, n_datapoints, 2 | 3]
        return np.dstack([np.repeat(xs[None], repeats=yz.shape[0], axis=0), yz])

    def _create_line_stack(self):
        data_slice = self.processor[self._indices]

        ls_data = self._create_line_stack_data(data_slice)

        self._graphic = LineStack(ls_data)

    def _create_heatmap_data(self, data_slice) -> tuple[ArrayProtocol, float]:
        """Returns [n_lines, y_values] array and scale factor for x dimension"""
        # check if x-vals uniformly spaced
        # this is very fast to do on the fly, especially for typical small display windows
        x, y = data_slice
        norm = np.linalg.norm(np.diff(np.diff(x))) / x.size
        if norm > 10 ** -12:
            # need to create evenly spaced x-values
            x_uniform = np.linspace(x[0], x[-1], num=x.size)
            # yz is [n_lines, n_datapoints]
            y_interp = np.zeros(shape=y.shape, dtype=np.float32)
            for i in range(y.shape[0]):
                y_interp[i] = np.interp(x_uniform, x, y[i])

        else:
            y_interp = y

        x_scale = x[-1] / x.size

        return y_interp, x_scale

    def _create_heatmap(self):
        data_slice = self.processor[self._indices]

        hm_data, x_scale = self._create_heatmap_data(data_slice)

        self._graphic = ImageGraphic(hm_data)
        self._graphic.world_object.world.scale_x = x_scale