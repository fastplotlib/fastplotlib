import warnings
from collections.abc import Callable
from typing import Literal, Sequence, Hashable

import numpy as np

from ... import (
    ScatterCollection,
    ScatterStack,
    LineCollection,
    LineStack,
    ImageGraphic,
)
from ...layouts import Subplot
from ...utils import ArrayProtocol, enums
from . import NDImageProcessor, NDImage, NDPositions, NDTimeseries, NDVectors
from ._index import AutoRangeContinuous
from ._video import VideoProcessor
from ._base import NDGraphic, WindowFuncCallable


class NDWSubplot:
    """
    Entry point for adding ``NDGraphic`` objects to a subplot of an ``NDWidget``.

    Accessed via ``ndw[row, col]`` or ``ndw["subplot_name"]``.
    Each ``add_nd_<...>`` method constructs the appropriate ``NDGraphic``, registers it with the parent
    ``ReferenceIndex``, appends it to this subplot and returns the ``NDGraphic`` instance to the user.

    Note: ``NDWSubplot`` is not meant to be constructed directly, it only exists as part of an ``NDWidget``
    """

    def __init__(self, ndw, subplot: Subplot):
        self.ndw = ndw
        self._subplot = subplot

        self._nd_graphics = list()

    @property
    def subplot(self) -> Subplot:
        return self._subplot

    @property
    def nd_graphics(self) -> tuple[NDGraphic]:
        """all the NDGraphic instance in this subplot"""
        return tuple(self._nd_graphics)

    def __getitem__(self, key) -> NDGraphic:
        # get a specific NDGraphic by index or name
        if isinstance(key, (int, np.integer)):
            return self.nd_graphics[key]

        for g in self.nd_graphics:
            if g.name == key:
                return g

        else:
            raise KeyError(f"NDGraphc with given key not found: {key}")

    def delete_nd_graphic(self, ndg: NDGraphic):
        """Delete an NDGraphic from the subplot"""

        # TODO: verify that this actually garbage collects
        del ndg.data
        self.subplot.delete_graphic(ndg.graphic)
        self._nd_graphics.remove(ndg)

        del ndg

    def _check_slider_dims(
        self,
        dims: Sequence[Hashable],
        spatial_dims: Sequence[Hashable],
        data: ArrayProtocol | None,
        positions: bool = False,
    ):
        """
        Make sure every slider (non-spatial) dim of a graphic being added has a
        reference range. A dim without one gets an ``AutoRangeContinuous`` sized to
        the data, an existing ``AutoRangeContinuous`` is grown to fit, and an
        explicit range is left untouched.
        """
        if data is None:
            # size is unknown, an explicit range is still required
            return

        dims = tuple(dims)
        slider_dims = set(dims) - set(spatial_dims)
        if positions:
            # the datapoints `p` axis is a spatial dim that also needs a reference range
            slider_dims.add(spatial_dims[1])

        for dim in slider_dims:
            size = data.shape[dims.index(dim)]

            if dim not in self.ndw.indices.dims:
                warnings.warn(
                    f"No reference range specified for non-spatial dim '{dim}', "
                    f"auto-generating an `AutoRangeContinuous(0, {size}, 1)`."
                )
                self.ndw.indices.push_dims({dim: AutoRangeContinuous(0, size, 1)})

            elif isinstance(self.ndw.indices.ref_ranges[dim], AutoRangeContinuous):
                # grow the existing auto range to fit this array
                self.ndw.indices.ref_ranges[dim].stop = max(
                    self.ndw.indices.ref_ranges[dim].stop, size
                )

    def add_nd_image(
        self,
        data: ArrayProtocol | None,
        dims: Sequence[Hashable],
        spatial_dims: (
            tuple[str, str] | tuple[str, str, str]
        ),  # must be in order! [rows, cols] | [z, rows, cols]
        rgb_dim: str | None = None,
        window_funcs: tuple[WindowFuncCallable | None, ...] | WindowFuncCallable = None,
        window_order: tuple[int, ...] = None,
        spatial_func: Callable[[ArrayProtocol], ArrayProtocol] = None,
        compute_histogram: bool = True,
        slider_dim_transforms=None,
        name: str = None,
        **kwargs,
    ):
        self._check_slider_dims(dims, spatial_dims, data)

        nd = NDImage(
            self.ndw.indices,
            nd_subplot=self,
            data=data,
            dims=dims,
            spatial_dims=spatial_dims,
            rgb_dim=rgb_dim,
            window_funcs=window_funcs,
            window_order=window_order,
            spatial_func=spatial_func,
            compute_histogram=compute_histogram,
            slider_dim_transforms=slider_dim_transforms,
            name=name,
            **kwargs,
        )

        self._nd_graphics.append(nd)
        return nd

    def add_video(
            self,
            data: ArrayProtocol | None,
            dims: Sequence[str],
            spatial_dims: tuple[str, str] | tuple[str, str, str],
            rgb_dim: str | None = None,
            colorspace: enums.ColorspacesYUV | enums.ColorspacesRGB = "yuv420p",
            colorrange: enums.ColorRange = "limited",
            processor_type: NDImageProcessor = VideoProcessor,
            **kwargs,
    ):
        return self.add_nd_image(
            data=data,
            dims=dims,
            spatial_dims=spatial_dims,
            rgb_dim=rgb_dim,
            colorspace=colorspace,
            colorrange=colorrange,
            processor_type=processor_type,
            **kwargs,
        )

    def add_nd_vectors(
        self,
        data: ArrayProtocol | None,
        dims: Sequence[str],
        spatial_dims: tuple[str, str, str],
        window_funcs: tuple[WindowFuncCallable | None, ...] | WindowFuncCallable = None,
        window_order: tuple[int, ...] = None,
        spatial_func: Callable[[ArrayProtocol], ArrayProtocol] = None,
        slider_dim_transforms=None,
        name: str = None,
        **kwargs
    ) -> NDVectors:
        self._check_slider_dims(dims, spatial_dims, data)

        nd = NDVectors(
            self.ndw.indices,
            nd_subplot=self,
            data=data,
            dims=dims,
            spatial_dims=spatial_dims,
            window_funcs=window_funcs,
            window_order=window_order,
            spatial_func=spatial_func,
            slider_dim_transforms=slider_dim_transforms,
            name=name,
            **kwargs
        )

        self._nd_graphics.append(nd)
        return nd

    def add_nd_scatter(self, data, dims, spatial_dims, *args, **kwargs):
        # TODO: better func signature here, send all kwargs to processor_kwargs
        self._check_slider_dims(dims, spatial_dims, data, positions=True)

        nd = NDPositions(
            self.ndw.indices,
            self,
            data,
            dims,
            spatial_dims,
            *args,
            graphic_type=ScatterCollection,
            **kwargs,
        )

        self._nd_graphics.append(nd)
        return nd

    def add_nd_timeseries(
        self,
        data,
        dims,
        spatial_dims,
        *args,
        graphic_type: type[
            LineCollection | LineStack | ScatterStack | ImageGraphic
        ] = LineStack,
        x_range_mode: Literal["fixed", "auto"] | None = "auto",
        **kwargs,
    ):
        self._check_slider_dims(dims, spatial_dims, data, positions=True)

        nd = NDTimeseries(
            self.ndw.indices,
            self,
            data,
            dims,
            spatial_dims,
            *args,
            graphic_type=graphic_type,
            linear_selector=True,
            x_range_mode=x_range_mode,
            **kwargs,
        )

        self._nd_graphics.append(nd)
        return nd

    def add_nd_lines(self, data, dims, spatial_dims, *args, **kwargs):
        self._check_slider_dims(dims, spatial_dims, data, positions=True)

        nd = NDPositions(
            self.ndw.indices,
            self,
            data,
            dims,
            spatial_dims,
            *args,
            graphic_type=LineCollection,
            **kwargs,
        )

        self._nd_graphics.append(nd)
        return nd
