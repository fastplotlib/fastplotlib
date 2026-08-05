from __future__ import annotations

from collections.abc import Callable, Hashable, Sequence
from functools import partial
from typing import Any, Type, TYPE_CHECKING
from warnings import warn

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from numpy.typing import ArrayLike

from ....graphics import (
    LineGraphic,
    LineStack,
    LineCollection,
    ScatterGraphic,
    ScatterCollection,
    ScatterStack,
)
from ....graphics.features.utils import parse_colors
from .._base import (
    NDProcessor,
    NDGraphic,
    WindowFuncCallable,
)
from ....utils import ArrayProtocol, CudaArrayProtocol, cuda_to_numpy
from .._index import ReferenceIndex
from .._async import run_in_thread_pool, run_sync

if TYPE_CHECKING:
    from .._ndw_subplot import NDWSubplot

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
        dims: Sequence[str],
        # TODO: allow stack_dim to be None and auto-add new dim of size 1 in get logic
        spatial_dims: tuple[
            str | None, str, str
        ],  # [stack_dim, n_datapoints, spatial_dim], IN ORDER!!
        slider_dim_transforms: dict[str, Callable[[Any], int] | ArrayLike] = None,
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
        ``NDProcessor`` subclass for n-dimensional positional and timeseries data.


        The *datapoints* dimension is
        simultaneously a slider dim and a spatial dim and is handled by a dedicated
        :attr:`datapoints_window_func` rather than the general ``window_funcs``
        mechanism.


        Parameters
        ----------
        data
        dims
        spatial_dims
        slider_dim_transforms
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
            slider_dim_transforms=slider_dim_transforms,
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
        """get or set the spatial dims, **in display order**"""
        return self._spatial_dims

    @spatial_dims.setter
    def spatial_dims(self, sdims: tuple[str, str, str]):
        if len(sdims) != 3:
            raise IndexError

        if not all([d in self.dims for d in sdims]):
            raise KeyError

        self._spatial_dims = tuple(sdims)

        ## This is the ordered sequence of data indices that will be displayed
        self._spatial_dims_indices = tuple(
            self.spatial_dims.index(d) for d in self.dims if d in self.spatial_dims
        )

    @property
    def spatial_dims_indices(self) -> tuple[int, ...]:
        """
        The ordered sequence of data indices that will be displayed
        """
        return self._spatial_dims_indices

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

    def _apply_dw_window_func(self, array: ArrayProtocol) -> ArrayProtocol:
        """
        Takes array where display window has already been applied and applies window functions on the `p` dim.

        Parameters
        ----------
        array: ArrayProtocol
            array of shape: [l, display_window, 2 | 3]

        Returns
        -------
        ArrayProtocol
            array with window functions applied along `p` dim
        """
        if self.display_window == 0:
            # can't apply window func when there is only 1 datapoint
            return array

        p_dim = self.spatial_dims[1]

        # display window in array index space
        if self.display_window is not None:
            dw = self.slider_dim_transforms[p_dim](self.display_window)

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
                coor_dims = tuple(map({"x": 0, "y": 1, "z": 2}.get, apply_dims))

                # windows will be of shape [n, (p - ws + 1), 1 | 2 | 3, ws]
                windows = sliding_window_view(
                    array[..., coor_dims], ws, axis=-2
                ).squeeze()

                # make a copy because we need to modify it
                array = array[:, start:stop].copy()

                # this reshape is required to reshape wf outputs of shape [n, p] -> [n, p, 1] only when necessary
                array[..., coor_dims] = wf(windows, axis=-1).reshape(
                    *array.shape[:-1], len(coor_dims)
                )

                return array[:, ::step]

        step = max(1, array.shape[1] // self.max_display_datapoints)

        return array[:, ::step]

    def _apply_spatial_func(self, array: ArrayProtocol) -> ArrayProtocol:
        if self.spatial_func is not None:
            return self.spatial_func(array)

        return array

    def _finalize(self, array: ArrayProtocol) -> ArrayProtocol:
        return self._apply_spatial_func(self._apply_dw_window_func(array))

    def _get_other_features(
        self, data_slice: ArrayProtocol, dw_slice: slice
    ) -> dict[str, ArrayProtocol]:
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
                val_sliced = np.broadcast_to(
                    val_sliced, shape=(n_graphics, *val_sliced.shape[1:])
                )

            other[attr] = val_sliced

        return other

    async def get(self, indices: dict[str, Any]) -> dict[str, ArrayProtocol]:
        """
        slices through all slider dims and outputs an array that can be used to set graphic data

        Note that we do not use __getitem__ here since the index is a tuple specifying a single integer
        index for each dimension. Slices are not allowed, therefore __getitem__ is not suitable here.
        """
        # already squeezed and in the correct spatial_dims order
        window_output = await self.get_window_output(indices)

        # get slice obj for display window
        dw_slice = self._get_dw_slice(indices)

        # data that will be used for the graphical representation
        # slice the datapoints to be displayed in the graphic using the display window slice
        # data are already squeezed & transposed w.r.t the spatial_dims order after get_window_output()
        # p_dims is dim 1
        graphic_data = window_output[:, dw_slice]

        # _finalize runs the user's datapoints_window_func and spatial_func.
        if isinstance(graphic_data, CudaArrayProtocol):
            # the datapoints_window_func and spatial_func should be direct on-cuda functions
            # ex: torch functions that can take cuda arrays directly
            data = self._finalize(graphic_data)
        else:
            # run CPU functions, probably numpy-based, in a thread pool
            data = await run_in_thread_pool(
                self._executor, self._finalize, graphic_data
            )

        other = self._get_other_features(data, dw_slice)

        # final CUDA -> numpy conversion at the end of the pipeline
        if isinstance(data, CudaArrayProtocol):
            data = await run_in_thread_pool(self._executor, cuda_to_numpy, data)

        data = data.transpose(*self._spatial_dims_int)

        return {
            "data": data,
            **other,
        }


class NDPositions(NDGraphic):
    def __init__(
        self,
        ref_index: ReferenceIndex,
        nd_subplot: NDWSubplot,
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
        ],
        processor: type[NDPositionsProcessor] = NDPositionsProcessor,
        display_window: int = 10,
        window_funcs: tuple[WindowFuncCallable | None] | None = None,
        slider_dim_transforms: tuple[Callable[[Any], int] | None] | None = None,
        max_display_datapoints: int = 1_000,
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
        """
        Wraps an :class:`NDPositionsProcessor` and supports four interchangeable
        graphical representations: ``LineStack``, ``LineCollection``, ``ScatterStack``,
        and ``ScatterCollection``.

        Parameters
        ----------
        ref_index
        nd_subplot
        data
        dims
        spatial_dims
        args
        graphic_type
        processor
        display_window
        window_funcs
        slider_dim_transforms
        max_display_datapoints
        colors
        cmap
        cmap_each
        cmap_transform_each
        markers
        markers_each
        sizes
        sizes_each
        thickness
        name
        graphic_kwargs
        processor_kwargs
        """

        super().__init__(nd_subplot, name)

        self.init(
            ref_index,
            data,
            dims,
            spatial_dims,
            *args,
            graphic_type=graphic_type,
            processor=processor,
            display_window=display_window,
            window_funcs=window_funcs,
            slider_dim_transforms=slider_dim_transforms,
            max_display_datapoints=max_display_datapoints,
            colors=colors,
            cmap=cmap,
            cmap_each=cmap_each,
            cmap_transform_each=cmap_transform_each,
            markers=markers,
            markers_each=markers_each,
            sizes=sizes,
            sizes_each=sizes_each,
            thickness=thickness,
            graphic_kwargs=graphic_kwargs,
            processor_kwargs=processor_kwargs,
        )

        run_sync(self._create_graphic())

    def init(
        self,
        ref_index: ReferenceIndex,
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
        ],
        processor: type[NDPositionsProcessor] = NDPositionsProcessor,
        display_window: int = 10,
        window_funcs: tuple[WindowFuncCallable | None] | None = None,
        slider_dim_transforms: tuple[Callable[[Any], int] | None] | None = None,
        max_display_datapoints: int = 1_000,
        colors: (
            Sequence[str] | np.ndarray | Callable[[slice, np.ndarray], np.ndarray]
        ) = None,
        cmap: str = None,
        cmap_each: Sequence[str] = None,
        cmap_transform_each: np.ndarray = None,
        markers: np.ndarray = None,
        markers_each: Sequence[str] = None,
        sizes: np.ndarray = None,
        sizes_each: Sequence[float] = None,
        thickness: np.ndarray = None,
        graphic_kwargs: dict = None,
        processor_kwargs: dict = None,
    ):
        """
        Set up the processor and per-graphic state, i.e. everything except creating the graphic.

        Separated from ``__init__`` so ``NDTimeseries`` can run its own one-time setup
        between this and graphic creation.
        """
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
            slider_dim_transforms=slider_dim_transforms,
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
        | None
    ):
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
    ]:
        return self._graphic_type

    @graphic_type.setter
    def graphic_type(self, graphic_type):
        if type(self.graphic) is graphic_type:
            return

        self._nd_subplot.subplot.delete_graphic(self._graphic)
        self._graphic_type = graphic_type
        run_sync(self._create_graphic())

    @property
    def spatial_dims(self) -> tuple[str, str, str]:
        return self.processor.spatial_dims

    @spatial_dims.setter
    def spatial_dims(self, dims: tuple[str, str, str]):
        self.processor.spatial_dims = dims
        # force re-render
        run_sync(self._set_indices_())

    @property
    def indices(self) -> dict[Hashable, Any]:
        return {d: self._ref_index[d] for d in self.processor.slider_dims}

    async def _get_data_slice(self, indices: dict[str, Any]) -> dict[str, Any]:
        return await self.processor.get(indices)

    async def _set_indices_(self, indices: dict[str, Any] = None):
        if self.data is None:
            return

        if indices is None:
            # fetch the latest indices from the ReferenceIndex
            # else use passed indices from schedule time
            indices = self.indices

        new_features = await self._get_data_slice(indices)
        self._update_graphic(new_features, indices)
        self._last_indices = indices

    def _update_graphic(self, new_features: dict[str, Any], indices: dict[str, Any]):
        data_slice = new_features["data"]

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
                    value = new_features.get(feature, None)

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

    def _tooltip_handler(self, graphic, pick_info):
        if isinstance(self.graphic, (LineCollection, ScatterCollection)):
            # get graphic within the collection
            n_index = np.argwhere(self.graphic.graphics == graphic).item()
            p_index = pick_info["vertex_index"]
            return self.processor.tooltip_format(n_index, p_index)

    async def _create_graphic(self):
        if self.data is None:
            return

        new_features = await self._get_data_slice(self.indices)
        self._setup_graphic(new_features, self.indices)

    def _setup_graphic(self, new_features: dict[str, Any], indices: dict[str, Any]):
        """Build, configure, and add the graphic for the current slice."""
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
                    value = new_features.get(feature, None)

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

        self._nd_subplot.subplot.add_graphic(self._graphic)

    @property
    def display_window(self) -> int | float | None:
        """display window in the reference units for the n_datapoints dim"""
        return self.processor.display_window

    @display_window.setter
    def display_window(self, dw: int | float | None):
        self.processor.display_window = dw
        # force re-render
        run_sync(self._set_indices_())

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
        run_sync(self._set_indices_())

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
        run_sync(self._set_indices_())

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
        run_sync(self._set_indices_())

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
        run_sync(self._set_indices_())
