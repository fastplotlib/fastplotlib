from collections.abc import Hashable, Sequence
import inspect
from typing import Callable, Any

import numpy as np
from numpy.typing import ArrayLike
import xarray as xr

from ...layouts import Subplot
from ...utils import subsample_array, ArrayProtocol, ARRAY_LIKE_ATTRS
from ...graphics import ImageGraphic, ImageVolumeGraphic
from ...tools import HistogramLUTTool
from ._base import NDProcessor, NDGraphic, WindowFuncCallable
from ._index import ReferenceIndex


class NDImageProcessor(NDProcessor):
    def __init__(
        self,
        data: ArrayProtocol | None,
        dims: Sequence[Hashable],
        spatial_dims: (
            tuple[str, str] | tuple[str, str, str]
        ),  # must be in order! [rows, cols] | [z, rows, cols]
        rgb_dim: str | None = None,
        window_funcs: tuple[WindowFuncCallable | None, ...] | WindowFuncCallable = None,
        window_order: tuple[int, ...] = None,
        spatial_func: Callable[[ArrayLike], ArrayLike] = None,
        compute_histogram: bool = True,
        slider_dim_transforms=None,
    ):
        """
        ``NDProcessor`` subclass for n-dimensional image data.

        Produces 2-D or 3-D spatial slices for an ``ImageGraphic`` or ``ImageVolumeGraphic``.

        Parameters
        ----------
        data: ArrayProtocol
            array-like data, must have 2 or more dimensions

                dims: Sequence[str]
            names for each dimension in ``data``. Dimensions not listed in
            ``spatial_dims`` are treated as slider dimensions and **must** appear as
            keys in the parent ``NDWidget``'s ``ref_ranges``
                Examples::
                 ``("time", "depth", "row", "col")``
                 ``("channels", "time", "xy")``
                 ``("keypoints", "time", "xyz")``

            A custom subclass's ``data`` object doesn't necessarily need to have these dims, but the ``get()`` method
            must operate as if these dimensions exist and return an array that matches the spatial dimensions.

        dims: Sequence[str]
            names for each dimension in ``data``. Dimensions not listed in
            ``spatial_dims`` are treated as slider dimensions and **must** appear as
            keys in the parent ``NDWidget``'s ``ref_ranges``
                Examples::
                 ``("time", "depth", "row", "col")``
                 ``("row", "col")``
                 ``("other_dim", "depth", "time", "row", "col")``

            dims in the array do not need to be in order, for example you can have a weird array where the dims are
            interpreted as: ``("col", "depth", "row", "time")``, and then specify spatial_dims as ``("row", "col")``
            thanks to xarray magic =D.

        spatial_dims : tuple[str, str] | tuple[str, str, str]
            The 2 or 3 spatial dimensions **in order**: ``(rows, cols)`` or ``(z, rows, cols)``.
            This also determines whether an ``ImageGraphic`` or ``ImageVolumeGraphic`` is used for rendering.
            The ordering determines how the Image/Volume is rendered. For example, if
            you specify ``spatial_dims = ("rows", "cols")`` and then change it to ``("cols", "rows")``, it will display
            the transpose.

        rgb_dim : str, optional
            Name of an RGB(A) dimension, if present.

        compute_histogram: bool, default True
            Compute a histogram of the data, disable if random-access of data is not blazing-fast (ex: data that uses
            video codecs), or if histograms are not useful for this data.

        slider_dim_transforms : dict, optional
            See :class:`NDProcessor`.

        window_funcs : dict, optional
            See :class:`NDProcessor`.

        window_order : tuple, optional
            See :class:`NDProcessor`.

        spatial_func : callable, optional
            See :class:`NDProcessor`.

        See Also
        --------
            NDProcessor : Base class with full parameter documentation.
            NDImage : The ``NDGraphic`` that wraps this processor.
        """

        # set as False until data, window funcs stuff and spatial func is all set
        self._compute_histogram = False

        # make sure rgb dim is size 3 or 4
        if rgb_dim is not None:
            dim_index = dims.index(rgb_dim)
            if data.shape[dim_index] not in (3, 4):
                raise IndexError(
                    f"The size of the RGB(A) dim must be 3 | 4. You have specified an array of shape: {data.shape}, "
                    f"with dims: {dims}, and specified the ``rgb_dim`` name as: {rgb_dim} which has size "
                    f"{data.shape[dim_index]} != 3 | 4"
                )

        super().__init__(
            data=data,
            dims=dims,
            spatial_dims=spatial_dims,
            slider_dim_transforms=slider_dim_transforms,
            window_funcs=window_funcs,
            window_order=window_order,
            spatial_func=spatial_func,
        )

        self.rgb_dim = rgb_dim
        self._compute_histogram = compute_histogram
        self._recompute_histogram()

    @property
    def data(self) -> xr.DataArray | None:
        """
        get or set managed data. If setting with new data, the new data is interpreted
        to have the same dims (i.e. same dim names and ordering of dims).
        """
        return self._data

    @data.setter
    def data(self, data: ArrayProtocol):
        self._data = self._validate_data(data)
        self._recompute_histogram()

    def _validate_data(self, data: ArrayProtocol):
        if not isinstance(data, ArrayProtocol):
            # check that it's compatible with array and generally array-like
            raise TypeError(
                f"`data` arrays must have all of the following attributes to be sufficiently array-like:\n"
                f"{ARRAY_LIKE_ATTRS}, or they must be `None`"
            )

        if data.ndim < 2:
            # ndim < 2 makes no sense for image data
            raise IndexError(
                f"Image data must have a minimum of 2 dimensions, you have passed an array of shape: {data.shape}"
            )

        return xr.DataArray(data, dims=self.dims)

    @property
    def rgb_dim(self) -> str | None:
        """
        get or set the RGB(A) dim name, ``None`` if no RGB(A) dim exists
        """
        return self._rgb

    @rgb_dim.setter
    def rgb_dim(self, rgb: str | None):
        if rgb is not None:
            if rgb not in self.dims:
                raise KeyError

        self._rgb = rgb

    @property
    def compute_histogram(self) -> bool:
        """get or set whether or not to compute the histogram"""
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

        # TODO: account for window funcs

        sub = subsample_array(self.data, ignore_dims=ignore_dims)

        if isinstance(sub, xr.DataArray):
            # can't do the isnan and isinf boolean indexing below on xarray
            sub = sub.values

        sub_real = sub[~(np.isnan(sub) | np.isinf(sub))]

        self._histogram = np.histogram(sub_real, bins=100)


