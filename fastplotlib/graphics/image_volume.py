from typing import *

import pygfx

from ..utils import quick_min_max
from ._base import Graphic
from .features import (
    TextureArray,
    ImageCmap,
    ImageVmin,
    ImageVmax,
    ImageInterpolation,
    ImageCmapInterpolation,
)


class _VolumeTile(pygfx.Volume):
    """
    Similar to pygfx.Volume, only difference is that it modifies the pick_info
    by adding the data row start indices that correspond to this chunk of the big Volume
    """

    def __init__(
        self,
        geometry,
        material,
        data_slice: tuple[slice, slice, slice],
        chunk_index: tuple[int, int, int],
        **kwargs,
    ):
        super().__init__(geometry, material, **kwargs)

        self._data_slice = data_slice
        self._chunk_index = chunk_index

    def _wgpu_get_pick_info(self, pick_value):
        pick_info = super()._wgpu_get_pick_info(pick_value)

        data_row_start, data_col_start, data_z_start = (
            self.data_slice[0].start,
            self.data_slice[1].start,
            self.data_slice[2].start,
        )

        # add the actual data row and col start indices
        x, y, z = pick_info["index"]
        x += data_col_start
        y += data_row_start
        z += data_z_start
        pick_info["index"] = (x, y, z)

        xp, yp, zp = pick_info["voxel_coord"]
        xp += data_col_start
        yp += data_row_start
        zp += data_z_start
        pick_info["voxel_coord"] = (xp, yp, zp)

        # add row chunk and col chunk index to pick_info dict
        return {
            **pick_info,
            "data_slice": self.data_slice,
            "chunk_index": self.chunk_index,
        }

    @property
    def data_slice(self) -> tuple[slice, slice, slice]:
        return self._data_slice

    @property
    def chunk_index(self) -> tuple[int, int, int]:
        return self._chunk_index


class ImageVolumeGraphic(Graphic):
    _features = {
        "data": TextureArray,
        "cmap": ImageCmap,
        "vmin": ImageVmin,
        "vmax": ImageVmax,
        "interpolation": ImageInterpolation,
        "cmap_interpolation": ImageCmapInterpolation,
    }

    def __init__(
            self,
            data: Any,
            mode: str = "ray",
            vmin: int = None,
            vmax: int = None,
            cmap: str = "plasma",
            interpolation: str = "nearest",
            cmap_interpolation: str = "linear",
            isolated_buffer: bool = True,
            **kwargs,
    ):
        valid_modes = ["basic", "ray", "slice", "iso", "mip", "minip"]
        if mode not in valid_modes:
            raise ValueError(f"invalid mode specified: {mode}, valid modes are: {valid_modes}")

        super().__init__(**kwargs)

        world_object = pygfx.Group()

        # texture array that manages the textures on the GPU that represent this image volume
        self._data = TextureArray(data, dim=3, isolated_buffer=isolated_buffer)

        if (vmin is None) or (vmax is None):
            vmin, vmax = quick_min_max(data)

        # other graphic features
        self._vmin = ImageVmin(vmin)
        self._vmax = ImageVmax(vmax)

        self._interpolation = ImageInterpolation(interpolation)

        # TODO: I'm assuming RGB volume images aren't supported???
        # use TextureMap for grayscale images
        self._cmap = ImageCmap(cmap)
        self._cmap_interpolation = ImageCmapInterpolation(cmap_interpolation)

        _map = pygfx.TextureMap(
            self._cmap.texture,
            filter=self._cmap_interpolation.value,
            wrap="clamp-to-edge",
        )

        material_cls = getattr(pygfx, f"Volume{mode.capitalize()}Material")

        # TODO: graphic features for the various material properties
        self._material = material_cls(
            clim=(self._vmin.value, self._vmax.value),
            map=_map,
            interpolation=self._interpolation.value,
            pick_write=True,
        )

        # iterate through each texture chunk and create
        # a _VolumeTile, offset the tile using the data indices
        for texture, chunk_index, data_slice in self._data:
            # create a _VolumeTile using the texture for this chunk
            vol = _VolumeTile(
                geometry=pygfx.Geometry(grid=texture),
                material=self._material,
                data_slice=data_slice,  # used to parse pick_info
                chunk_index=chunk_index,
            )

            # row and column start index for this chunk
            data_row_start = data_slice[0].start
            data_col_start = data_slice[1].start
            data_z_start = data_slice[2].start

            # offset tile position using the indices from the big data array
            # that correspond to this chunk
            vol.world.x = data_col_start
            vol.world.y = data_row_start
            vol.world.z = data_z_start

            world_object.add(vol)

        self._set_world_object(world_object)

    @property
    def data(self) -> TextureArray:
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

    def reset_vmin_vmax(self):
        """
        Reset the vmin, vmax by estimating it from the data

        Returns
        -------
        None

        """

        vmin, vmax = quick_min_max(self._data.value)
        self.vmin = vmin
        self.vmax = vmax
