from collections.abc import Callable
from typing import Literal, Sequence, Hashable

import numpy as np

from ... import ScatterCollection, ScatterStack, LineCollection, LineStack, ImageGraphic
from ...layouts import Subplot
from ...utils import ArrayProtocol
from . import NDImage, NDPositions
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
    def nd_graphics(self) -> tuple[NDGraphic]:
        """all the NDGraphic instance in this subplot"""
        return tuple(self._nd_graphics)

    def __getitem__(self, key):
        # get a specific NDGraphic by index or name
        if isinstance(key, (int, np.integer)):
            return self.nd_graphics[key]

        for g in self.nd_graphics:
            if g.name == key:
                return g

        else:
            raise KeyError(f"NDGraphc with given key not found: {key}")

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
    ):
        nd = NDImage(self.ndw.indices, self._subplot, data=data,
            dims=dims,
            spatial_dims=spatial_dims,
            rgb_dim=rgb_dim,
            window_funcs=window_funcs,
            window_order=window_order,
            spatial_func=spatial_func,
            compute_histogram=compute_histogram,
            slider_dim_transforms=slider_dim_transforms,
            name=name,
         )

        self._nd_graphics.append(nd)
        return nd

    def add_nd_scatter(self, *args, **kwargs):
        # TODO: better func signature here, send all kwargs to processor_kwargs
        nd = NDPositions(
            self.ndw.indices,
            self._subplot,
            *args,
            graphic_type=ScatterCollection,
            **kwargs,
        )

        self._nd_graphics.append(nd)
        return nd

    def add_nd_timeseries(
        self,
        *args,
        graphic_type: type[
            LineCollection | LineStack | ScatterStack | ImageGraphic
        ] = LineStack,
        x_range_mode: Literal["fixed", "auto"] | None = "auto",
        **kwargs,
    ):
        nd = NDPositions(
            self.ndw.indices,
            self._subplot,
            *args,
            graphic_type=graphic_type,
            linear_selector=True,
            x_range_mode=x_range_mode,
            timeseries=True,
            **kwargs,
        )

        self._nd_graphics.append(nd)
        return nd

    def add_nd_lines(self, *args, **kwargs):
        nd = NDPositions(
            self.ndw.indices,
            self._subplot,
            *args,
            graphic_type=LineCollection,
            **kwargs,
        )

        self._nd_graphics.append(nd)
        return nd
