from typing import *
from math import ceil
from itertools import product

import numpy as np
import pygfx
from pygfx.utils import unpack_bitfield

from ._base import Graphic, Interaction, PreviouslyModifiedData
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

        texture_view = pygfx.Texture(buffer_init, dim=2).get_view(filter=filter)

        geometry = pygfx.Geometry(grid=texture_view)

        # if data is RGB
        if data.ndim == 3:
            self.cmap = None
            material = pygfx.ImageBasicMaterial(clim=(vmin, vmax))
        # if data is just 2D without color information, use colormap LUT
        else:
            self.cmap = ImageCmapFeature(self, cmap)
            material = pygfx.ImageBasicMaterial(clim=(vmin, vmax), map=self.cmap())

        self._world_object: pygfx.Image = pygfx.Image(
            geometry,
            material
        )

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


class _ImageTile(pygfx.Image):
    """
    Similar to pygfx.Image, only difference is that it contains a few properties to keep track of
    row chunk index, column chunk index


    """
    def _wgpu_get_pick_info(self, pick_value):
        tex = self.geometry.grid
        if hasattr(tex, "texture"):
            tex = tex.texture  # tex was a view
        # This should match with the shader
        values = unpack_bitfield(pick_value, wobject_id=20, x=22, y=22)
        x = values["x"] / 4194304 * tex.size[0] - 0.5
        y = values["y"] / 4194304 * tex.size[1] - 0.5
        ix, iy = int(x + 0.5), int(y + 0.5)
        return {
            "index": (ix, iy),
            "pixel_coord": (x - ix, y - iy),
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

        self._world_object = pygfx.Group()

        if (vmin is None) or (vmax is None):
            vmin, vmax = quick_min_max(data)

        self.cmap = HeatmapCmapFeature(self, cmap)
        self._material = pygfx.ImageBasicMaterial(clim=(vmin, vmax), map=self.cmap())

        for start, stop, chunk in zip(start_ixs, stop_ixs, chunks):
            row_start, col_start = start
            row_stop, col_stop = stop

            # x and y positions of the Tile in world space coordinates
            y_pos, x_pos = row_start, col_start

            tex_view = pygfx.Texture(buffer_init[row_start:row_stop, col_start:col_stop], dim=2).get_view(filter=filter)
            geometry = pygfx.Geometry(grid=tex_view)
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
