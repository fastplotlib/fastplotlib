import inspect
from typing import Literal, Callable, Any, Type
from warnings import warn

import numpy as np
from numpy.typing import ArrayLike

from ...utils import subsample_array, ArrayProtocol

from ...graphics import ImageGraphic, LineGraphic, LineStack, LineCollection, ScatterGraphic
from ._processor_base import NDProcessor

# TODO: Maybe get rid of n_display_dims in NDProcessor,
#  we will know the display dims automatically here from the last dim
#  so maybe we only need it for images?
class NDPositionsProcessor(NDProcessor):
    def __init__(
            self,
            data: ArrayProtocol,
            multi: bool = False,  # TODO: interpret [n - 2] dimension as n_lines or n_points
            display_window: int | float | None = 100,  # window for n_datapoints dim only
    ):
        super().__init__(data=data)

        self._display_window = display_window

        self.multi = multi

    def _validate_data(self, data: ArrayProtocol):
        # TODO: determine right validation shape etc.
        return data

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
    def multi(self) -> bool:
        return self._multi

    @multi.setter
    def multi(self, m: bool):
        if m and self.data.ndim < 3:
            # p is p-datapoints, n is how many lines/scatter to show simultaneously
            raise ValueError("ndim must be >= 3 for multi, shape must be [s1..., sn, n, p, 2 | 3]")

        self._multi = m

    def __getitem__(self, indices: tuple[Any, ...]):
        """sliders through all slider dims and outputs an array that can be used to set graphic data"""
        if self.display_window is not None:
            indices_window = self.display_window

            # half window size
            hw = indices_window // 2

            # for now assume just a single index provided that indicates x axis value
            start = max(indices - hw, 0)
            stop = start + indices_window

            slices = [slice(start, stop)]

            # TODO: implement slicing for multiple slider dims, i.e. [s1, s2, ... n_datapoints, 2 | 3]
            #  this currently assumes the shape is: [n_datapoints, 2 | 3]
            if self.multi:
                # n - 2 dim is n_lines or n_scatters
                slices.insert(0, slice(None))

            return self.data[tuple(slices)]


class NDPositions:
    def __init__(self, data, graphic: Type[LineGraphic | LineCollection | LineStack | ScatterGraphic], multi: bool = False):
        self._indices = 0

        if issubclass(graphic, LineCollection):
            multi = True

        self._processor = NDPositionsProcessor(data, multi=multi)

        self._create_graphic(graphic)

    @property
    def processor(self) -> NDPositionsProcessor:
        return self._processor

    @property
    def graphic(self) -> LineGraphic | LineCollection | LineStack | ScatterGraphic | list[ScatterGraphic]:
        """LineStack or ImageGraphic for heatmaps"""
        return self._graphic

    @property
    def indices(self) -> tuple:
        return self._indices

    @indices.setter
    def indices(self, indices):
        data_slice = self.processor[indices]

        if isinstance(self.graphic, list):
            # list of scatter
            for i in range(len(self.graphic)):
                # data_slice shape is [n_scatters, n_datapoints, 2 | 3]
                # by using data_slice.shape[-1] it will auto-select if the data is only xy or has xyz
                self.graphic[i].data[:, :data_slice.shape[-1]] = data_slice[i]

        elif isinstance(self.graphic, (LineGraphic, ScatterGraphic)):
            self.graphic.data[:, :data_slice.shape[-1]] = data_slice

        elif isinstance(self.graphic, LineCollection):
            for i in range(len(self.graphic)):
                # data_slice shape is [n_lines, n_datapoints, 2 | 3]
                self.graphic[i].data[:, :data_slice.shape[-1]] = data_slice[i]

    def _create_graphic(self, graphic_cls: Type[LineGraphic | LineCollection | LineStack | ScatterGraphic]):
        if self.processor.multi and issubclass(graphic_cls, ScatterGraphic):
            # make list of scatters
            self._graphic = list()
            data_slice = self.processor[self.indices]
            for d in data_slice:
                scatter = graphic_cls(d)
                self._graphic.append(scatter)

        else:
            data_slice = self.processor[self.indices]
            self._graphic = graphic_cls(data_slice)
