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
ColorsType = str | Sequence[str] | np.ndarray | FeatureCallable | None
MarkersType = str | Sequence[str] | np.ndarray | FeatureCallable | None
SizesType = float | Sequence[float] | np.ndarray | FeatureCallable | None


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

        Produces ``[n_graphics, p, <value dim>]`` slices for a ``LineCollection``, ``LineStack``,
        ``ScatterCollection``, or ``ScatterStack``, where ``p`` is the datapoints dim.

        The ``p`` dim is simultaneously a slider dim and a spatial dim. Rather than the general ``window_funcs``
        mechanism, it is windowed by :attr:`display_window`, which selects the datapoints that are rendered, and
        by :attr:`datapoints_window_func`, which aggregates over them.

        Parameters
        ----------
        data: ArrayProtocol
            n-dimensional positional data, must have 3 or more dims.

        dims: Sequence[str]
            names for each dimension in ``data``. Dimensions not listed in ``spatial_dims`` are treated as slider
            dimensions and **must** appear as keys in the parent ``NDWidget``'s ``ref_ranges``.
                Examples::
                 ``("trial", "line", "time", "xy")``
                 ``("keypoints", "time", "xyz")``

            dims in the array do not need to be in the order that you want to display them, the data slice is
            transposed into the order given by ``spatial_dims``.

        spatial_dims : tuple[str, str, str]
            The 3 spatial dims **in display order**: ``(n_graphics, p, <value dim>)``, i.e. the number of lines
            or scatters in the collection, the number of datapoints ``p`` in each of them, and the value dim
            which holds the xy or xyz coordinate and must be of size 2 or 3.

        slider_dim_transforms : dict[str, Callable[[Any], int] | ArrayLike], optional
            See :class:`NDProcessor`. The transform for the ``p`` dim is also used to map ``display_window`` and
            the ``datapoints_window_func`` window size from reference units to array indices.

        display_window: int, float or None, default 100
            Size of the window of the ``p`` dim to render, in the reference units of that dim, centered on its
            current index. Use ``None`` to render every datapoint, or ``0`` to render only the datapoint at the
            current index.

        max_display_datapoints: int, default 1_000
            Maximum number of datapoints to render per graphic. The step size of the display window slice is set
            from this using floor division.

        datapoints_window_func: tuple[Callable, str, int | float], optional
            Window function applied along the ``p`` dim after the display window has been taken, as
            ``(func, apply_dims, window_size)`` where:

            * *func* must accept an ``axis: int`` kwarg (ex: ``np.mean``, ``np.max``). It is given a sliding
              window view of the data and is reduced along the window axis.

            * *apply_dims* names the coordinates of the value dim to apply it to, one of ``"all", "x", "y",
              "z", "xy", "xz", "yz", "xyz"``. Coordinates that are not named are passed through unchanged.

            * *window_size* is in the reference units of the ``p`` dim. It is mapped to array indices, clamped to
              a minimum of 3, and rounded up to an odd size.

            Important note: if used, ``display_window`` is approximate and not exact due to padding from the
            window size. The window function is skipped when ``display_window`` is ``0``, or when the display
            window spans more than ``2 * max_display_datapoints`` array indices, which would be too expensive to
            compute.

        kwargs
            passed to :class:`NDProcessor`, i.e. ``window_funcs``, ``window_order`` and ``spatial_func``.

        See Also
        --------
            NDProcessor : Base class with full parameter documentation.
            NDPositions : The ``NDGraphic`` that uses this processor by default.
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
    def slider_dims(self) -> tuple[str, ...]:
        """slider dim names, the non-spatial dims plus the ``p`` dim"""
        # append `p` dim to slider dims
        return tuple([*super().slider_dims, self.spatial_dims[1]])

    @property
    def display_window(self) -> int | float | None:
        """get or set the display window, in the reference units of the ``p`` dim"""
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
        """
        Get or set the maximum number of datapoints to render per graphic. The step size of the display window
        slice is set from this using floor division.
        """
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
        Get or set the window function applied along the ``p`` dim, as ``(func, apply_dims, window_size)``.

        ``apply_dims`` names the coordinates of the value dim that the window function is applied to, one of
        ``"all", "x", "y", "z", "xy", "xz", "yz", "xyz"``. ``window_size`` is in the reference units of the
        ``p`` dim.
        """
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
        display_window: int | float | None = 10,
        window_funcs: dict[
            str, tuple[WindowFuncCallable | None, int | float | None]
        ] = None,
        window_order: tuple[str, ...] = None,
        spatial_func: Callable[[ArrayProtocol], ArrayProtocol] = None,
        slider_dim_transforms: dict[str, Callable[[Any], int] | ArrayLike] = None,
        max_display_datapoints: int = 1_000,
        datapoints_window_func: tuple[Callable, str, int | float] | None = None,
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
        ``NDGraphic`` subclass for n-dimensional positional data.

        Uses an :class:`NDPositionsProcessor` to produce the data slices and manages one of four interchangeable
        graphical representations: ``LineStack``, ``LineCollection``, ``ScatterStack``, and ``ScatterCollection``.
        The representation can be changed at runtime by setting :attr:`graphic_type`.

        Every dimension that is *not* listed in ``spatial_dims`` becomes a slider dimension. Each slider dim must
        have a ``ReferenceRange`` defined in the ``ReferenceIndex`` of the parent ``NDWidget``. The datapoints
        dim, ``p``, is both a spatial dim and a slider dim, it is windowed by ``display_window`` and
        ``datapoints_window_func`` rather than by ``window_funcs``.

        Parameters
        ----------
        ref_index : ReferenceIndex
            The shared reference index that delivers slider updates to this graphic.

        nd_subplot : NDWSubplot
            parent NDWSubplot the NDGraphic is in

        data : array-like or None
            n-dimensional positional data.

            Ex: an array of shape ``[n_trials, n_lines, n_timepoints, 2]`` with ``dims`` of
            ``("trial", "line", "time", "xy")`` and ``spatial_dims`` of ``("line", "time", "xy")``.

            Pass ``None`` to create the ``NDPositions`` without a graphic and set the data later using
            :attr:`data`.

        dims : Sequence[str]
            Name for every dimension of ``data``, in order. Non-spatial dims must match keys in ``ref_index``.

        spatial_dims : tuple[str, str, str]
            The 3 spatial dims **in display order**: ``(n_graphics, p, <value dim>)``, i.e. the number of lines
            or scatters in the collection, the number of datapoints ``p`` in each of them, and the value dim
            which holds the xy or xyz coordinate and must be of size 2 or 3. The dims do not need to be in this
            order in the array, the data slice is transposed into display order.

        args
            extra positional arguments passed to the ``processor`` constructor.

        graphic_type : type[LineCollection | LineStack | ScatterCollection | ScatterStack]
            The graphical representation used to display the data slice.

        processor : type[NDPositionsProcessor], default ``NDPositionsProcessor``
            ``NDPositionsProcessor`` subclass that manages the data and produces the data slices.

        display_window : int, float or None, default 10
            Size of the window of the ``p`` dim to render, in the reference units of that dim, centered on its
            current index. Use ``None`` to render every datapoint, or ``0`` to render only the datapoint at the
            current index. This is what makes out-of-core rendering possible, i.e. rendering a window of a
            dataset that is larger than GPU VRAM.

        window_funcs : dict[str, tuple[WindowFuncCallable | None, int | float | None]], optional
            Per-slider-dim window functions applied around the current slider position, see
            :class:`NDProcessor`. Not used for the ``p`` dim, see ``datapoints_window_func``.

        window_order : tuple[str, ...], optional
            Order in which the window functions are applied across dims. Only dims listed here have their window
            function applied, see :class:`NDProcessor`.

        spatial_func : Callable[[ArrayProtocol], ArrayProtocol], optional
            A function applied to the spatial slice *after* the window funcs, right before rendering.

        slider_dim_transforms : dict[str, Callable[[Any], int] | ArrayLike], optional
            Per-slider-dim mapping from reference-space values to local array indices, see
            :class:`NDProcessor`.

        max_display_datapoints : int, default 1_000
            Maximum number of datapoints to render per graphic. The step size of the display window slice is set
            from this using floor division.

        datapoints_window_func : tuple[Callable, str, int | float], optional
            Window function applied along the ``p`` dim, as ``(func, apply_dims, window_size)``, see
            :class:`NDPositionsProcessor`.

        colors : str | Sequence[str] | np.ndarray | FeatureCallable, optional
            Colors of the graphics. Mutually exclusive with ``cmap``, setting one clears the other.

            * static, a single color for every graphic, ex: ``"cyan"`` or an RGBA sequence of 4 floats
            * static, one color per graphic, ``[n_graphics]`` of str or ``[n_graphics, 4]`` RGBA
            * windowed, one color per datapoint, ``[n_graphics, p, 4]`` RGBA
            * windowed, a ``FeatureCallable``

        cmap : str | Sequence[str], optional
            Colormap applied to the graphics, always static. A single name for every graphic, or an iterable of
            ``[n_graphics]`` names for a colormap per graphic. Mutually exclusive with ``colors``.

        cmap_transform : np.ndarray | FeatureCallable, optional
            Values that the colormap colors are mapped from.

            * static, one value per graphic, ``[n_graphics]``, so each graphic gets a single color
            * windowed, one value per datapoint, ``[n_graphics, p]``
            * windowed, a ``FeatureCallable``

        cmap_range : (float, float) | np.ndarray, optional
            The (min, max) of ``cmap_transform`` mapped onto the colormap, or ``[n_graphics, 2]`` for a range per
            graphic. A windowed array ``cmap_transform`` defaults to its own (min, max) over the full ``p`` dim,
            so the display window keeps its position within the colormap. A ``FeatureCallable`` transform
            requires an explicit range, its full range is not knowable without evaluating it everywhere.

        thickness : float | Sequence[float], optional
            Thickness of the lines, always static. A single value for every graphic, or ``[n_graphics]`` values
            for a thickness per graphic.

        sizes : float | Sequence[float] | np.ndarray | FeatureCallable, optional
            Size of the scatter points.

            * static, a single size for every graphic, or ``[n_graphics]`` sizes for one size per graphic
            * windowed, one size per datapoint, ``[n_graphics, p]``
            * windowed, a ``FeatureCallable``

        markers : str | Sequence[str] | np.ndarray | FeatureCallable, optional
            Marker shape of the scatter points.

            * static, a single marker for every graphic, or ``[n_graphics]`` markers for one per graphic
            * windowed, one marker per datapoint, ``[n_graphics, p]``
            * windowed, a ``FeatureCallable``

        name : str, optional
            Name for this ``NDGraphic``, used to retrieve it with ``nd_subplot[name]``.

        graphic_kwargs : dict, optional
            passed to the ``graphic_type`` constructor.

        processor_kwargs : dict, optional
            passed to the ``processor`` constructor.

        Notes
        -----
        Each of the other graphic features is either *windowed* or *static*, decided from the value itself:

        * **windowed**: a ``FeatureCallable``, or an array whose axis 1 spans the ``p`` dim. It is re-sliced with
          the same display window slice as the data on every update, so the feature carries a value per
          displayed datapoint. An array **must** span the **full** ``p`` dim of the data, i.e.
          ``[n_graphics, p, <value dim>]``, since it is indexed with an index into the full ``p`` dim. A
          ``FeatureCallable`` is passed the data slice and that display window slice, and returns the feature
          values for the displayed datapoints.

        * **static**: anything else. It is set once on the collection, ex: a single value for every graphic,
          ``[n_graphics]`` values for one per graphic, or an iterator of per-graphic values such as
          ``itertools.cycle(["jet", "viridis"])``.

        A feature the graphic type does not have is ignored, ex: ``thickness`` for scatters, ``markers`` for
        lines.

        See Also
        --------
        NDPositionsProcessor : The processor that produces the data slices for this graphic.

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
            window_order=window_order,
            spatial_func=spatial_func,
            slider_dim_transforms=slider_dim_transforms,
            max_display_datapoints=max_display_datapoints,
            datapoints_window_func=datapoints_window_func,
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
        display_window: int | float | None = 10,
        window_funcs: dict[
            str, tuple[WindowFuncCallable | None, int | float | None]
        ] = None,
        window_order: tuple[str, ...] = None,
        spatial_func: Callable[[ArrayProtocol], ArrayProtocol] = None,
        slider_dim_transforms: dict[str, Callable[[Any], int] | ArrayLike] = None,
        max_display_datapoints: int = 1_000,
        datapoints_window_func: tuple[Callable, str, int | float] | None = None,
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
            datapoints_window_func=datapoints_window_func,
            window_funcs=window_funcs,
            window_order=window_order,
            spatial_func=spatial_func,
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
        """NDProcessor that manages the data and produces data slices to display"""
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
        """Underlying Graphic object used to display the current data slice, ``None`` if the data is ``None``"""
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
        """
        Get or set the graphical representation used to display the data slice. Setting it deletes the current
        graphic and creates one of the given type using the current slice.
        """
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
        """
        Get or set the spatial dims **in display order**: ``(n_graphics, p, <value dim>)``. Setting them
        re-renders the current data slice.
        """
        return self.processor.spatial_dims

    @spatial_dims.setter
    def spatial_dims(self, dims: tuple[str, str, str]):
        self.processor.spatial_dims = dims
        # force re-render
        run_sync(self._set_indices_())

    @property
    def indices(self) -> dict[Hashable, Any]:
        """the current index of each slider dim in reference-space units, from the ``ReferenceIndex``"""
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
        """
        Get or set the display window, in the reference units of the ``p`` dim. Setting it re-renders the
        current data slice.
        """
        return self.processor.display_window

    @display_window.setter
    def display_window(self, dw: int | float | None):
        self.processor.display_window = dw
        # force re-render
        run_sync(self._set_indices_())

    @property
    def datapoints_window_func(self) -> tuple[Callable, str, int | float] | None:
        """
        Get or set the window function applied along the ``p`` dim, as ``(func, apply_dims, window_size)``.

        ``apply_dims`` names the coordinates of the value dim that the window function is applied to, one of
        ``"all", "x", "y", "z", "xy", "xz", "yz", "xyz"``. ``window_size`` is in the reference units of the
        ``p`` dim.
        """
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
