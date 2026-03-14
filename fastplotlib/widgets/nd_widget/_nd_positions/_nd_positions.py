from collections.abc import Callable, Hashable, Sequence
from functools import partial
from typing import Literal, Any, Type

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from numpy.typing import ArrayLike
import xarray as xr

from ....graphics import (
    Graphic,
    ImageGraphic,
    LineGraphic,
    LineStack,
    LineCollection,
    ScatterGraphic,
    ScatterCollection,
)
from ....graphics.features.utils import parse_colors
from ....graphics.utils import pause_events
from ....graphics.selectors import LinearSelector
from .._base import (
    NDProcessor,
    NDGraphic,
    WindowFuncCallable,
    block_reentrance,
    block_indices,
)
from .._index import GlobalIndex


# TODO: Maybe get rid of n_display_dims in NDProcessor,
#  we will know the display dims automatically here from the last dim
#  so maybe we only need it for images?
class NDPositionsProcessor(NDProcessor):
    _other_features = ["colors", "markers", "cmaps_transforms", "alphas", "sizes"]

    def __init__(
        self,
        data: Any,
        dims: Sequence[Hashable],
        # TODO: allow stack_dim to be None and auto-add new dim of size 1 in get logic
        spatial_dims: tuple[
            Hashable | None, Hashable, Hashable
        ],  # [stack_dim, n_datapoints, spatial_dim], IN ORDER!!
        index_mappings: dict[str, Callable[[Any], int] | ArrayLike] = None,
        display_window: int | float | None = 100,  # window for n_datapoints dim only
        max_display_datapoints: int = 1_000,
        datapoints_window_func: tuple[Callable, str, int | float] | None = None,
        colors: Sequence[str] | np.ndarray = None,
        markers: Sequence[str] | np.ndarray = None,
        cmaps_transforms: np.ndarray = None,
        alpha: np.ndarray = None,
        sizes: Sequence[float] = None,
        **kwargs,
    ):
        """

        Parameters
        ----------
        data
        dims
        spatial_dims
        index_mappings
        display_window
        max_display_datapoints
        datapoints_window_func:
            Important note: if used, display_window is approximate and not exact due to padding from the window size
        kwargs
        """
        self._display_window = display_window
        self._max_display_datapoints = max_display_datapoints

        super().__init__(
            data=data,
            dims=dims,
            spatial_dims=spatial_dims,
            index_mappings=index_mappings,
            **kwargs,
        )

        self._datapoints_window_func = datapoints_window_func

        self.colors = colors
        self.markers = markers
        self.cmaps_transforms = cmaps_transforms
        self.alphas = alpha
        self.sizes = sizes

    def _check_get_datapoints_dim_size(self, check_prop: str, check_shape: int) -> tuple[int, int]:
        # this function exists because it's used repeatedly for colors, markers, etc.
        # shape for [l, p] dims must match, or l must be 1
        shape = tuple([self.shape[dim] for dim in self.spatial_dims[:2]])

        if check_shape[0] != 1 and check_shape != shape:
            raise IndexError(
                f"Number of {check_prop} must match the size of the datapoints dim in the data"
            )

        return shape

    @property
    def colors(self) -> np.ndarray | None | Callable:
        return self._colors

    @colors.setter
    def colors(self, new):
        if callable(new):
            self._colors = new
            return

        if new is None:
            self._colors = None
            return

        n = self._check_get_datapoints_dim_size("colors", new.shape)
        self._colors = parse_colors(new, n_colors=n)

    @property
    def markers(self) -> np.ndarray | None:
        return self._markers

    @markers.setter
    def markers(self, new: Sequence[str] | None):
        if new is None:
            self._markers = None
            return

        self._check_get_datapoints_dim_size("markers", len(new))
        self._markers = np.asarray(new)

    @property
    def cmaps_transforms(self) -> Sequence[str] | None:
        return self._cmaps_transforms

    @cmaps_transforms.setter
    def cmaps_transforms(self, new: Sequence[str] | None):
        if new is None:
            self._cmaps_transforms = None
            return

        self._check_get_datapoints_dim_size("markers", len(new))
        self._cmap_transforms = np.asarray(new)

    @property
    def alphas(self) -> np.ndarray | None:
        return self._alphas

    @alphas.setter
    def alphas(self, new: Sequence[float] | None):
        if new is None:
            self._alphas = None
            return

        self._check_get_datapoints_dim_size("alphas", len(new))
        alphas = np.asarray(new)

        self._alphas = alphas

    @property
    def sizes(self) -> np.ndarray | None:
        return self._sizes

    @sizes.setter
    def sizes(self, new: Sequence[float] | None):
        if new is None:
            self._sizes = None
            return

        self._check_get_datapoints_dim_size("alphas", len(new))
        new = np.array(new)

        if new.ndim != 1:
            raise ValueError

        self._sizes = new

    @property
    def spatial_dims(self) -> tuple[str, str, str]:
        return self._spatial_dims

    @spatial_dims.setter
    def spatial_dims(self, sdims: tuple[str, str, str]):
        if len(sdims) != 3:
            raise IndexError

        if not all([d in self.dims for d in sdims]):
            raise KeyError

        self._spatial_dims = tuple(sdims)

    @property
    def slider_dims(self) -> set[Hashable]:
        # append `p` dim to slider dims
        return tuple([*super().slider_dims, self.spatial_dims[1]])

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

    # TODO: validation for datapoints_window_func and size
    @property
    def datapoints_window_func(self) -> tuple[Callable, str, int | float] | None:
        """
        Callable, str indicating which dims to apply window function along, window_size in reference space:
            'all', 'x', 'y', 'z', 'xyz', 'xy', 'xz', 'yz'
        '"""
        return self._datapoints_window_func

    @datapoints_window_func.setter
    def datapoints_window_func(self, funcs: tuple[Callable, str, int | float]):
        if len(funcs) != 3:
            raise TypeError

        self._datapoints_window_func = tuple(funcs)

    def _get_dw_slice(self, indices: dict[str, Any]) -> slice:
        # given indices, return slice required to obtain display window

        # n_datapoints dim name
        # display_window acts on this dim
        p_dim = self.spatial_dims[1]

        if self.display_window is None:
            # just return everything
            return slice(0, self.shape[p_dim] - 1)

        if self.display_window == 0:
            # just map p dimension at this index and return
            index = self._ref_index_to_array_index(p_dim, indices[p_dim])
            return slice(index, index + 1)

        # half window size, in reference units
        hw = self.display_window / 2

        if self.datapoints_window_func is not None:
            # add half datapoints_window_func size here, assumes the reference space is somewhat continuous
            # and the display_window and datapoints window size map to their actual size values
            hw += self.datapoints_window_func[2] / 2

        # display window is in reference units, apply display window and then map to array indices
        # start in reference units
        start_ref = indices[p_dim] - hw
        # stop in reference units
        stop_ref = indices[p_dim] + hw

        # map to array indices
        start = self._ref_index_to_array_index(p_dim, start_ref)
        stop = self._ref_index_to_array_index(p_dim, stop_ref)

        if start >= stop:
            stop = start + 1

        w = stop - start

        # get step size
        step = max(1, w // self.max_display_datapoints)

        return slice(start, stop, step)

    def _apply_dw_window_func(self, array: xr.DataArray | np.ndarray) -> xr.DataArray | np.ndarray:
        """
        Takes array where display window has already been applied and applies window functions on the `p` dim.

        Parameters
        ----------
        array: np.ndarray
            array of shape: [l, display_window, 2 | 3]

        Returns
        -------
        np.ndarray
            array with window functions applied along `p` dim
        """
        if self.display_window == 0:
            # can't apply window func when there is only 1 datapoint
            return array

        p_dim = self.spatial_dims[1]

        # display window in array index space
        if self.display_window is not None:
            dw = self.index_mappings[p_dim](self.display_window)

            # step size based on max number of datapoints to render
            step = max(1, dw // self.max_display_datapoints)

            # apply window function on the `p` n_datapoints dim
            if (
                self.datapoints_window_func is not None
                # if there are too many points to efficiently compute the window func, skip
                # applying a window func also requires making a copy so that's a further performance hit
                and (dw < self.max_display_datapoints * 2)
            ):
                # get windows

                # graphic_data will be of shape: [n, p, 2 | 3]
                # where:
                #   n - number of lines, scatters, heatmap rows
                #   p - number of datapoints/samples

                # ws is in ref units
                wf, apply_dims, ws = self.datapoints_window_func

                # map ws in ref units to array index
                # min window size is 3
                ws = max(self._ref_index_to_array_index(p_dim, ws), 3)

                if ws % 2 == 0:
                    # odd size windows are easier to handle
                    ws += 1

                hw = ws // 2
                start, stop = hw, array.shape[1] - hw

                # apply user's window func
                # result will be of shape [n, p, 2 | 3]
                if apply_dims == "all":
                    # windows will be of shape [n, p, 1 | 2 | 3, ws]
                    windows = sliding_window_view(array, ws, axis=-2)
                    return wf(windows, axis=-1)[:, ::step]

                # map user dims str to tuple of numerical dims
                dims = tuple(map({"x": 0, "y": 1, "z": 2}.get, apply_dims))

                # windows will be of shape [n, (p - ws + 1), 1 | 2 | 3, ws]
                windows = sliding_window_view(array[..., dims], ws, axis=-2).squeeze()

                # make a copy because we need to modify it
                array = array[:, start:stop].copy()

                # this reshape is required to reshape wf outputs of shape [n, p] -> [n, p, 1] only when necessary
                array[..., dims] = wf(windows, axis=-1).reshape(
                    *array.shape[:-1], len(dims)
                )

                return array[:, ::step]

        step = max(1, array.shape[1] // self.max_display_datapoints)

        return array[:, ::step]

    def _apply_spatial_func(self, array: xr.DataArray | np.ndarray) -> xr.DataArray | np.ndarray:
        if self.spatial_func is not None:
            return self.spatial_func(array)

        return array

    def _finalize_(self, array: xr.DataArray | np.ndarray) -> xr.DataArray | np.ndarray:
        return self._apply_spatial_func(self._apply_dw_window_func(array))

    def _get_other_features(self, data_slice: np.ndarray, dw_slice: slice) -> dict[str, np.ndarray]:
        other = dict.fromkeys(self._other_features)
        for attr in self._other_features:
            val = getattr(self, attr)

            if callable(val):
                # if it's a callable, give it the data and display window slice, it must return the appropriate
                # type of array for that graphic feature
                val = val(data_slice, dw_slice)

            match val:
                case None:
                    other[attr] = None

                case _:
                    other[attr] = val[dw_slice]

        return other

    def get(self, indices: dict[str, Any]) -> dict[str, np.ndarray]:
        """
        slices through all slider dims and outputs an array that can be used to set graphic data

        Note that we do not use __getitem__ here since the index is a tuple specifying a single integer
        index for each dimension. Slices are not allowed, therefore __getitem__ is not suitable here.
        """

        if len(self.slider_dims) > 1:
            # there are slider dims in addition to the datapoints_dim
            window_output = self._apply_window_functions(indices).squeeze()
        else:
            # no slider dims, use all the data
            window_output = self.data

        # verify window output only has the spatial dims
        if not set(window_output.dims) == set(self.spatial_dims):
            raise IndexError

        # get slice obj for display window
        dw_slice = self._get_dw_slice(indices)

        # data that will be used for the graphical representation
        # a copy is made, if there were no window functions then this is a view of the original data
        p_dim = self.spatial_dims[1]

        # slice the datapoints to be displayed in the graphic using the display window slice
        # transpose to match spatial dims order, get numpy array, this is a view
        graphic_data = window_output.isel({p_dim: dw_slice}).transpose(
            *self.spatial_dims
        )

        data = self._finalize_(graphic_data).values
        other = self._get_other_features(data, dw_slice)

        return {
            "data": data,
            **other,
        }


class NDPositions(NDGraphic):
    def __init__(
        self,
        global_index: GlobalIndex,
        data: Any,
        dims: Sequence[str],
        spatial_dims: tuple[str, str, str],
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
        display_window: int = 10,
        window_funcs: tuple[WindowFuncCallable | None] | None = None,
        index_mappings: tuple[Callable[[Any], int] | None] | None = None,
        max_display_datapoints: int = 1_000,
        linear_selector: bool = False,
        colors: Sequence[str] | np.ndarray | Callable[[slice, np.ndarray], np.ndarray] = None,
        # TODO: cleanup how this cmap stuff works, require a cmap to be set per-graphic
        #  before allowing cmaps_transform, validate that stuff makes sense etc.
        cmap: str = None,  # across the line/scatter collection
        cmaps: Sequence[str] = None,  # for each individual line/scatter
        cmaps_transforms: np.ndarray = None,  # for each individual line/scatter
        markers: Sequence[str] = None,
        sizes: Sequence[float] = None,
        alpha: Sequence[float] = None,
        name: str = None,
        graphic_kwargs: dict = None,
        processor_kwargs: dict = None,
    ):
        self._global_index = global_index

        if processor_kwargs is None:
            processor_kwargs = dict()

        if graphic_kwargs is None:
            self._graphic_kwargs = dict()

        self._processor = processor(
            data,
            dims,
            spatial_dims,
            *args,
            display_window=display_window,
            max_display_datapoints=max_display_datapoints,
            window_funcs=window_funcs,
            index_mappings=index_mappings,
            colors=colors,
            markers=markers,
            cmaps_transforms=cmaps_transforms,
            alpha=alpha,
            sizes=sizes,
            **processor_kwargs,
        )

        self._processor.p_max = 1_000

        self._create_graphic(graphic)

        self._x_range_mode = None
        self._last_x_range = np.array([0.0, 0.0], dtype=np.float32)

        if linear_selector:
            self._linear_selector = LinearSelector(
                0, limits=(-np.inf, np.inf), edge_color="cyan"
            )
            self._linear_selector.add_event_handler(
                self._linear_selector_handler, "selection"
            )
        else:
            self._linear_selector = None

        self._pause = False

        super().__init__(name)

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
    def cmap(self) -> str | None:
        # across all lines/scatters, or heatmap cmap
        pass

    @property
    def cmaps(self) -> np.ndarray[str] | None:
        # per-line/scatter
        pass

    @property
    def cmaps_transforms(self) -> np.ndarray | None:
        # PER line/scatter, only allowed after `cmaps` is set.
        pass

    @property
    def spatial_dims(self) -> tuple[str, str, str]:
        return self.processor.spatial_dims

    @spatial_dims.setter
    def spatial_dims(self, dims: tuple[str, str, str]):
        self.processor.spatial_dims = dims
        # force re-render
        self.indices = self.indices

    @property
    def indices(self) -> dict[Hashable, Any]:
        return {d: self._global_index[d] for d in self.processor.slider_dims}

    @indices.setter
    @block_reentrance
    def indices(self, indices):
        new_features = self.processor.get(indices)
        data_slice = new_features["data"]

        # TODO: set other graphic features, colors, sizes, markers, etc.

        if isinstance(self.graphic, (LineGraphic, ScatterGraphic)):
            self.graphic.data[:, : data_slice.shape[-1]] = data_slice

        elif isinstance(self.graphic, (LineCollection, ScatterCollection)):
            for l, g in enumerate(self.graphic.graphics):
                new_data = data_slice[l]
                if g.data.value.shape[0] != new_data.shape[0]:
                    # will replace buffer internally
                    g.data = new_data
                else:
                    # if data are only xy, set only xy
                    g.data[:, : new_data.shape[1]] = new_data

                for feature in ["colors", "sizes", "markers"]:
                    value = new_features[feature]

                    match value:
                        case None:
                            pass
                        case _:
                            if feature == "colors":
                                g.color_mode = "vertex"

                            setattr(g, feature, value[l])

                if self.cmaps is not None:
                    match new_features["cmaps_transforms"]:
                        case None:
                            pass
                        case _:
                            setattr(
                                getattr(g, "cmap"),  # indv_graphic.cmap
                                "transform",
                                new_features["cmaps_transforms"],
                            )

        elif isinstance(self.graphic, ImageGraphic):
            image_data, x0, x_scale = self._create_heatmap_data(data_slice)
            self.graphic.data = image_data
            self.graphic.offset = (x0, *self.graphic.offset[1:])
            self.graphic.scale = (x_scale, *self.graphic.scale[1:])

        # x range of the data
        xr = data_slice[0, 0, 0], data_slice[0, -1, 0]
        if self._x_range_mode is not None:
            self.graphic._plot_area.x_range = xr

        # if the update_from_view is polling, this prevents it from being called by setting the new last xrange
        # in theory, but this doesn't seem to fully work yet, not a big deal right now can check later
        self._last_x_range[:] = self.graphic._plot_area.x_range

        if self._linear_selector is not None:
            with pause_events(self._linear_selector):
                self._linear_selector.limits = xr
                # linear selector acts on `p` dim
                self._linear_selector.selection = indices[
                    self.processor.spatial_dims[1]
                ]

    def _linear_selector_handler(self, ev):
        with block_indices(self):
            # linear selector always acts on the `p` dim
            self._global_index[self.processor.spatial_dims[1]] = ev.info["value"]

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

        new_features = self.processor.get(self.indices)
        data_slice = new_features["data"]

        if issubclass(graphic_cls, ImageGraphic):
            # `d` dim must only have xy data to be interpreted as a heatmap, xyz can't become a timeseries heatmap
            if self.processor.shape[self.processor.spatial_dims[-1]] != 2:
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

        if isinstance(self._graphic, (LineCollection, ScatterCollection)):
            for l, g in enumerate(self.graphic.graphics):
                for feature in ["colors", "sizes", "markers"]:
                    value = new_features[feature]

                    match value:
                        case None:
                            pass
                        case _:
                            if feature == "colors":
                                g.color_mode = "vertex"

                            setattr(g, feature, value[l])

                if self.cmaps is not None:
                    match new_features["cmaps_transforms"]:
                        case None:
                            pass
                        case _:
                            setattr(
                                getattr(g, "cmap"),  # indv_graphic.cmap
                                "transform",
                                new_features["cmaps_transforms"],
                            )

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

        # force re-render
        self.indices = self.indices

    @property
    def datapoints_window_func(self) -> tuple[Callable, str, int | float] | None:
        """
        Callable, str indicating which dims to apply window function along, window_size in reference space:
            'all', 'x', 'y', 'z', 'xyz', 'xy', 'xz', 'yz'
        '"""
        return self.processor.datapoints_window_func

    @datapoints_window_func.setter
    def datapoints_window_func(self, funcs: tuple[Callable, str, int | float]):
        self.processor.datapoints_window_func = funcs

    @property
    def x_range_mode(self) -> Literal[None, "fixed-window", "view-range"]:
        """x-range using a fixed window from the display window, or by polling the camera (view-range)"""
        return self._x_range_mode

    @x_range_mode.setter
    def x_range_mode(self, mode: Literal[None, "fixed-window", "view-range"]):
        if self._x_range_mode == "view-range":
            # old mode was view-range
            self.graphic._plot_area.remove_animation(self._update_from_view_range)

        if mode == "view-range":
            self.graphic._plot_area.add_animations(self._update_from_view_range)

        self._x_range_mode = mode

    def _update_from_view_range(self):
        xr = self.graphic._plot_area.x_range

        # the floating point error near zero gets nasty here
        if np.allclose(xr, self._last_x_range, atol=1e-14):
            return

        last_width = abs(self._last_x_range[1] - self._last_x_range[0])
        self._last_x_range[:] = xr

        new_width = abs(xr[1] - xr[0])
        new_index = (xr[0] + xr[1]) / 2

        if (new_index == self._global_index[self.processor.spatial_dims[1]]) and (
            last_width == new_width
        ):
            return

        self.processor.display_window = new_width
        # set the `p` dim on the global index vector
        self._global_index[self.processor.spatial_dims[1]] = new_index
