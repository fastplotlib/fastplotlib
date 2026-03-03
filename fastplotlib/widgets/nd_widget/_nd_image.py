from collections.abc import Hashable, Sequence
import inspect
from typing import Literal, Callable, Type, Any
from warnings import warn

import numpy as np
from numpy.typing import ArrayLike
import xarray as xr

from ...utils import subsample_array, ArrayProtocol, ARRAY_LIKE_ATTRS
from ...graphics import ImageGraphic, ImageVolumeGraphic
from .base import NDProcessor, NDGraphic, WindowFuncCallable


class NDImageProcessor(NDProcessor):
    def __init__(
        self,
        data: ArrayLike | None,
        dims: Sequence[Hashable],
        spatial_dims: (
            tuple[str, str] | tuple[str, str, str]
        ),  # must be in order! [rows, cols] | [z, rows, cols]
        rgb_dim: str | None = None,
        window_funcs: tuple[WindowFuncCallable | None, ...] | WindowFuncCallable = None,
        window_order: tuple[int, ...] = None,
        spatial_func: Callable[[ArrayLike], ArrayLike] = None,
        compute_histogram: bool = True,
        index_mappings=None,
    ):
        """
        An ND image that supports computing window functions, and functions over spatial dimensions.

        Parameters
        ----------
        data: ArrayLike
            array-like data, must have 2 or more dimensions

        n_display_dims: int, 2 or 3, default 2
            number of display dimensions

        rgb: bool, default False
            whether the image data is RGB(A) or not

        window_funcs: tuple[WindowFuncCallable | None, ...] | WindowFuncCallable, optional
            A function or a ``tuple`` of functions that are applied to a rolling window of the data.

            You can provide unique window functions for each dimension. If you want to apply a window function
            only to a subset of the dimensions, put ``None`` to indicate no window function for a given dimension.

            A "window function" must take ``axis`` argument, which is an ``int`` that specifies the axis along which
            the window function is applied. It must also take a ``keepdims`` argument which is a ``bool``. The window
            function **must** return an array that has the same number of dimensions as the original ``data`` array,
            therefore the size of the dimension along which the window was applied will reduce to ``1``.

            The output array-like type from a window function **must** support a ``.squeeze()`` method, but the
            function itself should NOT squeeze the output array.

        window_sizes: tuple[int | None, ...], optional
            ``tuple`` of ``int`` that specifies the window size for each dimension.

        window_order: tuple[int, ...] | None, optional
            order in which to apply the window functions, by default just applies it from the left-most dim to the
            right-most slider dim.

        spatial_func: Callable[[ArrayLike], ArrayLike] | None, optional
            A function that is applied on the _spatial_ dimensions of the data array, i.e. the last 2 or 3 dimensions.
            This function is applied after the window functions (if present).

        compute_histogram: bool, default True
            Compute a histogram of the data, auto re-computes if window function propties or spatial_func changes.
            Disable if slow.

        """
        # set as False until data, window funcs stuff and spatial func is all set
        self._compute_histogram = False

        super().__init__(
            data=data,
            dims=dims,
            spatial_dims=spatial_dims,
            index_mappings=index_mappings,
            window_funcs=window_funcs,
            window_order=window_order,
            spatial_func=spatial_func,
        )

        self.rgb_dim = rgb_dim
        self._compute_histogram = compute_histogram
        self._recompute_histogram()

    @property
    def data(self) -> xr.DataArray | None:
        """get or set the data array"""
        return self._data

    @data.setter
    def data(self, data: ArrayLike):
        # check that all array-like attributes are present
        self._data = self._validate_data(data, self.dims)
        self._recompute_histogram()

    def _validate_data(self, data: ArrayProtocol, dims):
        if not isinstance(data, ArrayProtocol):
            raise TypeError(
                f"`data` arrays must have all of the following attributes to be sufficiently array-like:\n"
                f"{ARRAY_LIKE_ATTRS}, or they must be `None`"
            )

        if data.ndim < 2:
            raise IndexError(
                f"Image data must have a minimum of 2 dimensions, you have passed an array of shape: {data.shape}"
            )

        return xr.DataArray(data, dims=dims)

    @property
    def rgb_dim(self) -> str | None:
        """indicates the rgb dim if one exists"""
        return self._rgb

    @rgb_dim.setter
    def rgb_dim(self, rgb: str | None):
        if rgb is not None:
            if rgb not in self.dims:
                raise KeyError

        self._rgb = rgb

    @property
    def compute_histogram(self) -> bool:
        return self._compute_histogram

    @compute_histogram.setter
    def compute_histogram(self, compute: bool):
        if compute:
            if not self._compute_histogram:
                # compute a histogram
                self._recompute_histogram()
                self._compute_histogram = True
        else:
            self._compute_histogram = False
            self._histogram = None

    @property
    def histogram(self) -> tuple[np.ndarray, np.ndarray] | None:
        """
        an estimate of the histogram of the data, (histogram_values, bin_edges).

        returns `None` if `compute_histogram` is `False`
        """
        return self._histogram

    def get(self, indices: dict[str, Any]) -> ArrayLike | None:
        """
        Get the data at the given index, process data through the window functions.

        Note that we do not use __getitem__ here since the index is a tuple specifying a single integer
        index for each dimension. Slices are not allowed, therefore __getitem__ is not suitable here.

        Parameters
        ----------
        indices: tuple[int, ...]
            Get the processed data at this index. Must provide a value for each dimension.
            Example: get((100, 5))

        """
        if len(self.slider_dims) > 0:
            # there are dims in addition to the spatial dims
            window_output = self._apply_window_functions(indices).squeeze()
        else:
            # no slider dims, use all the data
            window_output = self.data

        if window_output.ndim != len(self.spatial_dims):
            raise ValueError

        # apply spatial_func
        if self.spatial_func is not None:
            spatial_out = self._spatial_func(window_output)
            if spatial_out.ndim != len(self.spatial_dims):
                raise ValueError

            return spatial_out.transpose(*self.spatial_dims).values

        return window_output.transpose(*self.spatial_dims).values

    def _recompute_histogram(self):
        """

        Returns
        -------
        (histogram_values, bin_edges)

        """
        if not self._compute_histogram or self.data is None:
            self._histogram = None
            return

        if self.spatial_func is not None:
            # don't subsample spatial dims if a spatial function is used
            # spatial functions often operate on the spatial dims, ex: a gaussian kernel
            # so their results require the full spatial resolution, the histogram of a
            # spatially subsampled image will be very different
            ignore_dims = [self.dims.index(dim) for dim in self.spatial_dims]
        else:
            ignore_dims = None

        sub = subsample_array(self.data.values, ignore_dims=ignore_dims)
        sub_real = sub[~(np.isnan(sub) | np.isinf(sub))]

        self._histogram = np.histogram(sub_real, bins=100)


