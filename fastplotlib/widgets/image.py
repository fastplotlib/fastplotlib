from ..plot import Plot
from ..layouts import GridPlot
from ..graphics import Image
from ipywidgets.widgets import IntSlider, VBox, HBox, Layout
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


def get_indexer(ndim: int, dim_index: int, slice_index: int) -> slice:
    dim_index = [slice(None)] * ndim
    dim_index[dim_index] = slice_index
    return tuple(dim_index)


class ImageWidget:
    def __init__(
            self,
            data: Union[np.ndarray, List[np.ndarray]],
            axes_order: str = None,
            slider_sync: bool = True,
            slider_axes: Union[int, str, dict] = None,
            frame_apply: Union[callable, dict] = None,
            grid_shape: Tuple[int, int] = None,
            **kwargs
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

        # if a single one is provided
        if isinstance(slider_axes, (int, str)):
            if isinstance(slider_axes, (int)):
                self._slider_axes = slider_axes

            # also if a single one is provided, get the integer dimension index from the axes_oder string
            elif isinstance(slider_axes, str):
                self._slider_axes = self.axes_order.index(slider_axes)

            self.slider: IntSlider = IntSlider(
                min=0,
                max=data.shape[self._slider_axes] - 1,
                value=0,
                step=1,
                description=f"slider axis: {self._slider_axes}"
            )

        # individual slider for each data array
        elif isinstance(slider_axes, dict):
            if not len(slider_axes.keys()) == len(self.data):
                raise ValueError(
                    f"Must provide slider_axes entry for every input `data` array"
                )

            if not isinstance(axes_order, dict):
                raise ValueError("Must pass `axes_order` dict if passing a dict of `slider_axes`")

            if not len(axes_order.keys()) == len(self.data):
                raise ValueError(
                    f"Must provide `axes_order` entry for every input `data` array"
                )

            # convert str type desired slider axes to dimension index integers
            # matchup to the given axes_order dict
            _axes = [
                self.axes_order[array].index(slider_axes[array])
                    if isinstance(dim_index, str)
                    else dim_index
                        for
                            array, dim_index in slider_axes.items()
            ]

            self.sliders: Dict[IntSlider] = {
                array: IntSlider(
                    min=0,
                    max=array.shape[dim] -1,
                    step=1,
                    value=0,
                )
                for array, dim in self.axes_order.items()
            }

        if self.plot_type == Plot:
            self.plot = Plot()

            slice_index = get_indexer(ndim, self._slider_axes, slice_index=0)

            self.image_graphics: List[Image] = [self.plot.image(
                data=data[0][slice_index],
                **kwargs
            )]

            self.slider.observe(
                lambda x: self.image_graphics[0].update_data(
                    data[0][
                        get_indexer(ndim, self._slider_axes, slice_index=x["new"])
                    ]
                ),
                names="value"
            )

            self.widget = VBox([self.plot, self.slider])

        elif self.plot_type == GridPlot:
            pass

    def set_frame_slider_width(self):
        w, h = self.plot.renderer.logical_size
        self.slider.layout = Layout(width=f"{w}px")

    def slider_changed(self):
        pass

    def show(self):
        pass