class NDImage(NDGraphic):
    def __init__(
        self,
        ref_index: ReferenceIndex,
        subplot: Subplot,
        data: ArrayProtocol | None,
        dims: Sequence[str],
        spatial_dims: (
            tuple[str, str] | tuple[str, str, str]
        ),  # must be in order! [rows, cols] | [z, rows, cols]
        rgb_dim: str | None = None,
        window_funcs: tuple[WindowFuncCallable | None, ...] | WindowFuncCallable = None,
        window_order: tuple[int, ...] = None,
        spatial_func: Callable[[ArrayLike], ArrayLike] = None,
        compute_histogram: bool = True,
        slider_dim_transforms=None,
        name: str = None,
    ):
        """
        ``NDGraphic`` subclass for n-dimensional image rendering.

        Wraps an :class:`NDImageProcessor` and manages either an ``ImageGraphic`` or``ImageVolumeGraphic``.
        swaps automatically when :attr:`spatial_dims` is reassigned at runtime. Also
        owns a ``HistogramLUTTool`` for interactive vmin, vmax adjustment.

        Every dimension that is *not* listed in ``spatial_dims`` becomes a slider
        dimension. Each slider dim must have a ``ReferenceRange`` defined in the
        ``ReferenceIndex`` of the parent ``NDWidget``. The widget uses this to direct
        a change in the ``ReferenceIndex`` and update the graphics.

        Parameters
        ----------
        ref_index : ReferenceIndex
            The shared reference index that delivers slider updates to this graphic.

        subplot : Subplot
            parent subplot the NDGraphic is in

        data : array-like or None
            n-dimension image data array

        dims : sequence of hashable
            Name for every dimension of ``data``, in order. Non-spatial dims must
            match keys in ``ref_index``.

            ex: ``("time", "depth", "row", "col")`` — ``"time"`` and ``"depth"`` must
            be present in ``ref_index``.

        spatial_dims : tuple[str, str] | tuple[str, str, str]
            Spatial dimensions **in order**: ``(rows, cols)`` for 2-D images or
            ``(z, rows, cols)`` for volumes. Controls whether an ``ImageGraphic`` or
            ``ImageVolumeGraphic`` is used.

        rgb_dim : str, optional
            Name of the RGB or channel dimension, if present.

        window_funcs : dict, optional
            See :class:`NDProcessor`.

        window_order : tuple, optional
            See :class:`NDProcessor`.

        spatial_func : callable, optional
            See :class:`NDProcessor`.

        compute_histogram : bool, default ``True``
            Whether to initialize the ``HistogramLUTTool``.

        slider_dim_transforms : dict, optional
            See :class:`NDProcessor`.

        name : str, optional
            Name for the underlying graphic.

        See Also
        --------
        NDImageProcessor : The processor that backs this graphic.

        """

        if not (set(dims) - set(spatial_dims)).issubset(ref_index.dims):
            raise IndexError(
                f"all specified `dims` must either be a spatial dim or a slider dim "
                f"specified in the NDWidget ref_ranges, provided dims: {dims}, "
                f"spatial_dims: {spatial_dims}. Specified NDWidget ref_ranges: {ref_index.dims}"
            )

        super().__init__(subplot, name)

        self._ref_index = ref_index

        self._processor = NDImageProcessor(
            data,
            dims=dims,
            spatial_dims=spatial_dims,
            rgb_dim=rgb_dim,
            window_funcs=window_funcs,
            window_order=window_order,
            spatial_func=spatial_func,
            compute_histogram=compute_histogram,
            slider_dim_transforms=slider_dim_transforms,
        )

        self._graphic: ImageGraphic | None = None
        self._histogram_widget: HistogramLUTTool | None = None

        # create a graphic
        self._create_graphic()

    @property
    def processor(self) -> NDImageProcessor:
        """NDProcessor that manages the data and produces data slices to display"""
        return self._processor

    @property
    def graphic(
        self,
    ) -> ImageGraphic | ImageVolumeGraphic:
        """Underlying Graphic object used to display the current data slice"""
        return self._graphic

    def _create_graphic(self):
        # Creates an ``ImageGraphic`` or ``ImageVolumeGraphic`` based on the number of spatial dims,
        # adds it to the subplot, and resets the camera and histogram.

        if self.processor.data is None:
            # no graphic if data is None, useful for initializing in null states when we want to set data later
            return

        # determine if we need a 2d image or 3d volume
        # remove RGB spatial dim, ex: if we have an RGBA image of shape [512, 512, 4] we want to interpet this as
        # 2D for images
        # [30, 512, 512, 4] with an rgb dim is an RGBA volume which is also supported
        match len(self.processor.spatial_dims) - int(bool(self.processor.rgb_dim)):
            case 2:
                cls = ImageGraphic
            case 3:
                cls = ImageVolumeGraphic

        # get the data slice for this index
        # this will only have the dims specified by ``spatial_dims``
        data_slice = self.processor.get(self.indices)

        # create the new graphic
        new_graphic = cls(data_slice)

        old_graphic = self._graphic
        # check if we are replacing a graphic
        # ex: swapping from 2D <-> 3D representation after ``spatial_dims`` was changed
        if old_graphic is not None:
            # carry over some attributes from old graphic
            attrs = dict.fromkeys(["cmap", "interpolation", "cmap_interpolation"])
            for k in attrs:
                attrs[k] = getattr(old_graphic, k)

            # delete the old graphic
            self._subplot.delete_graphic(old_graphic)

            # set any attributes that we're carrying over like cmap
            for attr, val in attrs.items():
                setattr(new_graphic, attr, val)

        self._graphic = new_graphic

        self._subplot.add_graphic(self._graphic)

        self._reset_camera()
        self._reset_histogram()

    def _reset_histogram(self):
        # reset histogram
        if self.graphic is None:
            return

        if not self.processor.compute_histogram:
            # hide right dock if histogram not desired
            self._subplot.docks["right"].size = 0
            return

        if self.processor.histogram:
            if self._histogram_widget:
                # histogram widget exists, update it
                self._histogram_widget.histogram = self.processor.histogram
                self._histogram_widget.images = self.graphic
                if self._subplot.docks["right"].size < 1:
                    self._subplot.docks["right"].size = 80
            else:
                # make hist tool
                self._histogram_widget = HistogramLUTTool(
                    histogram=self.processor.histogram,
                    images=self.graphic,
                    name=f"hist-{hex(id(self.graphic))}",
                )
                self._subplot.docks["right"].add_graphic(self._histogram_widget)
                self._subplot.docks["right"].size = 80

            self.graphic.reset_vmin_vmax()

    def _reset_camera(self):
        # set camera to a nice position based on whether it's a 2D ImageGraphic or 3D ImageVolumeGraphic
        if isinstance(self._graphic, ImageGraphic):
            # set camera orthogonal to the xy plane, flip y axis
            self._subplot.camera.set_state(
                {
                    "position": [0, 0, -1],
                    "rotation": [0, 0, 0, 1],
                    "scale": [1, -1, 1],
                    "reference_up": [0, 1, 0],
                    "fov": 0,  # orthographic projection
                    "depth_range": None,
                }
            )

            self._subplot.controller = "panzoom"
            self._subplot.axes.intersection = None
            self._subplot.auto_scale()

        else:
            # It's not an ImageGraphic, set perspective projection
            self._subplot.camera.fov = 50
            self._subplot.controller = "orbit"

            # set all 3D dimension camera scales to positive since positive scales
            # are typically used for looking at volumes
            for dim in ["x", "y", "z"]:
                if getattr(self._subplot.camera.local, f"scale_{dim}") < 0:
                    setattr(self._subplot.camera.local, f"scale_{dim}", 1)

            self._subplot.auto_scale()

    @property
    def spatial_dims(self) -> tuple[str, str] | tuple[str, str, str]:
        """get or set the spatial dims, see docstring for details"""
        return self.processor.spatial_dims

    @spatial_dims.setter
    def spatial_dims(self, dims: tuple[str, str] | tuple[str, str, str]):
        self.processor.spatial_dims = dims

        # shape has probably changed, recreate graphic
        self._create_graphic()

    @property
    def indices(self) -> dict[Hashable, Any]:
        """get or set the indices, managed by the ReferenceIndex, users usually don't want to set this manually"""
        return {d: self._ref_index[d] for d in self.processor.slider_dims}

    @indices.setter
    def indices(self, indices):
        data_slice = self.processor.get(indices)

        self.graphic.data = data_slice

    @property
    def compute_histogram(self) -> bool:
        """whether or not to compute the histogram and display the HistogramLUTTool"""
        return self.processor.compute_histogram

    @compute_histogram.setter
    def compute_histogram(self, v: bool):
        self.processor.compute_histogram = v
        self._reset_histogram()

    @property
    def spatial_func(self) -> Callable[[xr.DataArray], xr.DataArray] | None:
        """get or set the spatial_func, see docstring for details"""
        return self.processor.spatial_func

    @spatial_func.setter
    def spatial_func(
        self, func: Callable[[xr.DataArray], xr.DataArray]
    ) -> Callable | None:
        self.processor.spatial_func = func
        self.processor._recompute_histogram()
        self._reset_histogram()

    def _tooltip_handler(self, graphic, pick_info):
        # TODO: need to do this better
        # get graphic within the collection
        n_index = np.argwhere(self.graphic.graphics == graphic).item()
        p_index = pick_info["vertex_index"]
        return self.processor.tooltip_format(n_index, p_index)