class NDImage(NDGraphic):
    def __init__(
        self,
        global_index,
        data: ArrayLike | None,
        dims: Sequence[Hashable],
        spatial_dims: (
            tuple[str, str] | tuple[str, str, str]
        ),  # must be in order! [rows, cols] | [z, rows, cols]
        rgb_dim: str | None = None,
        window_funcs: tuple[WindowFuncCallable | None, ...] | WindowFuncCallable = None,
        window_order: tuple[int, ...] = None,
        spatial_func: Callable[[ArrayLike], ArrayLike] = None,
        compute_histogram: bool = True,
        index_mappings=None,
        name: str = None,
    ):

        self._global_index = global_index

        self._processor = NDImageProcessor(
            data,
            dims=dims,
            spatial_dims=spatial_dims,
            rgb_dim=rgb_dim,
            window_funcs=window_funcs,
            window_order=window_order,
            spatial_func=spatial_func,
            compute_histogram=compute_histogram,
            index_mappings=index_mappings,
        )

        self._graphic = None

        self._create_graphic()
        super().__init__(name)

    @property
    def processor(self) -> NDImageProcessor:
        return self._processor

    @property
    def graphic(
        self,
    ) -> ImageGraphic | ImageVolumeGraphic:
        """LineStack or ImageGraphic for heatmaps"""
        return self._graphic

    @graphic.setter
    def graphic(self, graphic_type):
        # TODO implement if graphic type changes to custom user subclass
        pass

    def _create_graphic(self):
        match len(self.processor.spatial_dims) - int(bool(self.processor.rgb_dim)):
            case 2:
                cls = ImageGraphic
            case 3:
                cls = ImageVolumeGraphic

        data_slice = self.processor.get(self.indices)

        old_graphic = self._graphic
        new_graphic = cls(data_slice)

        if old_graphic is not None:
            plot_area = old_graphic._plot_area
            plot_area.delete_graphic(old_graphic)
            plot_area.add_graphic(new_graphic)

        self._graphic = new_graphic

        if self._graphic._plot_area is not None:
            self._reset_camera()

    def _reset_camera(self):
        plot_area = self._graphic._plot_area

        # set camera to a nice position for 2D or 3D
        if isinstance(self._graphic, ImageGraphic):
            # set camera orthogonal to the xy plane, flip y axis
            plot_area.camera.set_state(
                {
                    "position": [0, 0, -1],
                    "rotation": [0, 0, 0, 1],
                    "scale": [1, -1, 1],
                    "reference_up": [0, 1, 0],
                    "fov": 0,
                    "depth_range": None,
                }
            )

            plot_area.controller = "panzoom"
            plot_area.axes.intersection = None
            plot_area.auto_scale()

        else:
            plot_area.camera.fov = 50
            plot_area.controller = "orbit"

            # make sure all 3D dimension camera scales are positive
            # MIP rendering doesn't work with negative camera scales
            for dim in ["x", "y", "z"]:
                if getattr(plot_area.camera.local, f"scale_{dim}") < 0:
                    setattr(plot_area.camera.local, f"scale_{dim}", 1)

            plot_area.auto_scale()

    @property
    def spatial_dims(self) -> tuple[str, str] | tuple[str, str, str]:
        return self.processor.spatial_dims

    @spatial_dims.setter
    def spatial_dims(self, dims: tuple[str, str] | tuple[str, str, str]):
        self.processor.spatial_dims = dims

        # shape has probably changed, recreate graphic
        self._create_graphic()

    @property
    def indices(self) -> dict[Hashable, Any]:
        return {d: self._global_index[d] for d in self.processor.slider_dims}

    @indices.setter
    def indices(self, indices):
        data_slice = self.processor.get(indices)

        self.graphic.data = data_slice

    def _tooltip_handler(self, graphic, pick_info):
        # get graphic within the collection
        n_index = np.argwhere(self.graphic.graphics == graphic).item()
        p_index = pick_info["vertex_index"]
        return self.processor.tooltip_format(n_index, p_index)
