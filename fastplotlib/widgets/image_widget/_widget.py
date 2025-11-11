from typing import Callable, Sequence, Literal
from warnings import warn

import numpy as np

from rendercanvas import BaseRenderCanvas

from ...layouts import ImguiFigure as Figure
from ...graphics import ImageGraphic, ImageVolumeGraphic
from ...utils import calculate_figure_shape, quick_min_max, ArrayProtocol
from ...tools import HistogramLUTTool
from ._sliders import ImageWidgetSliders
from ._processor import NDImageProcessor, WindowFuncCallable
from ._properties import ImageWidgetProperty, Indices


IMGUI_SLIDER_HEIGHT = 49


class ImageWidget:
    def __init__(
        self,
        data: ArrayProtocol | Sequence[ArrayProtocol | None] | None,
        processors: NDImageProcessor | Sequence[NDImageProcessor] = NDImageProcessor,
        n_display_dims: Literal[2, 3] | Sequence[Literal[2, 3]] = 2,
        slider_dim_names: Sequence[str] | None = None,  # dim names left -> right
        rgb: bool | Sequence[bool] = False,
        cmap: str | Sequence[str] = "plasma",
        window_funcs: (
            tuple[WindowFuncCallable | None, ...]
            | WindowFuncCallable
            | None
            | Sequence[
                tuple[WindowFuncCallable | None, ...] | WindowFuncCallable | None
            ]
        ) = None,
        window_sizes: (
            tuple[int | None, ...] | Sequence[tuple[int | None, ...] | None]
        ) = None,
        window_order: tuple[int, ...] | Sequence[tuple[int, ...] | None] = None,
        finalizer_func: (
            Callable[[ArrayProtocol], ArrayProtocol]
            | Sequence[Callable[[ArrayProtocol], ArrayProtocol]]
            | None
        ) = None,
        sliders_dim_order: Literal["right", "left"] = "right",
        figure_shape: tuple[int, int] = None,
        names: Sequence[str] = None,
        figure_kwargs: dict = None,
        histogram_widget: bool = True,
        graphic_kwargs: dict | Sequence[dict] = None,
    ):
        """
        This widget facilitates high-level navigation through image stacks, which are arrays containing one or more
        images. It includes sliders for key dimensions such as "t" (time) and "z", enabling users to smoothly navigate
        through one or multiple image stacks simultaneously.

        Allowed dimensions orders for each image stack: Note that each has a an optional (c) channel which refers to
        RGB(A) a channel. So this channel should be either 3 or 4.

        Parameters
        ----------
        data: ArrayProtocol | Sequence[ArrayProtocol | None] | None
            array-like or a list of array-like, each array must have a minimum of 2 dimensions

        processors: NDImageProcessor | Sequence[NDImageProcessor], default NDImageProcessor
            The image processors used for each n-dimensional data array

        n_display_dims: Literal[2, 3] | Sequence[Literal[2, 3]], default 2
            number of display dimensions

        slider_dim_names: Sequence[str], optional
            optional list/tuple of names for each slider dim

        rgb: bool | Sequence[bool], default
            whether or not each data array represents RGB(A) images

        figure_shape: Optional[Tuple[int, int]]
            manually provide the shape for the Figure, otherwise the number of rows and columns is estimated

        figure_kwargs: dict, optional
            passed to ``Figure``

        names: Optional[str]
            gives names to the subplots

        histogram_widget: bool, default False
            make histogram LUT widget for each subplot

        rgb: bool | list[bool], default None
            bool or list of bool for each input data array in the ImageWidget, indicating whether the corresponding
            data arrays are grayscale or RGB(A).

        graphic_kwargs: Any
            passed to each ImageGraphic in the ImageWidget figure subplots

        """

        if figure_kwargs is None:
            figure_kwargs = dict()

        if isinstance(data, ArrayProtocol) or (data is None):
            data = [data]

        elif isinstance(data, (list, tuple)):
            # verify that it's a list of np.ndarray
            if not all([isinstance(d, ArrayProtocol) or d is None for d in data]):
                raise TypeError(
                    f"`data` must be an array-like type or a list/tuple of array-like or None. "
                    f"You have passed the following type {type(data)}"
                )

        else:
            raise TypeError(
                f"`data` must be an array-like type or a list/tuple of array-like or None. "
                f"You have passed the following type {type(data)}"
            )

        if issubclass(processors, NDImageProcessor):
            processors = [processors] * len(data)

        elif isinstance(processors, (tuple, list)):
            if not all([issubclass(p, NDImageProcessor) for p in processors]):
                raise TypeError(
                    f"`processors` must be a `NDImageProcess` class, a subclass of `NDImageProcessor`, or a "
                    f"list/tuple of `NDImageProcess` subclasses. You have passed: {processors}"
                )

        else:
            raise TypeError(
                f"`processors` must be a `NDImageProcess` class, a subclass of `NDImageProcessor`, or a "
                f"list/tuple of `NDImageProcess` subclasses. You have passed: {processors}"
            )

        # subplot layout
        if figure_shape is None:
            if "shape" in figure_kwargs:
                figure_shape = figure_kwargs["shape"]
            else:
                figure_shape = calculate_figure_shape(len(data))

        # Regardless of how figure_shape is computed, below code
        # verifies that figure shape is large enough for the number of image arrays passed
        if figure_shape[0] * figure_shape[1] < len(data):
            original_shape = (figure_shape[0], figure_shape[1])
            figure_shape = calculate_figure_shape(len(data))
            warn(
                f"Original `figure_shape` was: {original_shape} "
                f" but data length is {len(data)}"
                f" Resetting figure shape to: {figure_shape}"
            )

        elif isinstance(rgb, bool):
            rgb = [rgb] * len(data)

        if not all([isinstance(v, bool) for v in rgb]):
            raise TypeError(
                f"`rgb` parameter must be a bool or a Sequence of bool, you have passed: {rgb}"
            )

        if not len(rgb) == len(data):
            raise ValueError(
                f"len(rgb) != len(data), {len(rgb)} != {len(data)}. These must be equal"
            )

        if names is not None:
            if not all([isinstance(n, str) for n in names]):
                raise TypeError("optional argument `names` must be a Sequence of str")

            if len(names) != len(data):
                raise ValueError(
                    "number of `names` for subplots must be same as the number of data arrays"
                )

        # verify window funcs
        if window_funcs is None:
            win_funcs = [None] * len(data)

        elif callable(window_funcs) or all(
            [callable(f) or f is None for f in window_funcs]
        ):
            # across all data arrays
            # one window function defined for all dims, or window functions defined per-dim
            win_funcs = [window_funcs] * len(data)

        # if the above two clauses didn't trigger, then window_funcs defined per-dim, per data array
        elif len(window_funcs) != len(data):
            raise IndexError
        else:
            win_funcs = window_funcs

        # verify window sizes
        if window_sizes is None:
            win_sizes = [window_sizes] * len(data)

        elif isinstance(window_sizes, int):
            win_sizes = [window_sizes] * len(data)

        elif all([isinstance(size, int) or size is None for size in window_sizes]):
            # window sizes defined per-dim across all data arrays
            win_sizes = [window_sizes] * len(data)

        elif len(window_sizes) != len(data):
            # window sizes defined per-dim, per data array
            raise IndexError
        else:
            win_sizes = window_sizes

        # verify window orders
        if window_order is None:
            win_order = [None] * len(data)

        elif all([isinstance(o, int) for o in order]):
            # window order defined per-dim across all data arrays
            win_order = [window_order] * len(data)

        elif len(window_order) != len(data):
            raise IndexError

        else:
            win_order = window_order

        # verify finalizer function
        if finalizer_func is None:
            final_funcs = [None] * len(data)

        elif callable(finalizer_func):
            # same finalizer func for all data arrays
            final_funcs = [finalizer_func] * len(data)

        elif len(finalizer_func) != len(data):
            raise IndexError

        else:
            final_funcs = finalizer_func

        # verify number of display dims
        if isinstance(n_display_dims, (int, np.integer)):
            n_display_dims = [n_display_dims] * len(data)

        elif isinstance(n_display_dims, (tuple, list)):
            if not all([isinstance(n, (int, np.integer)) for n in n_display_dims]):
                raise TypeError

            if len(n_display_dims) != len(data):
                raise IndexError
        else:
            raise TypeError

        n_display_dims = tuple(n_display_dims)

        if sliders_dim_order not in ("right",):
            raise ValueError(
                f"Only 'right' slider dims order is currently supported, you passed: {sliders_dim_order}"
            )
        self._sliders_dim_order = sliders_dim_order

        self._slider_dim_names = None
        self.slider_dim_names = slider_dim_names

        self._histogram_widget = histogram_widget

        # make NDImageArrays
        self._image_processors: list[NDImageProcessor] = list()
        for i in range(len(data)):
            cls = processors[i]
            image_processor = cls(
                data=data[i],
                rgb=rgb[i],
                n_display_dims=n_display_dims[i],
                window_funcs=win_funcs[i],
                window_sizes=win_sizes[i],
                window_order=win_order[i],
                finalizer_func=final_funcs[i],
                compute_histogram=self._histogram_widget,
            )

            self._image_processors.append(image_processor)

        self._data = ImageWidgetProperty(self, "data")
        self._rgb = ImageWidgetProperty(self, "rgb")
        self._n_display_dims = ImageWidgetProperty(self, "n_display_dims")
        self._window_funcs = ImageWidgetProperty(self, "window_funcs")
        self._window_sizes = ImageWidgetProperty(self, "window_sizes")
        self._window_order = ImageWidgetProperty(self, "window_order")
        self._finalizer_func = ImageWidgetProperty(self, "finalizer_func")

        if len(set(n_display_dims)) > 1:
            # assume user wants one controller for 2D images and another for 3D image volumes
            n_subplots = np.prod(figure_shape)
            controller_ids = [0] * n_subplots
            controller_types = ["panzoom"] * n_subplots

            for i in range(len(data)):
                if n_display_dims[i] == 2:
                    controller_ids[i] = 1
                else:
                    controller_ids[i] = 2
                    controller_types[i] = "orbit"

            # needs to be a list of list
            controller_ids = [controller_ids]

        else:
            controller_ids = "sync"
            controller_types = None

        figure_kwargs_default = {
            "controller_ids": controller_ids,
            "controller_types": controller_types,
            "names": names,
        }

        # update the default kwargs with any user-specified kwargs
        # user specified kwargs will overwrite the defaults
        figure_kwargs_default.update(figure_kwargs)
        figure_kwargs_default["shape"] = figure_shape

        if graphic_kwargs is None:
            graphic_kwargs = [dict()] * len(data)

        elif isinstance(graphic_kwargs, dict):
            graphic_kwargs = [graphic_kwargs] * len(data)

        elif len(graphic_kwargs) != len(data):
            raise IndexError

        if cmap is None:
            cmap = [None] * len(data)

        elif isinstance(cmap, str):
            cmap = [cmap] * len(data)

        elif not all([isinstance(c, str) for c in cmap]):
            raise TypeError(f"`cmap` must be a <str> or a list/tuple of <str>")

        self._figure: Figure = Figure(**figure_kwargs_default)

        self._indices = Indices(list(0 for i in range(self.n_sliders)), self)

        for i, subplot in zip(range(len(self._image_processors)), self.figure):
            image_data = self._get_image(
                self._image_processors[i], tuple(self._indices)
            )

            if image_data is None:
                # this subplot/data array is blank, skip
                continue

            # next 20 lines are just vmin, vmax parsing
            vmin_specified, vmax_specified = None, None
            if "vmin" in graphic_kwargs[i].keys():
                vmin_specified = graphic_kwargs[i].pop("vmin")
            if "vmax" in graphic_kwargs[i].keys():
                vmax_specified = graphic_kwargs[i].pop("vmax")

            if (vmin_specified is None) or (vmax_specified is None):
                # if either vmin or vmax are not specified, calculate an estimate by subsampling
                vmin_estimate, vmax_estimate = quick_min_max(
                    self._image_processors[i].data
                )

                # decide vmin, vmax passed to ImageGraphic constructor based on whether it's user specified or now
                if vmin_specified is None:
                    # user hasn't specified vmin, use estimated value
                    vmin = vmin_estimate
                else:
                    # user has provided a specific value, use that
                    vmin = vmin_specified

                if vmax_specified is None:
                    vmax = vmax_estimate
                else:
                    vmax = vmax_specified
            else:
                # both vmin and vmax are specified
                vmin, vmax = vmin_specified, vmax_specified

            graphic_kwargs[i]["cmap"] = cmap[i]

            if self._image_processors[i].n_display_dims == 2:
                # create an Image
                graphic = ImageGraphic(
                    data=image_data,
                    name="image_widget_managed",
                    vmin=vmin,
                    vmax=vmax,
                    **graphic_kwargs[i],
                )
            elif self._image_processors[i].n_display_dims == 3:
                # create an ImageVolume
                graphic = ImageVolumeGraphic(
                    data=image_data,
                    name="image_widget_managed",
                    vmin=vmin,
                    vmax=vmax,
                    **graphic_kwargs[i],
                )
                subplot.camera.fov = 50

            subplot.add_graphic(graphic)

            self._reset_histogram(subplot, self._image_processors[i])

        self._sliders_ui = ImageWidgetSliders(
            figure=self.figure,
            size=57 + (IMGUI_SLIDER_HEIGHT * self.n_sliders),
            location="bottom",
            title="ImageWidget Controls",
            image_widget=self,
        )

        self.figure.add_gui(self._sliders_ui)

        self._indices_changed_handlers = set()

        self._reentrant_block = False

    @property
    def data(self) -> ImageWidgetProperty[ArrayProtocol | None]:
        """get or set the nd-image data arrays"""
        return self._data

    @data.setter
    def data(self, new_data: Sequence[ArrayProtocol | None]):
        if isinstance(new_data, ArrayProtocol) or new_data is None:
            new_data = [new_data] * len(self._image_processors)

        if len(new_data) != len(self._image_processors):
            raise IndexError

        # if the data array hasn't been changed
        # graphics will not be reset for this data index
        skip_indices = list()

        for i, (new_data, image_processor) in enumerate(
            zip(new_data, self._image_processors)
        ):
            if new_data is image_processor.data:
                skip_indices.append(i)
                continue

            image_processor.data = new_data

        self._reset(skip_indices)

    @property
    def rgb(self) -> ImageWidgetProperty[bool]:
        """get or set the rgb toggle for each data array"""
        return self._rgb

    @rgb.setter
    def rgb(self, rgb: Sequence[bool]):
        if isinstance(rgb, bool):
            rgb = [rgb] * len(self._image_processors)

        if len(rgb) != len(self._image_processors):
            raise IndexError

        # if the rgb option hasn't been changed
        # graphics will not be reset for this data index
        skip_indices = list()

        for i, (new, image_processor) in enumerate(zip(rgb, self._image_processors)):
            if image_processor.rgb == new:
                skip_indices.append(i)
                continue

            image_processor.rgb = new

        self._reset(skip_indices)

    @property
    def n_display_dims(self) -> ImageWidgetProperty[Literal[2, 3]]:
        """Get or set the number of display dimensions for each data array, 2 is a 2D image, 3 is a 3D volume image"""
        return self._n_display_dims

    @n_display_dims.setter
    def n_display_dims(self, new_ndd: Sequence[Literal[2, 3]] | Literal[2, 3]):
        if isinstance(new_ndd, (int, np.integer)):
            if new_ndd == 2 or new_ndd == 3:
                new_ndd = [new_ndd] * len(self._image_processors)
            else:
                raise ValueError

        if len(new_ndd) != len(self._image_processors):
            raise IndexError

        if not all([(n == 2) or (n == 3) for n in new_ndd]):
            raise ValueError

        # if the n_display_dims hasn't been changed for this data array
        # graphics will not be reset for this data array index
        skip_indices = list()

        # first update image arrays
        for i, (image_processor, new) in enumerate(
            zip(self._image_processors, new_ndd)
        ):
            if new > image_processor.max_n_display_dims:
                raise IndexError(
                    f"number of display dims exceeds maximum number of possible "
                    f"display dimensions: {image_processor.max_n_display_dims}, for array at index: "
                    f"{i} with shape: {image_processor.shape}, and rgb set to: {image_processor.rgb}"
                )

            if image_processor.n_display_dims == new:
                skip_indices.append(i)
            else:
                image_processor.n_display_dims = new

        self._reset(skip_indices)

    @property
    def window_funcs(self) -> ImageWidgetProperty[tuple[WindowFuncCallable | None] | None]:
        """get or set the window functions"""
        return self._window_funcs

    @window_funcs.setter
    def window_funcs(self, new_funcs: Sequence[WindowFuncCallable | None] | None):
        if callable(new_funcs) or new_funcs is None:
            new_funcs = [new_funcs] * len(self._image_processors)

        if len(new_funcs) != len(self._image_processors):
            raise IndexError

        self._set_image_processor_funcs("window_funcs", new_funcs)

    @property
    def window_sizes(self) -> ImageWidgetProperty[tuple[int | None, ...] | None]:
        """get or set the window sizes"""
        return self._window_sizes

    @window_sizes.setter
    def window_sizes(
        self, new_sizes: Sequence[tuple[int | None, ...] | int | None] | int | None
    ):
        if isinstance(new_sizes, int) or new_sizes is None:
            # same window for all data arrays
            new_sizes = [new_sizes] * len(self._image_processors)

        if len(new_sizes) != len(self._image_processors):
            raise IndexError

        self._set_image_processor_funcs("window_sizes", new_sizes)

    @property
    def window_order(self) -> ImageWidgetProperty[tuple[int, ...] | None]:
        """get or set order in which window functions are applied over dimensions"""
        return self._window_order

    @window_order.setter
    def window_order(self, new_order: Sequence[tuple[int, ...]]):
        if new_order is None:
            new_order = [new_order] * len(self._image_processors)

        if all([isinstance(order, (int, np.integer))] for order in new_order):
            # same order specified across all data arrays
            new_order = [new_order] * len(self._image_processors)

        if len(new_order) != len(self._image_processors):
            raise IndexError

        self._set_image_processor_funcs("window_order", new_order)

    @property
    def finalizer_func(self) -> ImageWidgetProperty[Callable | None]:
        """Get or set a finalizer function that operates on the spatial dimensions of the 2D or 3D image"""
        return self._finalizer_func

    @finalizer_func.setter
    def finalizer_func(self, funcs: Callable | Sequence[Callable] | None):
        if callable(funcs) or funcs is None:
            funcs = [funcs] * len(self._image_processors)

        if len(funcs) != len(self._image_processors):
            raise IndexError

        self._set_image_processor_funcs("finalizer_func", funcs)

    def _set_image_processor_funcs(self, attr, new_values):
        """sets window_funcs, window_sizes, window_order, or finalizer_func and updates displayed data and histograms"""
        for new, image_processor, subplot in zip(
            new_values, self._image_processors, self.figure
        ):
            if getattr(image_processor, attr) == new:
                continue

            setattr(image_processor, attr, new)

            # window functions and finalizer functions will only change the histogram
            # they do not change the collections of dimensions, so we don't need to call _reset_dimensions
            # they also do not change the image graphic, so we do not need to call _reset_image_graphics
            self._reset_histogram(subplot, image_processor)

        # update the displayed image data in the graphics
        self.indices = self.indices

    @property
    def indices(self) -> ImageWidgetProperty[int]:
        """
        Get or set the current indices.

        Returns
        -------
        indices: ImageWidgetProperty[int]
            integer index for each slider dimension

        """
        return self._indices

    @indices.setter
    def indices(self, new_indices: Sequence[int]):
        if self._reentrant_block:
            return

        try:
            self._reentrant_block = True  # block re-execution until new_indices has *fully* completed execution

            if len(new_indices) != self.n_sliders:
                raise IndexError(
                    f"len(new_indices) != ImageWidget.n_sliders, {len(new_indices)} != {self.n_sliders}. "
                    f"The length of the new_indices must be the same as the number of sliders"
                )

            if any([i < 0 for i in new_indices]):
                raise IndexError(
                    f"only positive index values are supported, you have passed: {new_indices}"
                )

            for image_processor, graphic in zip(self._image_processors, self.graphics):
                new_data = self._get_image(image_processor, indices=new_indices)
                if new_data is None:
                    continue

                graphic.data = new_data

            self._indices._fpl_set(new_indices)

            # call any event handlers
            for handler in self._indices_changed_handlers:
                handler(self.indices)

        except Exception as exc:
            # raise original exception
            raise exc  # indices setter has raised. The lines above below are probably more relevant!
        finally:
            # set_value has finished executing, now allow future executions
            self._reentrant_block = False

    @property
    def histogram_widget(self) -> bool:
        """show or hide the histograms"""
        return self._histogram_widget

    @histogram_widget.setter
    def histogram_widget(self, show_histogram: bool):
        if not isinstance(show_histogram, bool):
            raise TypeError(
                f"`histogram_widget` can be set with a bool, you have passed: {show_histogram}"
            )

        for subplot, image_processor in zip(self.figure, self._image_processors):
            image_processor.compute_histogram = show_histogram
            self._reset_histogram(subplot, image_processor)

    @property
    def n_sliders(self) -> int:
        """number of sliders"""
        return max([a.n_slider_dims for a in self._image_processors])

    @property
    def bounds(self) -> tuple[int, ...]:
        """The max bound across all dimensions across all data arrays"""
        # initialize with 0
        bounds = [0] * self.n_sliders

        # TODO: implement left -> right slider dims ordering, right now it's only right -> left
        # in reverse because dims go left <- right
        for i, dim in enumerate(range(-1, -self.n_sliders - 1, -1)):
            # across each dim
            for array in self._image_processors:
                if i > array.n_slider_dims - 1:
                    continue
                # across each data array
                # dims go left <- right
                bounds[dim] = max(array.slider_dims_shape[dim], bounds[dim])

        return bounds

    @property
    def slider_dim_names(self) -> tuple[str, ...]:
        return self._slider_dim_names

    @slider_dim_names.setter
    def slider_dim_names(self, names: Sequence[str]):
        if names is None:
            self._slider_dim_names = None
            return

        if not all([isinstance(n, str) for n in names]):
            raise TypeError(f"`slider_dim_names` must be set with a list/tuple of <str>, you passed: {names}")

        if len(set(names)) != len(names):
            raise ValueError(
                f"`slider_dim_names` must be unique, you passed: {names}"
            )

        self._slider_dim_names = tuple(names)

    def _get_image(
        self, image_processor: NDImageProcessor, indices: Sequence[int]
    ) -> ArrayProtocol:
        """Get a processed 2d or 3d image from the NDImage at the given indices"""
        n = image_processor.n_slider_dims

        if self._sliders_dim_order == "right":
            return image_processor.get(indices[-n:])

        elif self._sliders_dim_order == "left":
            # TODO: left -> right is not fully implemented yet in ImageWidget
            return image_processor.get(indices[:n])

    def _reset_dimensions(self):
        """reset the dimensions w.r.t. current collection of NDImageProcessors"""
        # TODO: implement left -> right slider dims ordering, right now it's only right -> left
        # add or remove dims from indices
        # trim any excess dimensions
        while len(self._indices) > self.n_sliders:
            # remove outer most dims first
            self._indices.pop_dim()
            self._sliders_ui.pop_dim()

        # add any new dimensions that aren't present
        while len(self.indices) < self.n_sliders:
            # insert right -> left
            self._indices.push_dim()
            self._sliders_ui.push_dim()

        self._sliders_ui.size = 57 + (IMGUI_SLIDER_HEIGHT * self.n_sliders)

    def _reset_image_graphics(self, subplot, image_processor):
        """delete and create a new image graphic if necessary"""
        new_image = self._get_image(image_processor, indices=tuple(self.indices))
        if new_image is None:
            if "image_widget_managed" in subplot:
                # delete graphic from this subplot if present
                subplot.delete_graphic(subplot["image_widget_managed"])
            # skip this subplot
            return

        # check if a graphic exists
        if "image_widget_managed" in subplot:
            # create a new graphic only if the Texture buffer shape doesn't match
            if subplot["image_widget_managed"].data.value.shape == new_image.shape:
                return

            # keep cmap
            cmap = subplot["image_widget_managed"].cmap
            if cmap is None:
                # ex: going from rgb -> grayscale
                cmap = "plasma"
            # delete graphic since it will be replaced
            subplot.delete_graphic(subplot["image_widget_managed"])
        else:
            # default cmap
            cmap = "plasma"

        if image_processor.n_display_dims == 2:
            g = subplot.add_image(
                data=new_image, cmap=cmap, name="image_widget_managed"
            )

            # set camera orthogonal to the xy plane, flip y axis
            subplot.camera.set_state(
                {
                    "position": [0, 0, -1],
                    "rotation": [0, 0, 0, 1],
                    "scale": [1, -1, 1],
                    "reference_up": [0, 1, 0],
                    "fov": 0,
                    "depth_range": None,
                }
            )

            subplot.controller = "panzoom"
            subplot.axes.intersection = None
            subplot.auto_scale()

        elif image_processor.n_display_dims == 3:
            g = subplot.add_image_volume(
                data=new_image, cmap=cmap, name="image_widget_managed"
            )
            subplot.camera.fov = 50
            subplot.controller = "orbit"

            # make sure all 3D dimension camera scales are positive
            # MIP rendering doesn't work with negative camera scales
            for dim in ["x", "y", "z"]:
                if getattr(subplot.camera.local, f"scale_{dim}") < 0:
                    setattr(subplot.camera.local, f"scale_{dim}", 1)

            subplot.auto_scale()

    def _reset_histogram(self, subplot, image_processor):
        """reset the histogram"""
        if not self._histogram_widget:
            subplot.docks["right"].size = 0
            return

        if image_processor.histogram is None:
            # no histogram available for this processor
            # either there is no data array in this subplot,
            # or a histogram routine does not exist for this processor
            subplot.docks["right"].size = 0
            return

        if "image_widget_managed" not in subplot:
            # no image in this subplot
            subplot.docks["right"].size = 0
            return

        image = subplot["image_widget_managed"]

        if "histogram_lut" in subplot.docks["right"]:
            hlut: HistogramLUTTool = subplot.docks["right"]["histogram_lut"]
            hlut.histogram = image_processor.histogram
            hlut.images = image
            if subplot.docks["right"].size < 1:
                subplot.docks["right"].size = 80

        else:
            # need to make one
            hlut = HistogramLUTTool(
                histogram=image_processor.histogram,
                images=image,
                name="histogram_lut",
            )

            subplot.docks["right"].add_graphic(hlut)
            subplot.docks["right"].size = 80

        self.reset_vmin_vmax()

    def _reset(self, skip_data_indices: tuple[int, ...] = None):
        if skip_data_indices is None:
            skip_data_indices = tuple()

        # reset the slider indices according to the new collection of dimensions
        self._reset_dimensions()
        # update graphics where display dims have changed accordings to indices
        for i, (subplot, image_processor) in enumerate(
            zip(self.figure, self._image_processors)
        ):
            if i in skip_data_indices:
                continue

            self._reset_image_graphics(subplot, image_processor)
            self._reset_histogram(subplot, image_processor)

        # force an update
        self.indices = self.indices

    @property
    def figure(self) -> Figure:
        """
        ``Figure`` used by `ImageWidget`.
        """
        return self._figure

    @property
    def graphics(self) -> list[ImageGraphic]:
        """List of ``ImageWidget`` managed graphics."""
        iw_managed = list()
        for subplot in self.figure:
            if "image_widget_managed" in subplot:
                iw_managed.append(subplot["image_widget_managed"])
            else:
                iw_managed.append(None)
        return tuple(iw_managed)

    @property
    def cmap(self) -> tuple[str, ...]:
        """get the cmaps, or set the cmap across all images"""
        return tuple(g.cmap for g in self.graphics)

    @cmap.setter
    def cmap(self, name: str):
        for g in self.graphics:
            g.cmap = name

    def add_event_handler(self, handler: callable, event: str = "indices"):
        """
        Register an event handler.

        Currently the only event that ImageWidget supports is "indices". This event is
        emitted whenever the indices of the ImageWidget changes.

        Parameters
        ----------
        handler: callable
            callback function, must take a tuple of int as the only argument. This tuple will be the `indices`

        event: str, "indices"
            the only supported event is "indices"

        Example
        -------

        .. code-block:: py

            def my_handler(indices):
                print(indices)
                # example prints: (100, 15) if the data has 2 slider dimensions with sliders at positions 100, 15

            # create an image widget
            iw = ImageWidget(...)

            # add event handler
            iw.add_event_handler(my_handler)

        """
        if event != "indices":
            raise ValueError("`indices` is the only event supported by `ImageWidget`")

        self._indices_changed_handlers.add(handler)

    def remove_event_handler(self, handler: callable):
        """Remove a registered event handler"""
        self._indices_changed_handlers.remove(handler)

    def clear_event_handlers(self):
        """Clear all registered event handlers"""
        self._indices_changed_handlers.clear()

    def reset_vmin_vmax(self):
        """
        Reset the vmin and vmax w.r.t. the full data
        """
        for image_processor, subplot in zip(self._image_processors, self.figure):
            if "histogram_lut" not in subplot.docks["right"]:
                continue

            hlut = subplot.docks["right"]["histogram_lut"]
            hlut.histogram = image_processor.histogram

            edges = image_processor.histogram[1]
            hlut.vmin, hlut.vmax = edges[0], edges[-1]

    def reset_vmin_vmax_frame(self):
        """
        Resets the vmin vmax and HistogramLUT widgets w.r.t. the current data shown in the
        ImageGraphic instead of the data in the full data array. For example, if a post-processing
        function is used, the range of values in the ImageGraphic can be very different from the
        range of values in the full data array.
        """

        for subplot in self.figure:
            if "histogram_lut" not in subplot.docks["right"]:
                continue

            hlut = subplot.docks["right"]["histogram_lut"]
            # set the data using the current image graphic data
            image = subplot["image_widget_managed"]
            freqs, edges = np.histogram(image.data.value, bins=100)
            hlut.histogram = (freqs, edges)
            hlut.vmin, hlut.vmax = edges[0], edges[-1]

    def show(self, **kwargs):
        """
        Show the widget.

        Parameters
        ----------

        kwargs: Any
            passed to `Figure.show()`t

        Returns
        -------
        BaseRenderCanvas
            In Qt or GLFW, the canvas window containing the Figure will be shown.
            In jupyter, it will display the plot in the output cell or sidecar.

        """

        return self.figure.show(**kwargs)

    def close(self):
        """Close Widget"""
        self.figure.close()
