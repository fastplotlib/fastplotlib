from ..plot import Plot
from ..layouts import GridPlot
from ..graphics import Image
from ipywidgets.widgets import IntSlider, VBox, HBox
import numpy as np
from typing import *
from warnings import warn


DEFAULT_AXES_ORDER = \
    {
        2: "xy",
        3: "txy",
        4: "tzxy",
        5: "tczxy",
    }


def calc_gridshape(n):
    sr = np.sqrt(n)
    return (
        np.ceil(sr),
        np.round(sr)
    )


class ImageWidget:
    def __init__(
            self,
            data: Union[np.ndarray, List[np.ndarray]],
            axes_order: str = None,
            slider_sync: bool = True,
            slider_axes: Union[int, str, dict] = None,
            frame_apply: Union[callable, dict] = None,
            grid_shape: Tuple[int, int] = None,
    ):
        # single image
        if isinstance(data, np.ndarray):
                self.plot_type = Plot
                self.data: List[np.ndarray] = [data]
                ndim = data[0].ndim

        # list of lists
        elif isinstance(data, list):
            if all([isinstance(d, np.ndarray) for d in data]):
                self.plot_type = GridPlot

                if grid_shape is None:
                    grid_shape = calc_gridshape(len(data))

                elif grid_shape[0] * grid_shape[1] < len(data):
                    grid_shape = calc_gridshape(len(data))
                    warn(f"Invalid `grid_shape` passed, setting grid shape to: {grid_shape}")

                _ndim = [d.ndim for d in data]

                if not len(set(_ndim)) == 1:
                    raise ValueError(
                        f"Number of dimensions of all data arrays must match, your ndims are: {_ndim}"
                    )

                self.data: List[np.ndarray] = data
                ndim = data[0].ndim

        else:
            raise TypeError(
                f"`data` must be of type `numpy.ndarray` representing a single image/image sequence "
                f"or a  list of `numpy.ndarray` representing a grid of images/image sequences"
            )

        if axes_order is None:
            self.axes_order: List[str] = [DEFAULT_AXES_ORDER[ndim] for i in range(len(data))]

        if isinstance(slider_axes, (int)):
            self._slider_axes: List[int] = [slider_axes for i in range(len(data))]

        elif isinstance(slider_axes, str):
            self._slider_axes: List[int] = [self.axes_order.index(slider_axes)]

        self.sliders: List[IntSlider] = [
            IntSlider(
                min=0,
                max=data.shape[slider_axes] - 1,
                value=0,
                step=1,
                description=f"slider axis: {slider_axes}"
            )
        ]

    def slider_changed(self):
        pass

    def show(self):
        pass
