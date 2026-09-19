from typing import Callable
from warnings import warn, catch_warnings, filterwarnings

import numpy as np

from ...utils import ArrayProtocol, calculate_figure_shape, quick_min_max
from ..nd_widget import NDWidget


# slider dims in order, "t" then "z", matching the old ImageWidget convention
SLIDER_DIMS = ("t", "z")


def _adapt_window_func(func: Callable) -> Callable:
    # ImageWidget window functions take only `axis`, but an NDImage window function is called
    # with both `axis` and `keepdims`. Wrap so the windowed dim is kept (reduced to size 1).
    def wrapper(a, axis, keepdims):
        out = func(a, axis=axis)
        return np.expand_dims(out, axis) if keepdims else out

    return wrapper


class ImageWidget:
    def __init__(
        self,
        data: np.ndarray | list[np.ndarray],
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
        A high-level widget for navigating through image stacks. It is a thin wrapper around an
        :class:`.NDWidget`, one ``add_nd_image`` per array, with sliders for the "t" (time) and "z"
        dimensions shared across every image stack.

        Allowed dimension orders for each image stack, where the optional ``(c)`` is an RGB(A) channel of
        size 3 or 4:

        ======= ==========
        n_dims  dims order
        ======= ==========
        2       "xy(c)"
        3       "txy(c)"
        4       "tzxy(c)"
        ======= ==========

        Parameters
        ----------
        data: np.ndarray | list[np.ndarray]
            array-like or a list of array-like, one image stack per subplot

        window_funcs: dict[str, tuple[Callable, int]], optional
            Rolling window functions along the "t" and/or "z" dims, ``{dim: (func, window_size)}``, ex:
            ``{"t": (np.mean, 11)}``. ``func`` must take an ``axis`` kwarg, ``window_size`` is in frames.

        frame_apply: Callable | dict[int, Callable], optional
            Function(s) applied to each array's slice before it is displayed. A single callable is applied
            to every subplot, a ``{array_index: callable}`` dict applies per-array. Applied after
            ``window_funcs``.

        figure_shape: tuple[int, int], optional
            manually provide the ``[n_rows, n_cols]`` shape for the figure, otherwise it is estimated

        names: list[str], optional
            names for the subplots

        figure_kwargs: dict, optional
            passed to the underlying ``ImguiFigure``

        histogram_widget: bool, default ``True``
            make a histogram colorbar for each subplot to interactively set vmin, vmax

        rgb: bool | list[bool], optional
            whether each array is RGB(A), i.e. the last dim is a channel of size 3 or 4

        cmap: str, default "plasma"
            colormap for the image graphics

        graphic_kwargs: dict, optional
            passed to each ``ImageGraphic``
        """
        if isinstance(data, ArrayProtocol):
            data = [data]

        if not (isinstance(data, list) and all(isinstance(d, ArrayProtocol) for d in data)):
            raise TypeError(
                "`data` must be an array-like or a list of array-like, you have passed: "
                f"{type(data)}"
            )

        # normalize rgb to a list of bool, one per array
        if rgb is None:
            rgb = [False] * len(data)
        elif isinstance(rgb, bool):
            rgb = [rgb] * len(data)
        if not (isinstance(rgb, list) and len(rgb) == len(data)):
            raise TypeError(
                "`rgb` must be a bool or a list of bool with one entry per data array"
            )
        self._rgb = rgb

        if names is not None:
            if not all(isinstance(n, str) for n in names):
                raise TypeError("`names` must be a list of str")
            if len(names) != len(data):
                raise ValueError("number of `names` must equal the number of data arrays")

        # dims, display_dims, rgb_dim and number of slider dims for each array (validates the arrays)
        image_dims = [self._dims_for(arr, is_rgb) for arr, is_rgb in zip(data, rgb)]
        max_slider_dims = max(n for *_, n in image_dims)
        self._slider_dims = list(SLIDER_DIMS[:max_slider_dims])

        self._validate_window_funcs(window_funcs)
        self._window_funcs = window_funcs

        self._validate_frame_apply(frame_apply)
        self._frame_apply = frame_apply

        # figure grid, large enough to hold every array
        if figure_shape is None:
            figure_shape = calculate_figure_shape(len(data))
        if figure_shape[0] * figure_shape[1] < len(data):
            warn(
                f"`figure_shape` {figure_shape} is too small for {len(data)} arrays, "
                f"resetting it to {calculate_figure_shape(len(data))}"
            )
            figure_shape = calculate_figure_shape(len(data))

        if figure_kwargs is None:
            figure_kwargs = dict()
        if graphic_kwargs is None:
            graphic_kwargs = dict()

        # each slider dim gets an auto reference range spanning the largest array along that dim, so the
        # reference index is just the array index. ImageWidget syncs subplot controllers by default,
        # user figure_kwargs can override.
        self._ndw = NDWidget(
            **{
                "controller_ids": "sync",
                "names": names,
                **figure_kwargs,
                "shape": figure_shape,
            },
        )

        # ImageWidget uses raw array indices as reference values, so add_nd_image auto-creates the
        # reference ranges; silence its per-dim "no reference range specified" warning.
        self._nd_images = list()
        with catch_warnings():
            filterwarnings("ignore", message="No reference range specified")
            for i, ((dims, display_dims, rgb_dim, _), arr, subplot) in enumerate(
                zip(image_dims, data, self._ndw.figure)
            ):
                window_funcs, window_order = self._translate_window_funcs(
                    set(dims) & set(SLIDER_DIMS)
                )
                nd = self._ndw[subplot].add_nd_image(
                    arr,
                    dims,
                    display_dims,
                    rgb_dim=rgb_dim,
                    window_funcs=window_funcs,
                    window_order=window_order,
                    spatial_func=self._spatial_func_for(i),
                    compute_histogram=histogram_widget,
                    graphic_kwargs={**graphic_kwargs, "cmap": cmap},
                )
                self._nd_images.append(nd)

        # bridge the shared ReferenceIndices onto the "current_index" event
        self._current_index_changed_handlers = set()
        self._ndw.indices.add_event_handler(self._indices_changed, "indices")

    def _dims_for(
        self, arr: np.ndarray, rgb: bool
    ) -> tuple[tuple[str, ...], tuple[str, ...], str | None, int]:
        # dim names, display dims, rgb dim name and number of slider dims for one array
        n_image_dims = 3 if rgb else 2
        if arr.ndim < n_image_dims:
            raise ValueError(
                f"Array has shape {arr.shape} but each image is {n_image_dims}D"
            )
        if rgb and arr.shape[-1] not in (3, 4):
            raise ValueError(
                f"Expected size 3 or 4 for the last (RGB) dim, got {arr.shape[-1]}"
            )

        n_slider_dims = arr.ndim - n_image_dims
        if n_slider_dims > len(SLIDER_DIMS):
            raise ValueError(
                f"Array shape {arr.shape} has too many dims, at most {len(SLIDER_DIMS)} "
                f"slider dims {SLIDER_DIMS} are supported"
            )

        slider_dims = SLIDER_DIMS[:n_slider_dims]
        if rgb:
            return (*slider_dims, "row", "col", "c"), ("row", "col", "c"), "c", n_slider_dims
        return (*slider_dims, "row", "col"), ("row", "col"), None, n_slider_dims

    def _translate_window_funcs(
        self, slider_dims: set[str]
    ) -> tuple[dict | None, tuple[str, ...] | None]:
        # translate the plain {dim: (func, size)} dict into the window_funcs and window_order
        # that an NDImage with these slider dims expects
        if self._window_funcs is None:
            return None, None

        window_funcs = {
            dim: (_adapt_window_func(func), float(size))
            for dim, (func, size) in self._window_funcs.items()
            if dim in slider_dims
        }
        if not window_funcs:
            return None, None

        return window_funcs, tuple(d for d in SLIDER_DIMS if d in window_funcs)

    def _spatial_func_for(self, index: int) -> Callable | None:
        # the frame_apply function for the array at ``index``
        if self._frame_apply is None or callable(self._frame_apply):
            return self._frame_apply
        return self._frame_apply.get(index)

    def _indices_changed(self, indices: dict[str, float]):
        current_index = self.current_index
        for handler in self._current_index_changed_handlers:
            handler(current_index)

    @staticmethod
    def _validate_window_funcs(window_funcs):
        if window_funcs is None:
            return
        if not isinstance(window_funcs, dict):
            raise TypeError(
                "`window_funcs` must be a dict `{dim: (func, window_size)}` or None"
            )
        if not set(window_funcs).issubset(SLIDER_DIMS):
            raise ValueError(f"`window_funcs` keys must be a subset of {SLIDER_DIMS}")
        for func, size in window_funcs.values():
            if not callable(func):
                raise TypeError("each window function must be callable")
            if not isinstance(size, (int, np.integer)):
                raise TypeError("each window size must be an int")

    @staticmethod
    def _validate_frame_apply(frame_apply):
        if frame_apply is None or callable(frame_apply):
            return
        if isinstance(frame_apply, dict):
            if not all(isinstance(k, (int, np.integer)) for k in frame_apply):
                raise TypeError("`frame_apply` dict keys must be an int array index")
            return
        raise TypeError(
            "`frame_apply` must be a callable, a `{array_index: callable}` dict, or None"
        )

    @property
    def figure(self):
        """``ImguiFigure`` used by the ``ImageWidget``"""
        return self._ndw.figure

    @property
    def managed_graphics(self) -> list:
        """the ``ImageGraphic`` objects managed by the ``ImageWidget``"""
        return [nd.graphic for nd in self._nd_images]

    @property
    def data(self) -> list[np.ndarray]:
        """the data arrays displayed in the widget"""
        return [nd.data for nd in self._nd_images]

    @property
    def slider_dims(self) -> list[str]:
        """the dimensions that the sliders index, ``["t"]`` or ``["t", "z"]``"""
        return list(self._slider_dims)

    @property
    def cmap(self) -> list:
        return [nd.graphic.cmap for nd in self._nd_images]

    @cmap.setter
    def cmap(self, names: str | list[str]):
        if isinstance(names, str):
            names = [names] * len(self._nd_images)
        elif isinstance(names, list):
            if not all(isinstance(n, str) for n in names):
                raise TypeError(f"cmap names must be a str or list of str, you passed: {names}")
            if len(names) != len(self._nd_images):
                raise IndexError(
                    f"a list of cmap names must have one name per subplot, you passed "
                    f"{len(names)} names for {len(self._nd_images)} subplots"
                )
        else:
            raise TypeError(f"cmap names must be a str or list of str, you passed: {names}")

        for name, nd in zip(names, self._nd_images):
            nd.graphic.cmap = name

    @property
    def current_index(self) -> dict[str, int]:
        """
        Get or set the current index of each slider dim.

        Provide a subset or all of the slider dims, ex: ``{"t": 10}`` or ``{"t": 5, "z": 20}``. Any dim
        that is not provided keeps its current index.
        """
        return {d: round(self._ndw.indices[d]) for d in self._slider_dims}

    @current_index.setter
    def current_index(self, index: dict[str, int]):
        if not set(index).issubset(self._slider_dims):
            raise KeyError(
                f"All `current_index` keys must be slider dims: {self._slider_dims}, "
                f"you passed: {list(index)}"
            )
        for dim, value in index.items():
            if not isinstance(value, (int, np.integer)):
                raise TypeError("indices for all dimensions must be int")
            if value < 0:
                raise IndexError("negative indexing is not supported for ImageWidget")
            max_index = self._ndw.ranges[dim].stop - 1
            if value > max_index:
                raise IndexError(
                    f"index {value} is out of bounds for dim '{dim}' with max index {max_index}"
                )

        self._ndw.indices = {dim: int(value) for dim, value in index.items()}

    @property
    def window_funcs(self) -> dict[str, tuple[Callable, int]] | None:
        """get or set the window functions, ``{dim: (func, window_size)}``"""
        return self._window_funcs

    @window_funcs.setter
    def window_funcs(self, window_funcs: dict[str, tuple[Callable, int]] | None):
        self._validate_window_funcs(window_funcs)
        self._window_funcs = window_funcs
        for nd in self._nd_images:
            funcs, order = self._translate_window_funcs(nd.slider_dims)
            # disable windowing before swapping the funcs, so no intermediate render applies a
            # window_order dim whose function has just been cleared
            nd.window_order = None
            nd.window_funcs = funcs
            nd.window_order = order

    @property
    def frame_apply(self) -> Callable | dict[int, Callable] | None:
        """get or set the frame_apply function(s)"""
        return self._frame_apply

    @frame_apply.setter
    def frame_apply(self, frame_apply: Callable | dict[int, Callable] | None):
        self._validate_frame_apply(frame_apply)
        self._frame_apply = frame_apply
        for i, nd in enumerate(self._nd_images):
            nd.spatial_func = self._spatial_func_for(i)

    def add_event_handler(self, handler: Callable, event: str = "current_index"):
        """
        Register an event handler, called whenever the ``current_index`` changes with the
        ``current_index`` dict as the only argument. "current_index" is the only supported event.
        """
        if event != "current_index":
            raise ValueError("`current_index` is the only event supported by `ImageWidget`")
        self._current_index_changed_handlers.add(handler)

    def remove_event_handler(self, handler: Callable):
        """Remove a registered event handler"""
        self._current_index_changed_handlers.remove(handler)

    def clear_event_handlers(self):
        """Clear all registered event handlers"""
        self._current_index_changed_handlers.clear()

    def reset_vmin_vmax(self):
        """Reset the vmin, vmax of each image graphic, estimated from the full data array"""
        for nd in self._nd_images:
            nd.graphic.vmin, nd.graphic.vmax = quick_min_max(nd.data)

    def set_data(
        self,
        new_data: np.ndarray | list[np.ndarray],
        reset_vmin_vmax: bool = True,
        reset_indices: bool = True,
    ):
        """
        Change the data displayed in the widget.

        Parameters
        ----------
        new_data: np.ndarray | list[np.ndarray]
            the new data, one array per subplot, each with the same number of dims as the array it replaces

        reset_vmin_vmax: bool, default ``True``
            reset the vmin, vmax using the new data

        reset_indices: bool, default ``True``
            reset the current index of every slider dim to 0
        """
        if isinstance(new_data, ArrayProtocol):
            new_data = [new_data]
        if len(new_data) != len(self._nd_images):
            raise ValueError(
                f"number of new data arrays {len(new_data)} must equal the current number "
                f"{len(self._nd_images)}"
            )

        for i, (new_array, nd) in enumerate(zip(new_data, self._nd_images)):
            if new_array is nd.data:
                # allows setting only a subset of the arrays
                continue
            if new_array.ndim != nd.data.ndim:
                raise ValueError(
                    f"new data ndim {new_array.ndim} at index {i} does not equal the current "
                    f"ndim {nd.data.ndim}"
                )
            # validates the new array against its rgb setting
            self._dims_for(new_array, self._rgb[i])

            if not reset_vmin_vmax:
                vmin, vmax = nd.graphic.vmin, nd.graphic.vmax

            # recreates the graphic, resets the camera, histogram and vmin, vmax
            nd.data = new_array

            if not reset_vmin_vmax:
                nd.graphic.vmin, nd.graphic.vmax = vmin, vmax

            # grow the slider ranges to fit the new array
            for dim in nd.slider_dims:
                self._ndw.ranges[dim].stop = max(
                    self._ndw.ranges[dim].stop, new_array.shape[SLIDER_DIMS.index(dim)]
                )

        if reset_indices:
            self._ndw.indices = {dim: 0 for dim in self._slider_dims}

    def show(self, **kwargs):
        """
        Show the widget.

        Parameters
        ----------
        kwargs: Any
            passed to ``Figure.show()``

        Returns
        -------
        BaseRenderCanvas
            In Qt or GLFW, the canvas window containing the Figure will be shown.
            In jupyter, it will display the plot in the output cell or sidecar.
        """
        return self._ndw.show(**kwargs)

    def close(self):
        """Close the widget"""
        self._ndw.close()
