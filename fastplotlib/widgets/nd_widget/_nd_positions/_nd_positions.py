from __future__ import annotations

from collections.abc import Callable, Hashable, Sequence
from functools import partial
from typing import Any, Type, TYPE_CHECKING

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from numpy.typing import ArrayLike

from ....graphics import (
    LineStack,
    LineCollection,
    ScatterCollection,
    ScatterStack,
)
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


class NDPositionsProcessor(NDProcessor):
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

        # other graphic features windowed per-datapoint (arrays or callables), keyed by feature name
        self._other_features: dict[str, Any] = dict()


    def set_other_feature(self, name: str, value):
        """set, or clear if ``value`` is None, an other graphic feature to window per-datapoint"""
        if value is None:
            self._other_features.pop(name, None)
        elif callable(value):
            self._other_features[name] = value
        else:
            self._other_features[name] = np.asarray(value)

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
        # window the per-graphic datapoint (`p`) axis (axis 1) of each feature
        other = dict()
        for name, val in self._other_features.items():
            if callable(val):
                other[name] = val(data_slice, dw_slice)
            else:
                other[name] = val[:, dw_slice]
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

        data = data.transpose(*self.spatial_dims_indices)

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
            LineCollection
            | LineStack
            | ScatterCollection
            | ScatterStack
        ],
        processor: type[NDPositionsProcessor] = NDPositionsProcessor,
        display_window: int = 10,
        window_funcs: tuple[WindowFuncCallable | None] | None = None,
        slider_dim_transforms: tuple[Callable[[Any], int] | None] | None = None,
        max_display_datapoints: int = 1_000,
        colors: ColorsType = None,
        cmap: str | Sequence[str] = None,
        cmap_transform: np.ndarray | FeatureCallable = None,
        cmap_range: tuple[float, float] = None,
        thickness: float | Sequence[float] = None,
        sizes: SizesType = None,
        markers: MarkersType = None,
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
        cmap_transform
        cmap_range
        thickness
        sizes
        markers
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
            cmap_transform=cmap_transform,
            cmap_range=cmap_range,
            thickness=thickness,
            sizes=sizes,
            markers=markers,
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
            LineCollection
            | LineStack
            | ScatterCollection
            | ScatterStack
        ],
        processor: type[NDPositionsProcessor] = NDPositionsProcessor,
        display_window: int = 10,
        window_funcs: tuple[WindowFuncCallable | None] | None = None,
        slider_dim_transforms: tuple[Callable[[Any], int] | None] | None = None,
        max_display_datapoints: int = 1_000,
        colors: ColorsType = None,
        cmap: str | Sequence[str] = None,
        cmap_transform: np.ndarray | FeatureCallable = None,
        cmap_range: tuple[float, float] = None,
        thickness: float | Sequence[float] = None,
        sizes: SizesType = None,
        markers: MarkersType = None,
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
            **processor_kwargs,
        )

        self._graphic_type = graphic_type

        # each feature is either windowed per-datapoint (into the processor) or static (onto
        # the collection); _set_feature routes and stores it for re-creation on a type switch
        self._static_features: dict[str, Any] = dict()
        features = {
            "colors": colors,
            "cmap": cmap,
            "cmap_transform": cmap_transform,
            "cmap_range": cmap_range,
            "thickness": thickness,
            "sizes": sizes,
            "markers": markers,
        }
        for name, value in features.items():
            self._set_feature(name, value)

    def _set_feature(self, name: str, value):
        """
        Route a graphic feature to the collection.

        A callable, or an array with the datapoint dim (``p``) at axis 1, is windowed
        per-datapoint by the processor and set onto the collection each frame. Anything else is
        static: it is stored and set once onto the collection.
        """
        if value is not None:
            # explicit colors and a colormap are mutually exclusive; drop the other source
            self._clear_conflicting_color_source(name)

        if self._is_windowed(value):
            self._static_features.pop(name, None)
            self.processor.set_other_feature(name, value)
            if self._graphic is not None:
                run_sync(self._set_indices_())
            return

        # static: clear any windowed version, store, and set it onto the collection
        self.processor.set_other_feature(name, None)
        if value is None:
            self._static_features.pop(name, None)
            return
        self._static_features[name] = value
        if self._graphic is not None:
            setattr(self.graphic, name, value)

    def _get_feature(self, name: str):
        # the static value, or the windowed value held by the processor
        if name in self._static_features:
            return self._static_features[name]
        return self.processor._other_features.get(name)

    def _clear_conflicting_color_source(self, name: str):
        # a graphic's color is either explicit `colors` or a colormap, never both
        if name == "colors":
            conflicting = ("cmap", "cmap_transform", "cmap_range")
        elif name in ("cmap", "cmap_transform", "cmap_range"):
            conflicting = ("colors",)
        else:
            return
        for other in conflicting:
            self._static_features.pop(other, None)
            self.processor.set_other_feature(other, None)

    def _is_windowed(self, value) -> bool:
        # windowed features are per-datapoint and sliced to the display window each frame: a
        # callable, or a ``[n_graphics, p, ...]`` array-like carrying the datapoint (`p`) axis.
        # Anything else (a single value, or a per-graphic sequence/iterator) is static
        if callable(value):
            return True
        if isinstance(value, (list, tuple, np.ndarray)):
            value = np.asarray(value)
            p_size = self.processor.shape[self.processor.spatial_dims[1]]
            return value.ndim >= 2 and value.shape[1] == p_size
        return False

    def _cmap_range(self):
        # the cmap_range over the full `p` dimension (per-graphic min/max of the stored
        # cmap_transform), or the user's explicit cmap_range. A callable transform's full range
        # isn't knowable without evaluating it everywhere, so that needs an explicit cmap_range
        if "cmap_range" in self._static_features:
            return self._static_features["cmap_range"]
        transform = self.processor._other_features.get("cmap_transform")
        if not isinstance(transform, np.ndarray):
            return None
        if transform.ndim == 1:
            return (float(transform.min()), float(transform.max()))
        return np.stack([transform.min(axis=1), transform.max(axis=1)], axis=1)

    @property
    def processor(self) -> NDPositionsProcessor:
        return self._processor

    @property
    def graphic(
        self,
    ) -> (
        LineCollection
        | LineStack
        | ScatterCollection
        | ScatterStack
        | None
    ):
        return self._graphic

    @property
    def graphic_type(
        self,
    ) -> Type[
        LineCollection
        | LineStack
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

    def _set_other_features(self, new_features: dict[str, Any]):
        # set each windowed feature across the collection via its property setter (cmap-family
        # have no accessor); the setter broadcasts a shared value, switches each graphic's mode,
        # and resizes to the current display window
        for name, value in new_features.items():
            if name == "data" or not hasattr(type(self.graphic), name):
                # skip a feature the current graphic type doesn't have, e.g. sizes on lines
                continue
            setattr(self.graphic, name, value)

        # a windowed cmap_transform makes the graphic auto-set cmap_range to just the displayed
        # datapoints; override it with the range over the full `p` dimension so the display
        # window maps to its position in the colormap
        if "cmap_transform" in new_features and hasattr(type(self.graphic), "cmap_range"):
            cmap_range = self._cmap_range()
            if cmap_range is not None:
                self.graphic.cmap_range = cmap_range

    def _update_graphic(self, new_features: dict[str, Any], indices: dict[str, Any]):
        data_slice = new_features["data"]  # [n_graphics, n_datapoints, xy(z)]

        if self.graphic.data[0].shape[0] != data_slice.shape[1]:
            # n_datapoints changed, create new buffer
            self.graphic.data[:] = data_slice
        else:
            # same num datapoints
            self.graphic.data[:, :, : data_slice.shape[-1]] = data_slice

        self._set_other_features(new_features)

    def _tooltip_handler(self, graphic, pick_info):
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
        """Build and add the graphic for the current slice."""
        data_slice = new_features["data"]  # [n_graphics, n_datapoints, xy(z)]

        # skip any static feature the graphic type doesn't have, e.g. thickness on scatters
        static = {
            name: value
            for name, value in self._static_features.items()
            if hasattr(self._graphic_type, name)
        }
        self._graphic = self._graphic_type(
            data_slice, **static, **self._graphic_kwargs
        )
        self._set_other_features(new_features)

        if self.processor.tooltip:
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
    def colors(self):
        """get or set the colors of the graphics"""
        return self._get_feature("colors")

    @colors.setter
    def colors(self, value):
        self._set_feature("colors", value)

    @property
    def cmap(self):
        """get or set the cmap of the graphics"""
        return self._get_feature("cmap")

    @cmap.setter
    def cmap(self, value):
        self._set_feature("cmap", value)

    @property
    def cmap_transform(self):
        """get or set the cmap_transform of the graphics"""
        return self._get_feature("cmap_transform")

    @cmap_transform.setter
    def cmap_transform(self, value):
        self._set_feature("cmap_transform", value)

    @property
    def cmap_range(self):
        """get or set the cmap_range of the graphics"""
        return self._get_feature("cmap_range")

    @cmap_range.setter
    def cmap_range(self, value):
        self._set_feature("cmap_range", value)

    @property
    def thickness(self):
        """get or set the thickness of the graphics"""
        return self._get_feature("thickness")

    @thickness.setter
    def thickness(self, value):
        self._set_feature("thickness", value)

    @property
    def sizes(self):
        """get or set the sizes of the graphics"""
        return self._get_feature("sizes")

    @sizes.setter
    def sizes(self, value):
        self._set_feature("sizes", value)

    @property
    def markers(self):
        """get or set the markers of the graphics"""
        return self._get_feature("markers")

    @markers.setter
    def markers(self, value):
        self._set_feature("markers", value)
