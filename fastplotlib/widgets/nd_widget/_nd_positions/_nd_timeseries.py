from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Literal, Any, Type, TYPE_CHECKING

import numpy as np

from ....graphics import (
    ImageGraphic,
    LineStack,
    LineCollection,
    ScatterCollection,
    ScatterStack,
)
from ....graphics.utils import pause_events
from ....graphics.selectors import LinearSelector
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
        display_window: int = 10,
        window_funcs: tuple[WindowFuncCallable | None] | None = None,
        slider_dim_transforms: tuple[Callable[[Any], int] | None] | None = None,
        max_display_datapoints: int = 1_000,
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
        ``NDPositions`` for timeseries data, where the datapoints dim is a time-like x-axis.

        Supports the same ``LineStack`` / ``LineCollection`` / ``ScatterStack`` /
        ``ScatterCollection`` representations plus a heatmap (``ImageGraphic``) view, and
        additionally manages a linear selector and couples the camera x-range to the current
        datapoints position via :attr:`x_range_mode`.

        Parameters are the same as :class:`NDPositions`, plus ``linear_selector`` and
        ``x_range_mode``.
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
        """display window in the reference units for the n_datapoints dim"""
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
        """x-range using a fixed window from the display window, or by polling the camera (auto)"""
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
