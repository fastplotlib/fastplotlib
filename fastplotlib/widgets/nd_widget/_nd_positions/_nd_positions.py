from collections.abc import Callable, Hashable, Sequence
from functools import partial
from typing import Literal, Any, Type
from warnings import warn

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from numpy.typing import ArrayLike
import xarray as xr

from ....layouts import Subplot
from ....graphics import (
    Graphic,
    ImageGraphic,
    LineGraphic,
    LineStack,
    LineCollection,
    ScatterGraphic,
    ScatterCollection,
    ScatterStack,
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
from .._index import ReferenceIndex

# types for the other features
FeatureCallable = Callable[[np.ndarray, slice], np.ndarray]
ColorsType = np.ndarray | FeatureCallable | None
MarkersType = Sequence[str] | np.ndarray | FeatureCallable | None
SizesType = Sequence[float] | np.ndarray | FeatureCallable | None


def default_cmap_transform_each(p: int, data_slice: np.ndarray, s: slice):
    # create a cmap transform based on the `p` dim size
    n_displayed = data_slice.shape[1]

    # linspace that's just normalized 0 - 1 within `p` dim size
    return np.linspace(
        start=s.start / p,
        stop=s.stop / p,
        num=n_displayed,
        endpoint=False,  # since we use a slice object for the displayed data, the last point isn't included
    )


class NDPositionsProcessor(NDProcessor):
    _other_features = ["colors", "markers", "cmap_transform_each", "sizes"]

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
        colors: ColorsType = None,
        markers: MarkersType = None,
        cmap_transform_each: np.ndarray = None,
        sizes: SizesType = None,
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
        max_display_datapoints: int, default 1_000
            this is approximate since floor division is used to determine the step size of the current display window slice
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
        self.cmap_transform_each = cmap_transform_each
        self.sizes = sizes

    def _check_shape_feature(
        self, prop: str, check_shape: tuple[int, int]
    ) -> tuple[int, int]:
        # this function exists because it's used repeatedly for colors, markers, etc.
        # shape for [l, p] dims must match, or l must be 1
        shape = tuple([self.shape[dim] for dim in self.spatial_dims[:2]])

        if check_shape[1] != shape[1]:
            raise IndexError(
                f"shape of first two dims of {prop} must must be [l, p] or [1, p].\n"
                f"required `p` dim shape is: {shape[1]}, {check_shape[1]} was provided"
            )

        if check_shape[0] != 1 and check_shape[0] != shape[0]:
            raise IndexError(
                f"shape of first two dims of {prop} must must be [l, p] or [1, p]\n"
                f"required `l` dim shape is {shape[0]} | 1, {check_shape[0]} was provided"
            )

        return shape

    @property
    def colors(self) -> ColorsType:
        """
        A callable that dynamically creates colors for the current display window, or array of colors per-datapoint.

        Array must be of shape [l, p, 4] for unique colors per line/scatter, or [1, p, 4] for identical colors per
        line/scatter.

        Callable must return an array of shape [l, pw, 4] or [1, pw, 4], where pw is the number of currently displayed
        datapoints given the current display window. The callable receives the current data slice array, as well as the
        slice object that corresponds to the current display window.
        """
        return self._colors

    @colors.setter
    def colors(self, new):
        if callable(new):
            # custom callable that creates the colors
            self._colors = new
            return

        if new is None:
            self._colors = None
            return

        # as array so we can check shape
        new = np.asarray(new)
        if new.ndim == 2:
            # only [p, 4] provided, broadcast to [1, p, 4]
            new = new[None]

        shape = self._check_shape_feature("colors", new.shape[:2])

        if new.shape[0] == 1:
            # same colors across all graphical elements
            self._colors = parse_colors(new[0], n_colors=shape[1])[None]

        else:
            # colors specified for each individual line/scatter
            new_ = np.zeros(shape=(*self.data.shape[:2], 4), dtype=np.float32)
            for i in range(shape[0]):
                new_[i] = parse_colors(new[i], n_colors=shape[1])

            self._colors = new_

    @property
    def markers(self) -> MarkersType:
        """
        A callable that dynamically creates markers for the current display window, or array of markers per-datapoint.

        Array must be of shape [l, p] for unique markers per line/scatter, or [p,] or [1, p] for identical markers per
        line/scatter.

        Callable must return an array of shape [l, pw], [1, pw], or [pw,] where pw is the number of currently displayed
        datapoints given the current display window. The callable receives the current data slice array, as well as the
        slice object that corresponds to the current display window.
        """
        return self._markers

    @markers.setter
    def markers(self, new: MarkersType):
        if callable(new):
            # custom callable that creates the markers dynamically
            self._markers = new
            return

        if new is None:
            self._markers = None
            return

        # as array so we can check shape
        new = np.asarray(new)

        # if 1-dim, assume it's specifying markers over `p` dim, so set `l` dim to 1
        if new.ndim == 1:
            new = new[None]

        self._check_shape_feature("markers", new.shape[:2])

        self._markers = np.asarray(new)

    @property
    def cmap_transform_each(self) -> np.ndarray | FeatureCallable | None:
        return self._cmap_transform_each

    @cmap_transform_each.setter
    def cmap_transform_each(self, new: np.ndarray | FeatureCallable | None):
        """
        A callable that dynamically creates cmap transforms for the current display window, or array
        of transforms per-datapoint.

        Array must be of shape [l, p] for unique transforms per line/scatter, or [p,] or [1, p] for identical markers
        per line/scatter.

        Callable must return an array of shape [l, pw], [1, pw], or [pw,] where pw is the number of currently displayed
        datapoints given the current display window. The callable receives the current data slice array, as well as the
        slice object that corresponds to the current display window.
        """
        if callable(new):
            self._cmap_transform_each = new
            return

        if new is None:
            self._cmap_transform_each = None
            return

        new = np.asarray(new)

        # if 1-dim, assume it's specifying sizes over `p` dim, set `l` dim to 1
        if new.ndim == 1:
            new = new[None]

        self._check_shape_feature("cmap_transform_each", new.shape)

        self._cmap_transform_each = new

    @property
    def sizes(self) -> SizesType:
        return self._sizes

    @sizes.setter
    def sizes(self, new: SizesType):
        """
        A callable that dynamically creates sizes for the current display window, or array of sizes per-datapoint.

        Array must be of shape [l, p] for unique sizes per line/scatter, or [p,] or [1, p] for identical markers per
        line/scatter.

        Callable must return an array of shape [l, pw], [1, pw], or [pw,] where pw is the number of currently displayed
        datapoints given the current display window. The callable receives the current data slice array, as well as the
        slice object that corresponds to the current display window.
        """
        if callable(new):
            # custom callable
            self._sizes = new
            return

        if new is None:
            self._sizes = None
            return

        new = np.array(new)
        # if 1-dim, assume it's specifying sizes over `p` dim, set `l` dim to 1
        if new.ndim == 1:
            new = new[None]

        self._check_shape_feature("sizes", new.shape)

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
            return slice(0, self.shape[p_dim])

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

    def _apply_dw_window_func(
        self, array: xr.DataArray | np.ndarray
    ) -> xr.DataArray | np.ndarray:
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

    def _apply_spatial_func(
        self, array: xr.DataArray | np.ndarray
    ) -> xr.DataArray | np.ndarray:
        if self.spatial_func is not None:
            return self.spatial_func(array)

        return array

    def _finalize_(self, array: xr.DataArray | np.ndarray) -> xr.DataArray | np.ndarray:
        return self._apply_spatial_func(self._apply_dw_window_func(array))

    def _get_other_features(
        self, data_slice: np.ndarray, dw_slice: slice
    ) -> dict[str, np.ndarray]:
        other = dict.fromkeys(self._other_features)
        for attr in self._other_features:
            val = getattr(self, attr)

            if val is None:
                continue

            if callable(val):
                # if it's a callable, give it the data and display window slice, it must return the appropriate
                # type of array for that graphic feature
                val_sliced = val(data_slice, dw_slice)

            else:
                # if no l dim, broadcast to [1, p]
                if val.ndim == 1:
                    val = val[None]

                # apply current display window slice
                val_sliced = val[:, dw_slice]

            # check if l dim size is 1
            if val_sliced.shape[0] == 1:
                # broadcast across all graphical elements
                n_graphics = self.shape[self.spatial_dims[0]]
                print(val_sliced.shape, n_graphics)
                val_sliced = np.broadcast_to(
                    val_sliced, shape=(n_graphics, *val_sliced.shape[1:])
                )

            other[attr] = val_sliced

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
        ref_index: ReferenceIndex,
        subplot: Subplot,
        data: Any,
        dims: Sequence[str],
        spatial_dims: tuple[str, str, str],
        *args,
        graphic_type: Type[
            LineGraphic
            | LineCollection
            | LineStack
            | ScatterGraphic
            | ScatterCollection
            | ScatterStack
            | ImageGraphic
        ],
        processor: type[NDPositionsProcessor] = NDPositionsProcessor,
        display_window: int = 10,
        window_funcs: tuple[WindowFuncCallable | None] | None = None,
        index_mappings: tuple[Callable[[Any], int] | None] | None = None,
        max_display_datapoints: int = 1_000,
        linear_selector: bool = False,
        x_range_mode: Literal["fixed", "auto"] | None = None,
        colors: (
            Sequence[str] | np.ndarray | Callable[[slice, np.ndarray], np.ndarray]
        ) = None,
        # TODO: cleanup how this cmap stuff works, require a cmap to be set per-graphic
        #  before allowing cmaps_transform, validate that stuff makes sense etc.
        cmap: str = None,  # across the line/scatter collection
        cmap_each: Sequence[str] = None,  # for each individual line/scatter
        cmap_transform_each: np.ndarray = None,  # for each individual line/scatter
        markers: np.ndarray = None,  # across the scatter collection, shape [l,]
        markers_each: Sequence[str] = None,  # for each individual scatter, shape [l, p]
        sizes: np.ndarray = None,  # across the scatter collection, shape [l,]
        sizes_each: Sequence[float] = None,  # for each individual scatter, shape [l, p]
        thickness: np.ndarray = None,  # for each line, shape [l,]
        name: str = None,
        graphic_kwargs: dict = None,
        processor_kwargs: dict = None,
    ):
        super().__init__(subplot, name)

        self._ref_index = ref_index

        if processor_kwargs is None:
            processor_kwargs = dict()

        if graphic_kwargs is None:
            self._graphic_kwargs = dict()
        else:
            self._graphic_kwargs = graphic_kwargs

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
            markers=markers_each,
            cmap_transform_each=cmap_transform_each,
            sizes=sizes_each,
            **processor_kwargs,
        )

        self._cmap = cmap
        self._sizes = sizes
        self._markers = markers
        self._thickness = thickness

        self.cmap_each = cmap_each
        self.cmap_transform_each = cmap_transform_each

        self._graphic_type = graphic_type
        self._create_graphic()

        self._x_range_mode = None
        self.x_range_mode = x_range_mode
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
        | ScatterStack
        | ImageGraphic
        | None
    ):
        """LineStack or ImageGraphic for heatmaps"""
        return self._graphic

    @property
    def graphic_type(
        self,
    ) -> Type[
        LineGraphic
        | LineCollection
        | LineStack
        | ScatterGraphic
        | ScatterCollection
        | ScatterStack
        | ImageGraphic
    ]:
        return self._graphic_type

    @graphic_type.setter
    def graphic_type(self, graphic_type):
        if type(self.graphic) is graphic_type:
            return

        self._subplot.delete_graphic(self._graphic)
        self._graphic_type = graphic_type
        self._create_graphic()

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
        return {d: self._ref_index[d] for d in self.processor.slider_dims}

    @indices.setter
    @block_reentrance
    def indices(self, indices):
        if self.data is None:
            return

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

                if self.cmap_each is not None:
                    match new_features["cmap_transform_each"]:
                        case None:
                            pass
                        case _:
                            setattr(
                                getattr(g, "cmap"),  # ind_graphic.cmap
                                "transform",
                                new_features["cmap_transform_each"],
                            )

        elif isinstance(self.graphic, ImageGraphic):
            image_data, x0, x_scale = self._create_heatmap_data(data_slice)
            self.graphic.data = image_data
            self.graphic.offset = (x0, *self.graphic.offset[1:])
            self.graphic.scale = (x_scale, *self.graphic.scale[1:])

        # x range of the data
        xr = data_slice[0, 0, 0], data_slice[0, -1, 0]
        if self.x_range_mode is not None:
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
            self._ref_index[self.processor.spatial_dims[1]] = ev.info["value"]

    def _tooltip_handler(self, graphic, pick_info):
        if isinstance(self.graphic, (LineCollection, ScatterCollection)):
            # get graphic within the collection
            n_index = np.argwhere(self.graphic.graphics == graphic).item()
            p_index = pick_info["vertex_index"]
            return self.processor.tooltip_format(n_index, p_index)

    def _create_graphic(self):
        if self.data is None:
            return

        new_features = self.processor.get(self.indices)
        data_slice = new_features["data"]

        # store any cmap, sizes, thickness, etc. to assign to new graphic
        graphic_attrs = dict()
        for attr in ["cmap", "markers", "sizes", "thickness"]:
            if attr in new_features.keys():
                if new_features[attr] is not None:
                    # markers and sizes defined for each line via processor takes priority
                    continue

            val = getattr(self, attr)
            if val is not None:
                graphic_attrs[attr] = val

        if issubclass(self._graphic_type, ImageGraphic):
            # `d` dim must only have xy data to be interpreted as a heatmap, xyz can't become a timeseries heatmap
            if self.processor.shape[self.processor.spatial_dims[-1]] != 2:
                raise ValueError

            image_data, x0, x_scale = self._create_heatmap_data(data_slice)
            self._graphic = self._graphic_type(
                image_data, offset=(x0, 0, -1), scale=(x_scale, 1, 1)
            )

        else:
            if issubclass(self._graphic_type, (LineStack, ScatterStack)):
                kwargs = {"separation": 0.0, **self._graphic_kwargs}
            else:
                kwargs = self._graphic_kwargs
            self._graphic = self._graphic_type(data_slice, **kwargs)

        for attr in graphic_attrs.keys():
            if hasattr(self._graphic, attr):
                setattr(self._graphic, attr, graphic_attrs[attr])

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

                if self.cmap_each is not None:
                    g.color_mode = "vertex"
                    g.cmap = self.cmap_each[l]
                    match new_features["cmap_transform_each"]:
                        case None:
                            pass
                        case _:
                            setattr(
                                getattr(g, "cmap"),  # indv_graphic.cmap
                                "transform",
                                new_features["cmap_transform_each"],
                            )

        if self.processor.tooltip:
            if isinstance(self._graphic, (LineCollection, ScatterCollection)):
                for g in self._graphic.graphics:
                    g.tooltip_format = partial(self._tooltip_handler, g)

        self._subplot.add_graphic(self._graphic)

    def _create_heatmap_data(self, data_slice) -> tuple[np.ndarray, float, float]:
        """return [n_rows, n_cols] shape data from [n_timeseries, n_timepoints, xy] data"""
        # assumes x vals in every row is the same, otherwise a heatmap representation makes no sense
        # data slice is of shape [n_timeseries, n_timepoints, xy], where xy is x-y coordinates of each timeseries
        x = data_slice[0, :, 0]  # get x from just the first row

        # check if we need to interpolate
        norm = np.linalg.norm(np.diff(np.diff(x))) / x.size

        if norm > 1e-6:
            # x is not uniform upto float32 precision, must interpolate
            x_uniform = np.linspace(x[0], x[-1], num=x.size)
            y_interp = np.empty(shape=data_slice[..., 1].shape, dtype=np.float32)

            # this for loop is actually slightly faster than numpy.apply_along_axis()
            for i in range(data_slice.shape[0]):
                y_interp[i] = np.interp(x_uniform, x, data_slice[i, :, 1])

        else:
            # x is sufficiently uniform
            y_interp = data_slice[..., 1]

        x0 = data_slice[0, 0, 0]

        # assume all x values are the same across all lines
        # otherwise a heatmap representation makes no sense anyways
        x_stop = x[-1]
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
    def x_range_mode(self) -> Literal["fixed", "auto"] | None:
        """x-range using a fixed window from the display window, or by polling the camera (auto)"""
        return self._x_range_mode

    @x_range_mode.setter
    def x_range_mode(self, mode: Literal[None, "fixed", "auto"]):
        if self._x_range_mode == "auto":
            # old mode was auto
            self._subplot.remove_animation(self._update_from_view_range)

        if mode == "auto":
            self._subplot.add_animations(self._update_from_view_range)

        self._x_range_mode = mode

    def _update_from_view_range(self):
        if self._graphic is None:
            return

        xr = self._subplot.x_range

        # the floating point error near zero gets nasty here
        if np.allclose(xr, self._last_x_range, atol=1e-14):
            return

        last_width = abs(self._last_x_range[1] - self._last_x_range[0])
        self._last_x_range[:] = xr

        new_width = abs(xr[1] - xr[0])
        new_index = (xr[0] + xr[1]) / 2

        if (new_index == self._ref_index[self.processor.spatial_dims[1]]) and (
            last_width == new_width
        ):
            return

        self.processor.display_window = new_width
        # set the `p` dim on the global index vector
        self._ref_index[self.processor.spatial_dims[1]] = new_index

    @property
    def cmap(self) -> str | None:
        return self._cmap

    @cmap.setter
    def cmap(self, new: str | None):
        if new is None:
            # just set a default
            if isinstance(self.graphic, (LineCollection, ScatterCollection)):
                self.graphic.colors = "w"
            else:
                self.graphic.cmap = "plasma"

            self._cmap = None
            return

        self._graphic.cmap = new
        self._cmap = new
        # force a re-render
        self.indices = self.indices

    @property
    def cmap_each(self) -> np.ndarray[str] | None:
        # per-line/scatter
        return self._cmap_each

    @cmap_each.setter
    def cmap_each(self, new: Sequence[str] | None):
        if new is None:
            self._cmap_each = None
            return

        if isinstance(new, str):
            new = [new]

        new = np.asarray(new)

        if new.ndim != 1:
            raise ValueError

        l_dim_size = self.processor.shape[self.processor.spatial_dims[0]]
        # same cmap for all if size == 1, or specific cmap for each in `l` dim
        if new.size != 1 and new.size != l_dim_size:
            raise ValueError

        self._cmap_each = np.broadcast_to(new, shape=(l_dim_size,))

    @property
    def cmap_transform_each(self) -> np.ndarray | None:
        # PER line/scatter, only allowed after `cmaps` is set.
        return self.processor.cmap_transform_each

    @cmap_transform_each.setter
    def cmap_transform_each(self, new: np.ndarray | FeatureCallable | None):
        if new is None:
            self.processor.cmap_transform_each = None

        if self.cmap_each is None:
            self.processor.cmap_transform_each = None
            warn("must set `cmap_each` before `cmap_transform_each`")
            return

        if new is None and self.cmap_each is not None:
            # default transform is just a transform based on the `p` dim size
            new = partial(default_cmap_transform_each, self.shape[self.spatial_dims[1]])

        self.processor.cmap_transform_each = new

    @property
    def markers(self) -> str | Sequence[str] | None:
        return self._markers

    @markers.setter
    def markers(self, new: str | None):
        if not isinstance(self.graphic, ScatterCollection):
            self._markers = None
            return

        if new is None:
            # just set a default
            new = "circle"

        self.graphic.markers = new
        self._markers = new
        # force a re-render
        self.indices = self.indices

    @property
    def sizes(self) -> float | Sequence[float] | None:
        return self._sizes

    @sizes.setter
    def sizes(self, new: float | Sequence[float] | None):
        if not isinstance(self.graphic, ScatterCollection):
            self._sizes = None
            return

        if new is None:
            # just set a default
            new = 5.0

        self.graphic.sizes = new
        self._sizes = new
        # force a re-render
        self.indices = self.indices

    @property
    def thickness(self) -> float | Sequence[float] | None:
        return self._thickness

    @thickness.setter
    def thickness(self, new: float | Sequence[float] | None):
        if not isinstance(self.graphic, LineCollection):
            self._thickness = None
            return

        if new is None:
            # just set a default
            new = 2.0

        self.graphic.thickness = new
        self._thickness = new
        # force a re-render
        self.indices = self.indices
