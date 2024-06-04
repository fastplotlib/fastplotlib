from typing import *
import weakref

import numpy as np
from numpy.typing import NDArray

import pygfx

from ..utils import quick_min_max
from ._base import Graphic, Interaction
from .selectors import LinearSelector, LinearRegionSelector
from ._features import (
    TextureArray,
    ImageCmap,
    ImageVmin,
    ImageVmax,
    ImageInterpolation,
    ImageCmapInterpolation,
    WGPU_MAX_TEXTURE_SIZE
)


class _AddSelectorsMixin:
    def add_linear_selector(
        self, selection: int = None, padding: float = None, **kwargs
    ) -> LinearSelector:
        """
        Adds a :class:`.LinearSelector`.

        Parameters
        ----------
        selection: int, optional
            initial position of the selector

        padding: float, optional
            pad the length of the selector

        kwargs:
            passed to :class:`.LinearSelector`

        Returns
        -------
        LinearSelector

        """

        # default padding is 15% the height or width of the image
        if "axis" in kwargs.keys():
            axis = kwargs["axis"]
        else:
            axis = "x"

        (
            bounds_init,
            limits,
            size,
            origin,
            axis,
            end_points,
        ) = self._get_linear_selector_init_args(padding, **kwargs)

        if selection is None:
            selection = limits[0]

        if selection < limits[0] or selection > limits[1]:
            raise ValueError(
                f"the passed selection: {selection} is beyond the limits: {limits}"
            )

        selector = LinearSelector(
            selection=selection,
            limits=limits,
            end_points=end_points,
            parent=weakref.proxy(self),
            **kwargs,
        )

        self._plot_area.add_graphic(selector, center=False)
        selector.position_z = self.position_z + 1

        return weakref.proxy(selector)

    def add_linear_region_selector(
        self, padding: float = None, **kwargs
    ) -> LinearRegionSelector:
        """
        Add a :class:`.LinearRegionSelector`.

        Parameters
        ----------
        padding: float, optional
            Extends the linear selector along the y-axis to make it easier to interact with.

        kwargs: optional
            passed to ``LinearRegionSelector``

        Returns
        -------
        LinearRegionSelector
            linear selection graphic

        """

        (
            bounds_init,
            limits,
            size,
            origin,
            axis,
            end_points,
        ) = self._get_linear_selector_init_args(padding, **kwargs)

        # create selector
        selector = LinearRegionSelector(
            selection=bounds_init,
            limits=limits,
            size=size,
            origin=origin,
            parent=weakref.proxy(self),
            fill_color=(0, 0, 0.35, 0.2),
            **kwargs,
        )

        self._plot_area.add_graphic(selector, center=False)
        # so that it is above this graphic
        selector.position_z = self.position_z + 3

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

        if padding is None:
            if axis == "x":
                # based on number of rows
                padding = int(data.shape[0] * 0.15)
            elif axis == "y":
                # based on number of columns
                padding = int(data.shape[1] * 0.15)

        if axis == "x":
            offset = self.position_x
            # x limits, number of columns
            limits = (offset, data.shape[1] - 1)

            # size is number of rows + padding
            # used by LinearRegionSelector but not LinearSelector
            size = data.shape[0] + padding

            # initial position of the selector
            # center row
            position_y = data.shape[0] / 2

            # need y offset too for this
            origin = (limits[0] - offset, position_y + self.position_y)

            # endpoints of the data range
            # used by linear selector but not linear region
            # padding, n_rows + padding
            end_points = (0 - padding, data.shape[0] + padding)
        else:
            offset = self.position_y
            # y limits
            limits = (offset, data.shape[0] - 1)

            # width + padding
            # used by LinearRegionSelector but not LinearSelector
            size = data.shape[1] + padding

            # initial position of the selector
            position_x = data.shape[1] / 2

            # need x offset too for this
            origin = (position_x + self.position_x, limits[0] - offset)

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
    def __init__(self, geometry, material, row_chunk_ix: int, col_chunk_ix: int, **kwargs):
        super().__init__(geometry, material, **kwargs)

        self._row_chunk_index = row_chunk_ix
        self._col_chunk_index = col_chunk_ix

    def _wgpu_get_pick_info(self, pick_value):
        pick_info = super()._wgpu_get_pick_info(pick_value)

        row_start_ix = WGPU_MAX_TEXTURE_SIZE * self.row_chunk_index
        col_start_ix = WGPU_MAX_TEXTURE_SIZE * self.col_chunk_index

        # adjust w.r.t. chunk
        x, y = pick_info["index"]
        x += col_start_ix
        y += row_start_ix
        pick_info["index"] = (x, y)

        xp, yp = pick_info["pixel_coord"]
        xp += col_start_ix
        yp += row_start_ix
        pick_info["pixel_coord"] = (xp, yp)

        # add row chunk and col chunk index to pick_info dict
        return {
            **pick_info,
            "row_chunk_index": self.row_chunk_index,
            "col_chunk_index": self.col_chunk_index,
        }

    @property
    def row_chunk_index(self) -> int:
        return self._row_chunk_index

    @property
    def col_chunk_index(self) -> int:
        return self._col_chunk_index


