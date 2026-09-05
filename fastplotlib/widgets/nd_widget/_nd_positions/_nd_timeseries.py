from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Literal, Any, Type, TYPE_CHECKING

import numpy as np
from numpy.typing import ArrayLike

from ....graphics import (
    ImageGraphic,
    LineStack,
    LineCollection,
    ScatterCollection,
    ScatterStack,
)
from ....graphics.utils import pause_events
from ....graphics.selectors import LinearSelector
from ....utils import ArrayProtocol, CudaArrayProtocol, cuda_to_numpy
from .._base import NDGraphic, WindowFuncCallable, block_indices_ctx
from .._index import ReferenceIndex
from .._async import run_sync
from ._nd_positions import (
    NDPositions,
    NDPositionsProcessor,
    ColorsType,
    SizesType,
    MarkersType,
    FeatureCallable,
)

if TYPE_CHECKING:
    from .._ndw_subplot import NDWSubplot


class NDTimeseries(NDPositions):
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
            | ImageGraphic
        ] = LineStack,
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
        linear_selector: bool = False,
        x_range_mode: Literal["fixed", "auto"] | None = None,
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
        ``NDPositions`` subclass for timeseries data, where the ``p`` dim is a time-like x-axis.

        Supports the same ``LineStack``, ``LineCollection``, ``ScatterStack`` and ``ScatterCollection``
        representations plus a heatmap (``ImageGraphic``) view. It also manages a linear selector that tracks the
        current ``p`` index, and couples the camera x-range to it through :attr:`x_range_mode`.

        Parameters
        ----------
        ref_index : ReferenceIndex
            The shared reference index that delivers slider updates to this graphic.

        nd_subplot : NDWSubplot
            parent NDWSubplot the NDGraphic is in

        data : array-like or None
            n-dimensional timeseries data. The value dim holds the (x, y) of each datapoint, where x is the
            time-like coordinate.

            Ex: an array of shape ``[n_trials, n_traces, n_timepoints, 2]`` with ``dims`` of
            ``("trial", "trace", "time", "xy")`` and ``spatial_dims`` of ``("trace", "time", "xy")``.

            Pass ``None`` to create the ``NDTimeseries`` without a graphic and set the data later using
            :attr:`data`.

        dims : Sequence[str]
            Name for every dimension of ``data``, in order. Non-spatial dims must match keys in ``ref_index``.

        spatial_dims : tuple[str, str, str]
            The 3 spatial dims **in display order**: ``(n_graphics, p, <value dim>)``, i.e. the number of traces
            in the collection, the number of datapoints ``p`` in each of them, and the value dim which holds the
            xy or xyz coordinate. A heatmap requires a value dim of size exactly 2.

        args
            extra positional arguments passed to the ``processor`` constructor.

        graphic_type : type[LineCollection | LineStack | ScatterCollection | ScatterStack | ImageGraphic], default ``LineStack``
            The graphical representation used to display the data slice. ``ImageGraphic`` renders the traces as a
            heatmap, one row per trace, where the color represents the y coordinate. The x coordinates are
            applied as the offset and scale of the image, and the y values are interpolated onto a uniform x grid
            if the x sampling is not uniform.

        processor : type[NDPositionsProcessor], default ``NDPositionsProcessor``
            ``NDPositionsProcessor`` subclass that manages the data and produces the data slices.

        display_window : int, float or None, default 10
            Size of the window of the ``p`` dim to render, in the reference units of that dim, centered on its
            current index. Use ``None`` to render every datapoint, which also forces ``x_range_mode`` to
            ``None``. This is what makes out-of-core rendering possible, i.e. rendering a window of a dataset
            that is larger than GPU VRAM.

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
            :class:`NDProcessor`. The transform for the ``p`` dim is typically the array of x values, ex: a
            timestamps array, so the slider is in seconds rather than sample indices.

        max_display_datapoints : int, default 1_000
            Maximum number of datapoints to render per graphic. The step size of the display window slice is set
            from this using floor division.

        datapoints_window_func : tuple[Callable, str, int | float], optional
            Window function applied along the ``p`` dim, as ``(func, apply_dims, window_size)``, see
            :class:`NDPositionsProcessor`.

        linear_selector : bool, default ``False``
            Add a ``LinearSelector`` that marks the current index of the ``p`` dim. Dragging it sets that index
            in the ``ReferenceIndex``, so it drives every other graphic that uses this dim. Only one is created
            per subplot, if one is already present this is ignored.

        x_range_mode : "fixed" | "auto" | None, default ``None``
            How the camera x-range is coupled to the ``p`` dim.

            * ``None``: the camera is left alone.
            * ``"fixed"``: the x-range is set from ``display_window``, centered on the current ``p`` index, on
              every update.
            * ``"auto"``: as ``"fixed"``, and the camera x-range is also polled on every render. Panning or
              zooming then sets ``display_window`` to the new width and the ``p`` index to the new center, with
              a lower bound of 3 datapoints on the width.

        colors : str | Sequence[str] | np.ndarray | FeatureCallable, optional
            Colors of the graphics. Mutually exclusive with ``cmap``, setting one clears the other.

            * static, a single color for every graphic, ex: ``"cyan"`` or an RGBA sequence of 4 floats
            * static, one color per graphic, ``[n_graphics]`` of str or ``[n_graphics, 4]`` RGBA
            * windowed, one color per datapoint, ``[n_graphics, p, 4]`` RGBA
            * windowed, a ``FeatureCallable``

        cmap : str | Sequence[str], optional
            Colormap applied to the graphics, always static. A single name for every graphic, or an iterable of
            ``[n_graphics]`` names for a colormap per graphic. Mutually exclusive with ``colors``. It is the only
            feature that is carried over to the heatmap representation.

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
        lines. The heatmap representation uses only ``cmap``.

        See Also
        --------
        NDPositions : Base class for n-dimensional positional data.

        """
        # NDGraphic base init, then the shared positional setup. We deliberately do not call
        # NDPositions.__init__, since it would create the graphic before the timeseries state
        # (linear selector, x_range_mode) exists.
        NDGraphic.__init__(self, nd_subplot, name)

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

        # makes some assumptions about positional data that apply only to timeseries representations
        # probably don't want to maintain aspect
        self._nd_subplot.subplot.camera.maintain_aspect = False

        # determine a min display_window for x_range_mode = "auto"
        # determines required world space range for 3 datapoints
        p_dim = self.processor.spatial_dims[1]
        p_range = self._ref_index.ref_ranges[p_dim]
        p_map = self.processor.slider_dim_transforms[p_dim]
        p_span = p_range.stop - p_range.start
        p_mid = p_range.start + p_span / 2
        i = p_map(p_mid)
        i_increment = p_map(p_mid + p_range.step)
        delta_p = p_range.step / max(1, i_increment - i)
        self._min_display_window = 3 * delta_p

        # display_window = None overrides x_range_mode
        if self.processor.display_window is None:
            x_range_mode = None

        self._x_range_mode = None
        self._last_x_range: tuple[float, float] | None = None
        self.x_range_mode = x_range_mode

        # make a linear selector only if one does not already exist in this subplot
        if linear_selector and "__ndw_manged_linear_selector" not in self._nd_subplot.subplot:
            self._linear_selector = LinearSelector(
                0, limits=(-np.inf, np.inf), edge_color="cyan", name="__ndw_manged_linear_selector"
            )
            self._linear_selector.add_event_handler(
                self._linear_selector_handler, "selection"
            )
            self._nd_subplot.subplot.add_graphic(self._linear_selector)
        else:
            self._linear_selector = None

        run_sync(self._create_graphic())

    def _update_graphic(self, new_features: dict[str, Any], indices: dict[str, Any]):
        if isinstance(self.graphic, ImageGraphic):
            data_slice = new_features["data"]
            image_data, x0, x_scale = self._create_heatmap_data(data_slice)
            self.graphic.data = image_data
            self.graphic.offset = (x0, *self.graphic.offset[1:])
            self.graphic.scale = (x_scale, *self.graphic.scale[1:])
        else:
            super()._update_graphic(new_features, indices)

        self._update_view(indices, new_features["data"])

    def _setup_graphic(self, new_features: dict[str, Any], indices: dict[str, Any]):
        if issubclass(self._graphic_type, ImageGraphic):
            data_slice = new_features["data"]
            # `d` dim must only have xy data to be interpreted as a heatmap, xyz can't become a timeseries heatmap
            if self.processor.shape[self.processor.spatial_dims[-1]] != 2:
                raise ValueError

            image_data, x0, x_scale = self._create_heatmap_data(data_slice)
            self._graphic = self._graphic_type(
                image_data, offset=(x0, 0, -1), scale=(x_scale, 1, 1)
            )
            cmap = self._static_features.get("cmap")
            if cmap is not None:
                self._graphic.cmap = cmap
            self._nd_subplot.subplot.add_graphic(self._graphic)
        else:
            super()._setup_graphic(new_features, indices)

        self._update_view(indices, new_features["data"])

    async def _create_graphic(self):
        await super()._create_graphic()
        # use the max over the full `p` dim to account for the y-max of each line/scatter for proper spacing
        if isinstance(self._graphic, (LineStack, ScatterStack)):
            steps = np.zeros((len(self._graphic), 3))
            steps[:, 1] = await self._p_y_max()
            self._graphic.steps = steps

    async def _p_y_max(self) -> np.ndarray:
        """per-graphic max of the y values over the full `p` dim, shape [n_graphics]"""
        proc = self.processor
        # the indexer leaves the spatial `p` dim unsliced, so this raw slice spans every datapoint
        raw = await proc._get_raw_data_slice(self.indices)
        c = proc.dims.index(proc.spatial_dims[2])  # coord dim; y is index 1
        g = proc.dims.index(proc.spatial_dims[0])  # graphics dim
        y = raw[(slice(None),) * c + (1,)]  # y values as a view, coord dim removed
        # keep the graphics dim (shifted down if it was past the removed coord dim), max the rest;
        # `.max` runs on whatever the array is (numpy/cupy/torch/jax), so a GPU array reduces on-device
        g_axis = g if g < c else g - 1
        result = y.max(axis=tuple(i for i in range(y.ndim) if i != g_axis))
        if isinstance(result, CudaArrayProtocol):
            # only the small [n_graphics] result crosses back to host
            result = cuda_to_numpy(result)
        return result

    def _update_view(self, indices: dict[str, Any], data_slice: np.ndarray):
        """update the camera x-range and linear selector to the current datapoints position."""

        p_dim = self.processor.spatial_dims[1]

        if self.x_range_mode is not None:
            # set x_range directly from the display_window, NOT from the data_slice x-range,
            # this way it doesn't fight with the _update_from_view_range() polling
            hw = self.processor.display_window / 2
            center = indices[p_dim]
            self._nd_subplot.subplot.x_range = center - hw, center + hw
            # store new x_range so the auto-polling does not trigger
            # an x_range update and yet another view update resulting in jitter
            self._last_x_range = self._nd_subplot.subplot.x_range

        if self._linear_selector is not None:
            # x range of the data
            xr_data = data_slice[0, 0, 0], data_slice[0, -1, 0]
            with pause_events(
                self._linear_selector
            ):  # we don't want the linear selector change to update the indices
                self._linear_selector.limits = xr_data
                # linear selector acts on `p` dim
                self._linear_selector.selection = indices[p_dim]

    def _linear_selector_handler(self, ev):
        with block_indices_ctx(*self._nd_subplot.nd_graphics):
            # block index change in all NDGraphics that are not in the same subplot
            self._ref_index.set_dim_index(
                self.processor.spatial_dims[1], ev.info["value"]
            )

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
        """
        Get or set the display window, in the reference units of the ``p`` dim. Setting it re-renders the
        current data slice, setting it to ``None`` also sets :attr:`x_range_mode` to ``None``.
        """
        return self.processor.display_window

    @display_window.setter
    def display_window(self, dw: int | float | None):
        self.processor.display_window = dw
        if dw is None:
            self.x_range_mode = None

        # force re-render
        run_sync(self._set_indices_())

    @property
    def x_range_mode(self) -> Literal["fixed", "auto"] | None:
        """
        Get or set how the camera x-range is coupled to the ``p`` dim.

        * ``None``: the camera is left alone.
        * ``"fixed"``: the x-range is set from the display window, centered on the current ``p`` index, on every
          update.
        * ``"auto"``: as ``"fixed"``, and the camera x-range is also polled on every render. Panning or zooming
          then sets the display window to the new width and the ``p`` index to the new center.
        """
        return self._x_range_mode

    @x_range_mode.setter
    def x_range_mode(self, mode: Literal[None, "fixed", "auto"]):
        if mode not in (None, "fixed", "auto"):
            raise ValueError(
                f"x_range_mode must be None, 'fixed', or 'auto', got: {mode!r}"
            )
        if mode == self._x_range_mode:
            return

        if self._x_range_mode == "auto":
            # old mode was auto
            self._nd_subplot.subplot.remove_animation(self._update_from_view_range)
            self._last_x_range = None

        if mode == "auto":
            # seed so the first tick does not fire spuriously
            self._last_x_range = self._nd_subplot.subplot.x_range
            self._nd_subplot.subplot.add_animations(self._update_from_view_range)

        self._x_range_mode = mode

    def _update_from_view_range(self):
        # update from current x_range if it has changed
        if self._graphic is None:
            return

        xr = self._nd_subplot.subplot.x_range
        if xr == self._last_x_range:
            # x_range hasn't changed
            return

        self._last_x_range = xr

        new_width = abs(xr[1] - xr[0])
        # make sure width is sufficient for >= 3 datapoints
        if new_width < self._min_display_window:
            new_width = self._min_display_window

        new_index = (xr[0] + xr[1]) / 2

        self.processor.display_window = new_width

        # block scheduling an additional async _set_indices_ for ndgraphics in this subplot
        with block_indices_ctx(*self._nd_subplot.nd_graphics):
            p_dim = self.processor.spatial_dims[1]
            self._ref_index.set_dim_index(p_dim, new_index)

        # run this ndgraphic update immediately so graphic data and linear selector are in sync with the
        # camera, otherwise you get laggy movement
        run_sync(self._set_indices_())
