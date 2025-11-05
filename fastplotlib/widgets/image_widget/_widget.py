from typing import Callable
from warnings import warn

import numpy as np

from rendercanvas import BaseRenderCanvas

from ...layouts import ImguiFigure as Figure
from ...graphics import ImageGraphic
from ...utils import calculate_figure_shape, quick_min_max
from ...tools import HistogramLUTTool
from ._sliders import ImageWidgetSliders
from ._array import NDImageView


class ImageWidget:
    @property
    def figure(self) -> Figure:
        """
        ``Figure`` used by `ImageWidget`.
        """
        return self._figure

    @property
    def managed_graphics(self) -> list[ImageGraphic]:
        """List of ``ImageWidget`` managed graphics."""
        iw_managed = list()
        for subplot in self.figure:
            # empty subplots will not have any image widget data
            if len(subplot.graphics) > 0:
                iw_managed.append(subplot["image_widget_managed"])
        return iw_managed

    @property
    def cmap(self) -> list[str]:
        cmaps = list()
        for g in self.managed_graphics:
            cmaps.append(g.cmap)

        return cmaps

    @cmap.setter
    def cmap(self, names: str | list[str]):
        if isinstance(names, list):
            if not all([isinstance(n, str) for n in names]):
                raise TypeError(
                    f"Must pass cmap name as a `str` of list of `str`, you have passed:\n{names}"
                )

            if not len(names) == len(self.managed_graphics):
                raise IndexError(
                    f"If passing a list of cmap names, the length of the list must be the same as the number of "
                    f"image widget subplots. You have passed: {len(names)} cmap names and have "
                    f"{len(self.managed_graphics)} image widget subplots"
                )

            for name, g in zip(names, self.managed_graphics):
                g.cmap = name

        elif isinstance(names, str):
            for g in self.managed_graphics:
                g.cmap = names

    @property
    def data(self) -> list[np.ndarray]:
        """data currently displayed in the widget"""
        return self._data

    @property
    def current_index(self) -> dict[str, int]:
        """
        Get or set the current index

        Returns
        -------
        index: Dict[str, int]
            | ``dict`` for indexing each dimension, provide a ``dict`` with indices for all dimensions used by sliders
            or only a subset of dimensions used by the sliders.
            | example: if you have sliders for dims "t" and "z", you can pass either ``{"t": 10}`` to index to position
            10 on dimension "t" or ``{"t": 5, "z": 20}`` to index to position 5 on dimension "t" and position 20 on
            dimension "z" simultaneously.

        """
        return self._current_index

    @current_index.setter
    def current_index(self, index: dict[str, int]):
        if not self._initialized:
            return

        if self._reentrant_block:
            return

        try:
            self._reentrant_block = True  # block re-execution until current_index has *fully* completed execution
            if not set(index.keys()).issubset(set(self._current_index.keys())):
                raise KeyError(
                    f"All dimension keys for setting `current_index` must be present in the widget sliders. "
                    f"The dimensions currently used for sliders are: {list(self.current_index.keys())}"
                )

            for k, val in index.items():
                if not isinstance(val, int):
                    raise TypeError("Indices for all dimensions must be int")
                if val < 0:
                    raise IndexError(
                        "negative indexing is not supported for ImageWidget"
                    )
                if val > self._dims_max_bounds[k]:
                    raise IndexError(
                        f"index {val} is out of bounds for dimension '{k}' "
                        f"which has a max bound of: {self._dims_max_bounds[k]}"
                    )

            self._current_index.update(index)

            for i, (ig, data) in enumerate(zip(self.managed_graphics, self.data)):
                frame = self._process_indices(data, self._current_index)
                frame = self._process_frame_apply(frame, i)
                ig.data = frame

            # call any event handlers
            for handler in self._current_index_changed_handlers:
                handler(self.current_index)
        except Exception as exc:
            # raise original exception
            raise exc  # current_index setter has raised. The lines above below are probably more relevant!
        finally:
            # set_value has finished executing, now allow future executions
            self._reentrant_block = False

    def __init__(
        self,
        data: np.ndarray | list[np.ndarray],
        array_types: ImageWidgetArray | list[ImageWidgetArray] = ImageWidgetArray,
        window_funcs: dict[str, tuple[Callable, int]] = None,
        frame_apply: Callable | dict[int, Callable] = None,
        figure_shape: tuple[int, int] = None,
        names: list[str] = None,
        figure_kwargs: dict = None,
        histogram_widget: bool = True,
        rgb: bool | list[bool] = None,
        cmap: str = "plasma",
        graphic_kwargs: dict = None,
    ):
        """
        This widget facilitates high-level navigation through image stacks, which are arrays containing one or more
        images. It includes sliders for key dimensions such as "t" (time) and "z", enabling users to smoothly navigate
        through one or multiple image stacks simultaneously.

        Allowed dimensions orders for each image stack: Note that each has a an optional (c) channel which refers to
        RGB(A) a channel. So this channel should be either 3 or 4.

        Parameters
        ----------
        data: Union[np.ndarray, List[np.ndarray]
            array-like or a list of array-like

        window_funcs: dict[str, tuple[Callable, int]], i.e. {"t" or "z": (callable, int)}
            | Apply function(s) with rolling windows along "t" and/or "z" dimensions of the `data` arrays.
            | Pass a dict in the form: {dimension: (func, window_size)}, `func` must take a slice of the data array as
            | the first argument and must take `axis` as a kwarg.
            | Ex: mean along "t" dimension: {"t": (np.mean, 11)}, if `current_index` of "t" is 50, it will pass frames
            | 45 to 55 to `np.mean` with `axis=0`.
            | Ex: max along z dim: {"z": (np.max, 3)}, passes current, previous & next frame to `np.max` with `axis=1`

        frame_apply: Union[callable, Dict[int, callable]]
            | Apply function(s) to `data` arrays before to generate final 2D image that is displayed.
            | Ex: apply a spatial gaussian filter
            | Pass a single function or a dict of functions to apply to each array individually
            | examples: ``{array_index: to_grayscale}``, ``{0: to_grayscale, 2: threshold_img}``
            | "array_index" is the position of the corresponding array in the data list.
            | if `window_funcs` is used, then this function is applied after `window_funcs`
            | this function must be a callable that returns a 2D array
            | example use case: converting an RGB frame from video to a 2D grayscale frame

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
        self._initialized = False

        if figure_kwargs is None:
            figure_kwargs = dict()

        if _is_arraylike(data):
            data = [data]

        if isinstance(data, list):
            # verify that it's a list of np.ndarray
            if all([_is_arraylike(d) for d in data]):
                # Grid computations
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

                self._data: list[np.ndarray] = data

                # Establish number of image dimensions and number of scrollable dimensions for each array
                if rgb is None:
                    rgb = [False] * len(self.data)
                if isinstance(rgb, bool):
                    rgb = [rgb] * len(self.data)
                if not isinstance(rgb, list):
                    raise TypeError(
                        f"`rgb` parameter must be a bool or list of bool, a <{type(rgb)}> was provided"
                    )
                if not len(rgb) == len(self.data):
                    raise ValueError(
                        f"len(rgb) != len(data), {len(rgb)} != {len(self.data)}. These must be equal"
                    )

                if names is not None:
                    if not all([isinstance(n, str) for n in names]):
                        raise TypeError(
                            "optional argument `names` must be a list of str"
                        )

                    if len(names) != len(self.data):
                        raise ValueError(
                            "number of `names` for subplots must be same as the number of data arrays"
                        )

            else:
                raise TypeError(
                    f"If passing a list to `data` all elements must be an "
                    f"array-like type representing an n-dimensional image. "
                    f"You have passed the following types:\n"
                    f"{[type(a) for a in data]}"
                )
        else:
            raise TypeError(
                f"`data` must be an array-like type or a list of array-like."
                f"You have passed the following type {type(data)}"
            )

        # current_index stores {dimension_index: slice_index} for every dimension
        self._current_index: dict[str, int] = {sax: 0 for sax in self.slider_dims}

        figure_kwargs_default = {"controller_ids": "sync", "names": names}

        # update the default kwargs with any user-specified kwargs
        # user specified kwargs will overwrite the defaults
        figure_kwargs_default.update(figure_kwargs)
        figure_kwargs_default["shape"] = figure_shape

        if graphic_kwargs is None:
            graphic_kwargs = dict()

        graphic_kwargs.update({"cmap": cmap})

        vmin_specified, vmax_specified = None, None
        if "vmin" in graphic_kwargs.keys():
            vmin_specified = graphic_kwargs.pop("vmin")
        if "vmax" in graphic_kwargs.keys():
            vmax_specified = graphic_kwargs.pop("vmax")

        self._figure: Figure = Figure(**figure_kwargs_default)

        self._histogram_widget = histogram_widget
        for data_ix, (d, subplot) in enumerate(zip(self.data, self.figure)):

            frame = self._process_indices(d, slice_indices=self._current_index)
            frame = self._process_frame_apply(frame, data_ix)

            if (vmin_specified is None) or (vmax_specified is None):
                # if either vmin or vmax are not specified, calculate an estimate by subsampling
                vmin_estimate, vmax_estimate = quick_min_max(d)

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

            ig = ImageGraphic(
                frame,
                name="image_widget_managed",
                vmin=vmin,
                vmax=vmax,
                **graphic_kwargs,
            )
            subplot.add_graphic(ig)

            if self._histogram_widget:
                hlut = HistogramLUTTool(data=d, images=ig, name="histogram_lut")

                subplot.docks["right"].add_graphic(hlut)
                subplot.docks["right"].size = 80
                subplot.docks["right"].auto_scale(maintain_aspect=False)
                subplot.docks["right"].controller.enabled = False

        # hard code the expected height so that the first render looks right in tests, docs etc.
        if len(self.slider_dims) == 0:
            ui_size = 57
        if len(self.slider_dims) == 1:
            ui_size = 106
        elif len(self.slider_dims) == 2:
            ui_size = 155

        self._image_widget_sliders = ImageWidgetSliders(
            figure=self.figure,
            size=ui_size,
            location="bottom",
            title="ImageWidget Controls",
            image_widget=self,
        )

        self.figure.add_gui(self._image_widget_sliders)

        self._current_index_changed_handlers = set()

        self._reentrant_block = False

        self._initialized = True

    def add_event_handler(self, handler: callable, event: str = "current_index"):
        """
        Register an event handler.

        Currently the only event that ImageWidget supports is "current_index". This event is
        emitted whenever the index of the ImageWidget changes.

        Parameters
        ----------
        handler: callable
            callback function, must take a dict as the only argument. This dict will be the `current_index`

        event: str, "current_index"
            the only supported event is "current_index"

        Example
        -------

        .. code-block:: py

            def my_handler(index):
                print(index)
                # example prints: {"t": 100} if data has only time dimension
                # "z" index will be another key if present in the data, ex: {"t": 100, "z": 5}

            # create an image widget
            iw = ImageWidget(...)

            # add event handler
            iw.add_event_handler(my_handler)

        """
        if event != "current_index":
            raise ValueError(
                "`current_index` is the only event supported by `ImageWidget`"
            )

        self._current_index_changed_handlers.add(handler)

    def remove_event_handler(self, handler: callable):
        """Remove a registered event handler"""
        self._current_index_changed_handlers.remove(handler)

    def clear_event_handlers(self):
        """Clear all registered event handlers"""
        self._current_index_changed_handlers.clear()

    def reset_vmin_vmax(self):
        """
        Reset the vmin and vmax w.r.t. the full data
        """
        for data, subplot in zip(self.data, self.figure):
            if "histogram_lut" not in subplot.docks["right"]:
                continue
            hlut = subplot.docks["right"]["histogram_lut"]
            hlut.set_data(data, reset_vmin_vmax=True)

    def reset_vmin_vmax_frame(self):
        """
        Resets the vmin vmax and HistogramLUT widgets w.r.t. the current data shown in the
        ImageGraphic instead of the data in the full data array. For example, if a post-processing
        function is used, the range of values in the ImageGraphic can be very different from the
        range of values in the full data array.

        TODO: We could think of applying the frame_apply funcs to a subsample of the entire array to get a better estimate of vmin vmax?
        """

        for subplot in self.figure:
            if "histogram_lut" not in subplot.docks["right"]:
                continue

            hlut = subplot.docks["right"]["histogram_lut"]
            # set the data using the current image graphic data
            hlut.set_data(subplot["image_widget_managed"].data.value)

    def set_data(
        self,
        new_data: np.ndarray | list[np.ndarray],
        reset_vmin_vmax: bool = True,
        reset_indices: bool = True,
    ):
        """
        Change data of widget. Note: sliders max currently update only for ``txy`` and ``tzxy`` data.

        Parameters
        ----------
        new_data: array-like or list of array-like
            The new data to display in the widget

        reset_vmin_vmax: bool, default ``True``
            reset the vmin vmax levels based on the new data

        reset_indices: bool, default ``True``
            reset the current index for all dimensions to 0

        """

        if reset_indices:
            for key in self.current_index:
                self.current_index[key] = 0

        # set slider max according to new data
        max_lengths = dict()
        for scroll_dim in self.slider_dims:
            max_lengths[scroll_dim] = np.inf

        if _is_arraylike(new_data):
            new_data = [new_data]

        if len(self._data) != len(new_data):
            raise ValueError(
                f"number of new data arrays {len(new_data)} must match"
                f" current number of data arrays {len(self._data)}"
            )
        # check all arrays
        for i, (new_array, current_array) in enumerate(zip(new_data, self._data)):
            if new_array.ndim != current_array.ndim:
                raise ValueError(
                    f"new data ndim {new_array.ndim} at index {i} "
                    f"does not equal current data ndim {current_array.ndim}"
                )

            # Computes the number of scrollable dims and also validates new_array
            new_scrollable_dims = self._get_n_scrollable_dims(new_array, self._rgb[i])

            if self.n_scrollable_dims[i] != new_scrollable_dims:
                raise ValueError(
                    f"number of dimensions of data arrays must match number of dimensions of "
                    f"existing data arrays"
                )

        # if checks pass, update with new data
        for i, (new_array, current_array, subplot) in enumerate(
            zip(new_data, self._data, self.figure)
        ):
            # if the new array is the same as the existing array, skip
            # this allows setting just a subset of the arrays in the ImageWidget
            if new_data is self._data[i]:
                continue

            # check last two dims (x and y) to see if data shape is changing
            old_data_shape = self._data[i].shape[-self.n_img_dims[i] :]
            self._data[i] = new_array

            if old_data_shape != new_array.shape[-self.n_img_dims[i] :]:
                frame = self._process_indices(
                    new_array, slice_indices=self._current_index
                )
                frame = self._process_frame_apply(frame, i)

                # make new graphic first
                new_graphic = ImageGraphic(data=frame, name="image_widget_managed")

                if self._histogram_widget:
                    # set hlut tool to use new graphic
                    subplot.docks["right"]["histogram_lut"].images = new_graphic

                # delete old graphic after setting hlut tool to new graphic
                # this ensures gc
                subplot.delete_graphic(graphic=subplot["image_widget_managed"])
                subplot.insert_graphic(graphic=new_graphic)

            # Returns "", "t", or "tz"
            curr_scrollable_format = SCROLLABLE_DIMS_ORDER[self.n_scrollable_dims[i]]

            for scroll_dim in self.slider_dims:
                if scroll_dim in curr_scrollable_format:
                    new_length = new_array.shape[
                        curr_scrollable_format.index(scroll_dim)
                    ]
                    if max_lengths[scroll_dim] == np.inf:
                        max_lengths[scroll_dim] = new_length
                    elif max_lengths[scroll_dim] != new_length:
                        raise ValueError(
                            f"New arrays have differing values along dim {scroll_dim}"
                        )

                    self._dims_max_bounds[scroll_dim] = max_lengths[scroll_dim]

            # set histogram widget
            if self._histogram_widget:
                subplot.docks["right"]["histogram_lut"].set_data(
                    new_array, reset_vmin_vmax=reset_vmin_vmax
                )

        # force graphics to update
        self.current_index = self.current_index

    def show(self, **kwargs):
        """
        Show the widget.

        Parameters
        ----------

        kwargs: Any
            passed to `Figure.show()`

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
