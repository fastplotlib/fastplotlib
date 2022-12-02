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
    indexer = [slice(None)] * ndim
    indexer[dim_index] = slice_index
    return tuple(indexer)


class ImageWidget:
    """
    A high level for displaying n-dimensional image data in conjunction with automatically generated sliders for
    navigating through 1-2 selected dimensions within the image data.

    Can display a single n-dimensional image array or a grid of n-dimensional images.
    """
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
        # if single image array
        if isinstance(data, np.ndarray):
            self.plot_type = Plot
            self.data: List[np.ndarray] = [data]
            ndim = self.data[0].ndim

        # if list of image arrays, list of lists
        elif isinstance(data, list):
            # verify that it's a list of np.ndarray
            if all([isinstance(d, np.ndarray) for d in data]):
                self.plot_type = GridPlot

                if grid_shape is None:
                    grid_shape = calc_gridshape(len(data))

                # verify that user-specified grid shape is large enough for the number of image arrays passed
                elif grid_shape[0] * grid_shape[1] < len(data):
                    grid_shape = calc_gridshape(len(data))
                    warn(f"Invalid `grid_shape` passed, setting grid shape to: {grid_shape}")

                _ndim = [d.ndim for d in data]

                # verify that all image arrays have same number of dimensions
                # sliders get messy otherwise
                if not len(set(_ndim)) == 1:
                    raise ValueError(
                        f"Number of dimensions of all data arrays must match, your ndims are: {_ndim}"
                    )

                self.data: List[np.ndarray] = data
                ndim = self.data[0].ndim

        else:
            raise TypeError(
                f"`data` must be of type `numpy.ndarray` representing a single image/image sequence "
                f"or a  list of `numpy.ndarray` representing a grid of images/image sequences"
            )

        # default axes order if not passed
        if axes_order is None:
            self.axes_order: List[str] = [DEFAULT_AXES_ORDER[ndim] for i in range(len(data))]

        else:
            self.axes_order = axes_order

        # make a slider for "t", the time dimension, if slider_axes is not provided
        if slider_axes is None:
            slider_axes = self.axes_order.index("t")

        # if a single axes is provided for the slider
        if isinstance(slider_axes, (int, str)):
            if isinstance(slider_axes, (int)):
                self._slider_axes = slider_axes

            # if a single one is provided but it is a string, get the integer dimension index from the axes_order
            elif isinstance(slider_axes, str):
                self._slider_axes = self.axes_order.index(slider_axes)

            # a single slider for the desired axis/dimension
            self.slider: IntSlider = IntSlider(
                min=0,
                max=data.shape[self._slider_axes] - 1,
                value=0,
                step=1,
                description=f"slider axis: {self._slider_axes}"
            )

        # individual slider for each data array
        # TODO: not tested and fully implemented yet
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
            # match to the given axes_order dict
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

        # finally create the plot and slider for a single image array
        if self.plot_type == Plot:
            self.plot = Plot()

            # get slice object for dynamically indexing chosen dimension from `self._slider_axes`
            slice_index = get_indexer(ndim, self._slider_axes, slice_index=0)

            # create image graphic
            self.image_graphics: List[Image] = [self.plot.image(
                data=self.data[0][slice_index],
                **kwargs
            )]

            # update frame w.r.t. slider index
            self.slider.observe(
                lambda x: self.image_graphics[0].update_data(
                    self.data[0][
                        get_indexer(ndim, self._slider_axes, slice_index=x["new"])
                    ]
                ),
                names="value"
            )

            self.plot.renderer.add_event_handler(self._set_frame_slider_width, "resize")

            self.widget = VBox([self.plot.canvas, self.slider])

        elif self.plot_type == GridPlot:
            pass

    def _set_frame_slider_width(self, *args):
        w, h = self.plot.renderer.logical_size
        self.slider.layout = Layout(width=f"{w}px")

    def slider_changed(self):
        pass

    def show(self):
        self.plot.show()
        return self.widget
