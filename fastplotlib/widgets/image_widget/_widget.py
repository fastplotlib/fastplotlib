from typing import Callable, Sequence, Literal
from warnings import warn

import numpy as np

from rendercanvas import BaseRenderCanvas

from ...layouts import ImguiFigure as Figure
from ...graphics import ImageGraphic, ImageVolumeGraphic
from ...utils import calculate_figure_shape, quick_min_max
from ...tools import HistogramLUTTool
from ._sliders import ImageWidgetSliders
from ._array import NDImageArray, WindowFuncCallable, ArrayLike, is_arraylike


class ImageWidget:
    def __init__(
        self,
        data: np.ndarray | list[np.ndarray],
        array_types: NDImageArray | list[NDImageArray] = NDImageArray,
        n_display_dims: Literal[2, 3] | Sequence[Literal[2, 3]] = 2,
        rgb: bool | Sequence[bool] = None,
        cmap: str | Sequence[str]= "plasma",
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
        finalizer_funcs: (
            Callable[[ArrayLike], ArrayLike]
            | Sequence[Callable[[ArrayLike], ArrayLike]]
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
        data: np.ndarray | List[np.ndarray]
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

        if is_arraylike(data):
            data = [data]

        if isinstance(data, list):
            # verify that it's a list of np.ndarray
            if not all([is_arraylike(d) for d in data]):
                raise TypeError(
                    f"`data` must be an array-like type or a list of array-like."
                    f"You have passed the following type {type(data)}"
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

        if rgb is None:
            rgb = [False] * len(data)

        elif isinstance(rgb, bool):
            rgb = [rgb] * len(data)

        if not all([isinstance(v, bool) for v in rgb]):
            raise TypeError(
                f"`rgb` parameter must be a bool or a Sequence of bool, <{rgb}> was provided"
            )

        if not len(rgb) == len(data):
            raise ValueError(
                f"len(rgb) != len(data), {len(rgb)} != {len(self.data)}. These must be equal"
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
        if finalizer_funcs is None:
            final_funcs = [None] * len(data)

        elif callable(finalizer_funcs):
            # same finalizer func for all data arrays
            final_funcs = [finalizer_funcs] * len(data)

        elif len(finalizer_funcs) != len(data):
            raise IndexError

        else:
            final_funcs = finalizer_funcs

        # verify number of display dims
        if isinstance(n_display_dims, int):
            if n_display_dims not in (2, 3):
                raise ValueError
            n_display_dims = [n_display_dims] * len(data)

        elif isinstance(n_display_dims, (tuple, list)):
            if not all([n in (2, 3) for n in n_display_dims]):
                raise ValueError
            if len(n_display_dims) != len(data):
                raise IndexError
        else:
            raise TypeError

        self._n_display_dims = n_display_dims

        if sliders_dim_order not in ("left", "right"):
            raise ValueError
        self._sliders_dim_order = sliders_dim_order

        # make NDImageArrays
        self._image_arrays: list[NDImageArray] = list()
        for i in range(len(data)):
            image_array = NDImageArray(
                data=data[i],
                rgb=rgb[i],
                n_display_dims=n_display_dims[i],
                window_funcs=win_funcs[i],
                window_sizes=win_sizes[i],
                window_order=win_order[i],
                finalizer_func=final_funcs[i],
                compute_histogram=histogram_widget,
            )

            self._image_arrays.append(image_array)

        figure_kwargs_default = {"controller_ids": "sync", "names": names}

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

        self._histogram_widget = histogram_widget

        self._indices = tuple(0 for i in range(self.n_sliders))

        for i, subplot in zip(range(len(self._image_arrays)), self.figure):
            image_data = self._get_image(self._indices, self._image_arrays[i])

            # next 20 lines are just vmin, vmax parsing
            vmin_specified, vmax_specified = None, None
            if "vmin" in graphic_kwargs[i].keys():
                vmin_specified = graphic_kwargs[i].pop("vmin")
            if "vmax" in graphic_kwargs[i].keys():
                vmax_specified = graphic_kwargs[i].pop("vmax")

            if (vmin_specified is None) or (vmax_specified is None):
                # if either vmin or vmax are not specified, calculate an estimate by subsampling
                vmin_estimate, vmax_estimate = quick_min_max(self._image_arrays[i].data)

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

            if self._n_display_dims[i] == 2:
                # create an Image
                graphic = ImageGraphic(
                    data=image_data,
                    name="image_widget_managed",
                    vmin=vmin,
                    vmax=vmax,
                    **graphic_kwargs[i],
                )
            elif self._n_display_dims[i] == 3:
                # create an ImageVolume
                graphic = ImageVolumeGraphic(
                    data=image_data,
                    name="image_widget_managed",
                    vmin=vmin,
                    vmax=vmax,
                    **graphic_kwargs[i],
                )

            subplot.add_graphic(graphic)

            if self._histogram_widget:
                hlut = HistogramLUTTool(
                    data=self._image_arrays[i].data,
                    images=graphic,
                    name="histogram_lut",
                    histogram=self._image_arrays[i].histogram,
                )

                subplot.docks["right"].add_graphic(hlut)
                subplot.docks["right"].size = 80
                subplot.docks["right"].auto_scale(maintain_aspect=False)
                subplot.docks["right"].controller.enabled = False

        # hard code the expected height so that the first render looks right in tests, docs etc.
        ui_size = 57 + (self.n_sliders * 50)

        self._image_widget_sliders = ImageWidgetSliders(
            figure=self.figure,
            size=ui_size,
            location="bottom",
            title="ImageWidget Controls",
            image_widget=self,
        )

        self.figure.add_gui(self._image_widget_sliders)

        self._indices_changed_handlers = set()

        self._reentrant_block = False

        self._initialized = True

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
            # empty subplots will not have any image widget data
            if len(subplot.graphics) > 0:
                iw_managed.append(subplot["image_widget_managed"])
        return iw_managed

    @property
    def cmap(self) -> list[str]:
        cmaps = list()
        for g in self.graphics:
            cmaps.append(g.cmap)

        return cmaps

    @cmap.setter
    def cmap(self, names: str | list[str]):
        if isinstance(names, list):
            if not all([isinstance(n, str) for n in names]):
                raise TypeError(
                    f"Must pass cmap name as a `str` of list of `str`, you have passed:\n{names}"
                )

            if not len(names) == len(self.graphics):
                raise IndexError(
                    f"If passing a list of cmap names, the length of the list must be the same as the number of "
                    f"image widget subplots. You have passed: {len(names)} cmap names and have "
                    f"{len(self.graphics)} image widget subplots"
                )

            for name, g in zip(names, self.graphics):
                g.cmap = name

        elif isinstance(names, str):
            for g in self.graphics:
                g.cmap = names

    @property
    def data(self) -> list[np.ndarray]:
        """data currently displayed in the widget"""
        return self._data

    @property
    def indices(self) -> tuple[int, ...]:
        """
        Get or set the current indices

        Returns
        -------
        indices: tuple[int, ...]
            integer index for each slider dimension

        """
        return self._indices

    @indices.setter
    def indices(self, new_indices: Sequence[int]):
        if not self._initialized:
            return

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

            for image_array, graphic in zip(self._image_arrays, self.graphics):
                new_data = self._get_image(new_indices, image_array)
                graphic.data = new_data

            self._indices = new_indices

            # call any event handlers
            for handler in self._indices_changed_handlers:
                handler(self.indices)

        except Exception as exc:
            # raise original exception
            raise exc  # indices setter has raised. The lines above below are probably more relevant!
        finally:
            # set_value has finished executing, now allow future executions
            self._reentrant_block = False

    def _get_image(self, slider_indices: tuple[int, ...], image_array: NDImageArray):
        n = image_array.n_slider_dims

        if self._sliders_dim_order == "right":
            return image_array.get(self.indices[-n:])

        elif self._sliders_dim_order == "left":
            return image_array.get(self.indices[:n])

    @property
    def n_sliders(self) -> int:
        return max([a.n_slider_dims for a in self._image_arrays])

    @property
    def bounds(self) -> tuple[int, ...]:
        """The max bound across all dimensions across all data arrays"""
        # initialize with 0
        bounds = [0] * self.n_sliders

        for dim in range(self.n_sliders):
            # across each dim
            for array in self._image_arrays:
                if dim > array.n_slider_dims - 1:
                    continue
                # across each data array
                bounds[dim] = max(array.shape[dim], bounds[dim])

        return bounds

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

    @property
    def data(self) -> tuple[np.ndarray, ...]:
        return tuple(array.data for array in self._image_arrays)

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
            for key in self.indices:
                self.indices[key] = 0

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
        self.indices = self.indices

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