class ImageGraphic(Graphic, Interaction, _AddSelectorsMixin):
    features = {"data", "cmap", "vmin", "vmax"}

    @property
    def data(self) -> NDArray:
        """Get or set the image data"""
        return self._data

    @data.setter
    def data(self, data):
        self._data[:] = data

    @property
    def cmap(self) -> str:
        """colormap name"""
        return self._cmap.value

    @cmap.setter
    def cmap(self, name: str):
        self._cmap.set_value(self, name)

    @property
    def vmin(self) -> float:
        """lower contrast limit"""
        return self._vmin.value

    @vmin.setter
    def vmin(self, value: float):
        self._vmin.set_value(self, value)

    @property
    def vmax(self) -> float:
        """upper contrast limit"""
        return self._vmax.value

    @vmax.setter
    def vmax(self, value: float):
        self._vmax.set_value(self, value)

    @property
    def interpolation(self) -> str:
        """image data interpolation method"""
        return self._interpolation.value

    @interpolation.setter
    def interpolation(self, value: str):
        self._interpolation.set_value(self, value)

    @property
    def cmap_interpolation(self) -> str:
        """cmap interpolation method"""
        return self._cmap_interpolation.value

    @cmap_interpolation.setter
    def cmap_interpolation(self, value: str):
        self._cmap_interpolation.set_value(self, value)

    def __init__(
        self,
        data: Any,
        vmin: int = None,
        vmax: int = None,
        cmap: str = "plasma",
        interpolation: str = "nearest",
        cmap_interpolation: str = "linear",
        isolated_buffer: bool = True,
        *args,
        **kwargs,
    ):
        """
        Create an Image Graphic

        Parameters
        ----------
        data: array-like
            array-like, usually numpy.ndarray, must support ``memoryview()``
            | shape must be ``[x_dim, y_dim]``

        vmin: int, optional
            minimum value for color scaling, calculated from data if not provided

        vmax: int, optional
            maximum value for color scaling, calculated from data if not provided

        cmap: str, optional, default "plasma"
            colormap to use to display the data

        interpolation: str, optional, default "nearest"
            interpolation filter, one of "nearest" or "linear"

        cmap_interpolation: str, optional, default "linear"
            colormap interpolation method, one of "nearest" or "linear"

        isolated_buffer: bool, default True
            If True, initialize a buffer with the same shape as the input data and then
            set the data, useful if the data arrays are ready-only such as memmaps.
            If False, the input array is itself used as the buffer.

        args:
            additional arguments passed to Graphic

        kwargs:
            additional keyword arguments passed to Graphic

        Features
        --------

        **data**: :class:`.HeatmapDataFeature`
            Manages the data buffer displayed in the HeatmapGraphic

        **cmap**: :class:`.HeatmapCmapFeature`
            Manages the colormap

        **present**: :class:`.PresentFeature`
            Control the presence of the Graphic in the scene

        """

        super().__init__(*args, **kwargs)

        world_object = pygfx.Group()

        self._data = TextureArray(data, isolated_buffer=isolated_buffer)

        if (vmin is None) or (vmax is None):
            vmin, vmax = quick_min_max(data)

        self._vmin = ImageVmin(vmin)
        self._vmax = ImageVmax(vmax)

        self._cmap = ImageCmap(cmap)

        self._interpolation = ImageInterpolation(interpolation)
        self._cmap_interpolation = ImageCmapInterpolation(cmap_interpolation)

        self._material = pygfx.ImageBasicMaterial(
            clim=(vmin, vmax),
            map=self._cmap.texture,
            interpolatio=self._interpolation.value,
            map_interpolation=self._cmap_interpolation.value,
            pick_write=True,
        )

        for row_ix in range(self._data.row_indices.size):
            for col_ix in range(self._data.col_indices.size):
                img = _ImageTile(
                    geometry=pygfx.Geometry(grid=self._data.buffer[row_ix, col_ix]),
                    material=self._material,
                    row_chunk_ix=row_ix,
                    col_chunk_ix=col_ix
                )

                img.world.x = self._data.row_indices[row_ix]
                img.world.y = self._data.row_indices[col_ix]

                world_object.add(img)

        self._set_world_object(world_object)