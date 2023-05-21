from typing import *
from math import ceil
from itertools import product
import weakref

import numpy as np
import pygfx

from ._base import Graphic, Interaction, PreviouslyModifiedData
from .selectors import LinearSelector, LinearRegionSelector
from .features import ImageCmapFeature, ImageDataFeature, HeatmapDataFeature, HeatmapCmapFeature
from .features._base import to_gpu_supported_dtype
from ..utils import quick_min_max


class ImageGraphic(Graphic, Interaction):
    feature_events = (
        "data",
        "cmap",
    )

    def __init__(
            self,
            data: Any,
            vmin: int = None,
            vmax: int = None,
            cmap: str = 'plasma',
            filter: str = "nearest",
            isolated_buffer: bool = True,
            *args,
            **kwargs
    ):
        """
        Create an Image Graphic

        Parameters
        ----------
        data: array-like
            array-like, usually numpy.ndarray, must support ``memoryview()``
            Tensorflow Tensors also work **probably**, but not thoroughly tested
            | shape must be ``[x_dim, y_dim]`` or ``[x_dim, y_dim, rgb]``
        vmin: int, optional
            minimum value for color scaling, calculated from data if not provided
        vmax: int, optional
            maximum value for color scaling, calculated from data if not provided
        cmap: str, optional, default "plasma"
            colormap to use to display the image data, ignored if data is RGB
        filter: str, optional, default "nearest"
            interpolation filter, one of "nearest" or "linear"
        isolated_buffer: bool, default True
            If True, initialize a buffer with the same shape as the input data and then
            set the data, useful if the data arrays are ready-only such as memmaps.
            If False, the input array is itself used as the buffer.
        args:
            additional arguments passed to Graphic
        kwargs:
            additional keyword arguments passed to Graphic

        Examples
        --------
        .. code-block:: python

            from fastplotlib import Plot
            # create a `Plot` instance
            plot = Plot()
            # make some random 2D image data
            data = np.random.rand(512, 512)
            # plot the image data
            plot.add_image(data=data)
            # show the plot
            plot.show()
        """

        super().__init__(*args, **kwargs)

        data = to_gpu_supported_dtype(data)

        # TODO: we need to organize and do this better
        if isolated_buffer:
            # initialize a buffer with the same shape as the input data
            # we do not directly use the input data array as the buffer
            # because if the input array is a read-only type, such as
            # numpy memmaps, we would not be able to change the image data
            buffer_init = np.zeros(shape=data.shape, dtype=data.dtype)
        else:
            buffer_init = data

        if (vmin is None) or (vmax is None):
            vmin, vmax = quick_min_max(data)

        texture = pygfx.Texture(buffer_init, dim=2)

        geometry = pygfx.Geometry(grid=texture)

        # if data is RGB
        if data.ndim == 3:
            self.cmap = None
            material = pygfx.ImageBasicMaterial(clim=(vmin, vmax), map_interpolation=filter)
        # if data is just 2D without color information, use colormap LUT
        else:
            self.cmap = ImageCmapFeature(self, cmap)
            material = pygfx.ImageBasicMaterial(clim=(vmin, vmax), map=self.cmap(), map_interpolation=filter)

        world_object = pygfx.Image(
            geometry,
            material
        )

        self._set_world_object(world_object)

        self.data = ImageDataFeature(self, data)
        # TODO: we need to organize and do this better
        if isolated_buffer:
            # if the buffer was initialized with zeros
            # set it with the actual data
            self.data = data

    @property
    def vmin(self) -> float:
        """Minimum contrast limit."""
        return self.world_object.material.clim[0]

    @vmin.setter
    def vmin(self, value: float):
        """Minimum contrast limit."""
        self.world_object.material.clim = (
            value,
            self.world_object.material.clim[1]
        )

    @property
    def vmax(self) -> float:
        """Maximum contrast limit."""
        return self.world_object.material.clim[1]

    @vmax.setter
    def vmax(self, value: float):
        """Maximum contrast limit."""
        self.world_object.material.clim = (
            self.world_object.material.clim[0],
            value
        )

    def _set_feature(self, feature: str, new_data: Any, indices: Any):
        pass

    def _reset_feature(self, feature: str):
        pass

    def add_linear_selector(self, selection: int = None, padding: float = 50, **kwargs) -> LinearSelector:
        """
        Adds a linear selector.

        Parameters
        ----------
        selection: int
            initial position of the selector

        padding: float
            pad the length of the selector

        kwargs
            passed to :class:`.LinearSelector`

        Returns
        -------
        LinearSelector

        """

        bounds_init, limits, size, origin, axis, end_points = self._get_linear_selector_init_args(padding, **kwargs)

        if selection is None:
            selection = limits[0]

        if selection < limits[0] or selection > limits[1]:
            raise ValueError(f"the passed selection: {selection} is beyond the limits: {limits}")

        selector = LinearSelector(
            selection=selection,
            limits=limits,
            end_points=end_points,
            parent=self,
            **kwargs
        )

        self._plot_area.add_graphic(selector, center=False)
        selector.position.z = self.position.z + 1

        return weakref.proxy(selector)

    def add_linear_region_selector(self, padding: float = 100.0, **kwargs) -> LinearRegionSelector:
        """
        Add a :class:`.LinearRegionSelector`. Selectors are just ``Graphic`` objects, so you can manage,
        remove, or delete them from a plot area just like any other ``Graphic``.

        Parameters
        ----------
        padding: float, default 100.0
            Extends the linear selector along the y-axis to make it easier to interact with.

        kwargs
            passed to ``LinearRegionSelector``

        Returns
        -------
        LinearRegionSelector
            linear selection graphic

        """

        bounds_init, limits, size, origin, axis, end_points = self._get_linear_selector_init_args(padding, **kwargs)

        # create selector
        selector = LinearRegionSelector(
            bounds=bounds_init,
            limits=limits,
            size=size,
            origin=origin,
            parent=self,
            **kwargs
        )

        self._plot_area.add_graphic(selector, center=False)
        # so that it is above this graphic
        selector.position.set_z(self.position.z + 3)
        selector.fill.material.color = (*selector.fill.material.color[:-1], 0.2)

        # PlotArea manages this for garbage collection etc. just like all other Graphics
        # so we should only work with a proxy on the user-end
        return weakref.proxy(selector)

    # TODO: this method is a bit of a mess, can refactor later
    def _get_linear_selector_init_args(self, padding: float, **kwargs):
        # computes initial bounds, limits, size and origin of linear selectors
        data = self.data()

        if "axis" in kwargs.keys():
            axis = kwargs["axis"]
        else:
            axis = "x"

        if axis == "x":
            offset = self.position.x
            # x limits, number of columns
            limits = (offset, data.shape[1])

            # size is number of rows + padding
            # used by LinearRegionSelector but not LinearSelector
            size = data.shape[0] + padding

            # initial position of the selector
            # center row
            position_y = data.shape[0] / 2

            # need y offset too for this
            origin = (limits[0] - offset, position_y + self.position.y)

            # endpoints of the data range
            # used by linear selector but not linear region
            # padding, n_rows + padding
            end_points = (0 - padding, data.shape[0] + padding)
        else:
            offset = self.position.y
            # y limits
            limits = (offset, data.shape[0])

            # width + padding
            # used by LinearRegionSelector but not LinearSelector
            size = data.shape[1] + padding

            # initial position of the selector
            position_x = data.shape[1] / 2

            # need x offset too for this
            origin = (position_x + self.position.x, limits[0] - offset)

            # endpoints of the data range
            # used by linear selector but not linear region
            end_points = (0 - padding, data.shape[1] + padding)

        # initial bounds are 20% of the limits range
        # used by LinearRegionSelector but not LinearSelector
        bounds_init = (limits[0], int(np.ptp(limits) * 0.2) + offset)

        return bounds_init, limits, size, origin, axis, end_points

    def _add_plot_area_hook(self, plot_area):
        self._plot_area = plot_area


class _ImageTile(pygfx.Image):
    """
    Similar to pygfx.Image, only difference is that it contains a few properties to keep track of
    row chunk index, column chunk index
    """
    def _wgpu_get_pick_info(self, pick_value):
        pick_info = super()._wgpu_get_pick_info(pick_value)

        # add row chunk and col chunk index to pick_info dict
        return {
            **pick_info,
            "row_chunk_index": self.row_chunk_index,
            "col_chunk_index": self.col_chunk_index
        }

    @property
    def row_chunk_index(self) -> int:
        return self._row_chunk_index

    @row_chunk_index.setter
    def row_chunk_index(self, index: int):
        self._row_chunk_index = index

    @property
    def col_chunk_index(self) -> int:
        return self._col_chunk_index

    @col_chunk_index.setter
    def col_chunk_index(self, index: int):
        self._col_chunk_index = index


class HeatmapGraphic(Graphic, Interaction):
    feature_events = (
        "data",
        "cmap",
    )

    def __init__(
            self,
            data: Any,
            vmin: int = None,
            vmax: int = None,
            cmap: str = 'plasma',
            filter: str = "nearest",
            chunk_size: int = 8192,
            isolated_buffer: bool = True,
            *args,
            **kwargs
    ):
        """
        Create an Image Graphic

        Parameters
        ----------
        data: array-like
            array-like, usually numpy.ndarray, must support ``memoryview()``
            Tensorflow Tensors also work **probably**, but not thoroughly tested
            | shape must be ``[x_dim, y_dim]``
        vmin: int, optional
            minimum value for color scaling, calculated from data if not provided
        vmax: int, optional
            maximum value for color scaling, calculated from data if not provided
        cmap: str, optional, default "plasma"
            colormap to use to display the data
        filter: str, optional, default "nearest"
            interpolation filter, one of "nearest" or "linear"
        chunk_size: int, default 8192, max 8192
            chunk size for each tile used to make up the heatmap texture
        isolated_buffer: bool, default True
            If True, initialize a buffer with the same shape as the input data and then
            set the data, useful if the data arrays are ready-only such as memmaps.
            If False, the input array is itself used as the buffer.
        args:
            additional arguments passed to Graphic
        kwargs:
            additional keyword arguments passed to Graphic

        Examples
        --------
        .. code-block:: python

            from fastplotlib import Plot
            # create a `Plot` instance
            plot = Plot()
            # make some random 2D image data
            data = np.random.rand(512, 512)
            # plot the image data
            plot.add_image(data=data)
            # show the plot
            plot.show()
        """

        super().__init__(*args, **kwargs)

        if chunk_size > 8192:
            raise ValueError("Maximum chunk size is 8192")

        data = to_gpu_supported_dtype(data)

        # TODO: we need to organize and do this better
        if isolated_buffer:
            # initialize a buffer with the same shape as the input data
            # we do not directly use the input data array as the buffer
            # because if the input array is a read-only type, such as
            # numpy memmaps, we would not be able to change the image data
            buffer_init = np.zeros(shape=data.shape, dtype=data.dtype)
        else:
            buffer_init = data

        row_chunks = range(ceil(data.shape[0] / chunk_size))
        col_chunks = range(ceil(data.shape[1] / chunk_size))

        chunks = list(product(row_chunks, col_chunks))
        # chunks is the index position of each chunk

        start_ixs = [list(map(lambda c: c * chunk_size, chunk)) for chunk in chunks]
        stop_ixs = [list(map(lambda c: c + chunk_size, chunk)) for chunk in start_ixs]

        world_object = pygfx.Group()
        self._set_world_object(world_object)

        if (vmin is None) or (vmax is None):
            vmin, vmax = quick_min_max(data)

        self.cmap = HeatmapCmapFeature(self, cmap)
        self._material = pygfx.ImageBasicMaterial(clim=(vmin, vmax), map=self.cmap(), map_interpolation=filter)

        for start, stop, chunk in zip(start_ixs, stop_ixs, chunks):
            row_start, col_start = start
            row_stop, col_stop = stop

            # x and y positions of the Tile in world space coordinates
            y_pos, x_pos = row_start, col_start

            texture = pygfx.Texture(buffer_init[row_start:row_stop, col_start:col_stop], dim=2)
            geometry = pygfx.Geometry(grid=texture)
            # material = pygfx.ImageBasicMaterial(clim=(0, 1), map=self.cmap())

            img = _ImageTile(geometry, self._material)

            # row and column chunk index for this Tile
            img.row_chunk_index = chunk[0]
            img.col_chunk_index = chunk[1]

            img.position.set_x(x_pos)
            img.position.set_y(y_pos)

            self.world_object.add(img)

        self.data = HeatmapDataFeature(self, buffer_init)
        # TODO: we need to organize and do this better
        if isolated_buffer:
            # if the buffer was initialized with zeros
            # set it with the actual data
            self.data = data

    @property
    def vmin(self) -> float:
        """Minimum contrast limit."""
        return self._material.clim[0]

    @vmin.setter
    def vmin(self, value: float):
        """Minimum contrast limit."""
        self._material.clim = (
            value,
            self._material.clim[1]
        )

    @property
    def vmax(self) -> float:
        """Maximum contrast limit."""
        return self._material.clim[1]

    @vmax.setter
    def vmax(self, value: float):
        """Maximum contrast limit."""
        self._material.clim = (
            self._material.clim[0],
            value
        )

    def _set_feature(self, feature: str, new_data: Any, indices: Any):
        pass

    def _reset_feature(self, feature: str):
        pass
