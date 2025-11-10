from typing import *

import numpy as np
import pygfx

from ..utils import quick_min_max
from ._base import Graphic
from .features import (
    TextureArrayVolume,
    ImageCmap,
    ImageVmin,
    ImageVmax,
    ImageInterpolation,
    ImageCmapInterpolation,
    VolumeRenderMode,
    VolumeIsoThreshold,
    VolumeIsoStepSize,
    VolumeIsoSubStepSize,
    VolumeIsoEmissive,
    VolumeIsoShininess,
    VolumeSlicePlane,
    VOLUME_RENDER_MODES,
    create_volume_material_kwargs,
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

        data_z_start, data_row_start, data_col_start = (
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
        "data": TextureArrayVolume,
        "cmap": ImageCmap,
        "vmin": ImageVmin,
        "vmax": ImageVmax,
        "interpolation": ImageInterpolation,
        "cmap_interpolation": ImageCmapInterpolation,
        "mode": VolumeRenderMode,
        "threshold": VolumeIsoThreshold,
        "step_size": VolumeIsoStepSize,
        "substep_size": VolumeIsoSubStepSize,
        "emissive": VolumeIsoEmissive,
        "shininess": VolumeIsoShininess,
        "plane": VolumeSlicePlane,
    }

    def __init__(
        self,
        data: Any,
        mode: str = "mip",
        vmin: float = None,
        vmax: float = None,
        cmap: str = "plasma",
        interpolation: str = "linear",
        cmap_interpolation: str = "linear",
        plane: tuple[float, float, float, float] = (0, 0, -1, 0),
        threshold: float = 0.5,
        step_size: float = 1.0,
        substep_size: float = 0.1,
        emissive: str | tuple | np.ndarray = (0, 0, 0),
        shininess: int = 30,
        isolated_buffer: bool = True,
        **kwargs,
    ):
        """
        Create an ImageVolumeGraphic.

        Parameters
        ----------
        data: array-like
            array-like, usually numpy.ndarray, must support ``memoryview()``.
            Shape must be [n_planes, n_rows, n_cols] for grayscale, or [n_planes, n_rows, n_cols, 3 | 4] for RGB(A)

        mode: str, default "mip"
            render mode, one of "mip", "minip", "iso" or "slice"

        vmin: float
            lower contrast limit

        vmax: float
            upper contrast limit

        cmap: str, default "plasma"
            colormap for grayscale volumes

        interpolation: str, default "linear"
            interpolation method for sampling pixels

        cmap_interpolation: str, default "linear"
            interpolation method for sampling from colormap

        plane: (float, float, float, float), default (0, 0, -1, 0)
            Slice volume at this plane. Sets (a, b, c, d) in the equation the defines a plane: ax + by + cz + d = 0.
            Used only if `mode` = "slice"

        threshold : float, default 0.5
            The threshold texture value at which the surface is rendered.
            Used only if `mode` = "iso"

        step_size : float, default 1.0
            The size of the initial ray marching step for the initial surface finding. Smaller values will result in
            more accurate surfaces but slower rendering.
            Used only if `mode` = "iso"

        substep_size : float, default 0.1
            The size of the raymarching step for the refined surface finding. Smaller values will result in more
            accurate surfaces but slower rendering.
            Used only if `mode` = "iso"

        emissive : Color, default (0, 0, 0, 1)
            The emissive color of the surface. I.e. the color that the object emits even when not lit by a light
            source. This color is added to the final color and unaffected by lighting. The alpha channel is ignored.
            Used only if `mode` = "iso"

        shininess : int, default 30
            How shiny the specular highlight is; a higher value gives a sharper highlight.
            Used only if `mode` = "iso"

        isolated_buffer: bool, default True
            If True, initialize a buffer with the same shape as the input data and then set the data, useful if the
            data arrays are ready-only such as memmaps. If False, the input array is itself used as the
            buffer - useful if the array is large.

        kwargs
            additional keyword arguments passed to :class:`.Graphic`

        """

        valid_modes = VOLUME_RENDER_MODES.keys()
        if mode not in valid_modes:
            raise ValueError(
                f"invalid mode specified: {mode}, valid modes are: {valid_modes}"
            )

        super().__init__(**kwargs)

        world_object = pygfx.Group()

        if isinstance(data, TextureArrayVolume):
            # share existing buffer
            self._data = data
        else:
            # create new texture array to manage buffer
            # texture array that manages the textures on the GPU that represent this image volume
            self._data = TextureArrayVolume(data, isolated_buffer=isolated_buffer)

        if (vmin is None) or (vmax is None):
            _vmin, _vmax = quick_min_max(self.data.value)
            if vmin is None:
                vmin = _vmin
            if vmax is None:
                vmax = _vmax

        # other graphic features
        self._vmin = ImageVmin(vmin)
        self._vmax = ImageVmax(vmax)

        self._interpolation = ImageInterpolation(interpolation)

        if self._data.value.ndim  == 4:
            # set map to None for RGB image volumes
            self._cmap = None
            self._texture_map = None
            self._cmap_interpolation = None

        elif self._data.value.ndim == 3:
            # use TextureMap for grayscale images
            self._cmap = ImageCmap(cmap)
            self._cmap_interpolation = ImageCmapInterpolation(cmap_interpolation)
            self._texture_map = pygfx.TextureMap(
                self._cmap.texture,
                filter=self._cmap_interpolation.value,
                wrap="clamp-to-edge",
            )
        else:
            raise ValueError(
                f"ImageVolumeGraphic `data` must have 3 dimensions for grayscale images, "
                f"or 4 dimensions for RGB(A) images.\n"
                f"You have passed a a data array with: {self._data.value.ndim} dimensions, "
                f"and of shape: {self._data.value.shape}"
            )

        self._plane = VolumeSlicePlane(plane)
        self._threshold = VolumeIsoThreshold(threshold)
        self._step_size = VolumeIsoStepSize(step_size)
        self._substep_size = VolumeIsoSubStepSize(substep_size)
        self._emissive = VolumeIsoEmissive(emissive)
        self._shininess = VolumeIsoShininess(shininess)

        material_kwargs = create_volume_material_kwargs(graphic=self, mode=mode)

        VolumeMaterialCls = VOLUME_RENDER_MODES[mode]

        self._material = VolumeMaterialCls(**material_kwargs)

        self._mode = VolumeRenderMode(mode)

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
            data_z_start = data_slice[0].start
            data_row_start = data_slice[1].start
            data_col_start = data_slice[2].start

            # offset tile position using the indices from the big data array
            # that correspond to this chunk
            vol.world.z = data_z_start
            vol.world.x = data_col_start
            vol.world.y = data_row_start

            world_object.add(vol)

        self._set_world_object(world_object)

    @property
    def data(self) -> TextureArrayVolume:
        """Get or set the image data"""
        return self._data

    @data.setter
    def data(self, data):
        self._data[:] = data

    @property
    def mode(self) -> str:
        """Get or set the volume rendering mode"""
        return self._mode.value

    @mode.setter
    def mode(self, mode: str):
        self._mode.set_value(self, mode)

    @property
    def cmap(self) -> str | None:
        """Get or set colormap name"""
        if self._cmap is not None:
            return self._cmap.value

    @cmap.setter
    def cmap(self, name: str):
        self._cmap.set_value(self, name)

    @property
    def vmin(self) -> float:
        """Get or set the lower contrast limit"""
        return self._vmin.value

    @vmin.setter
    def vmin(self, value: float):
        self._vmin.set_value(self, value)

    @property
    def vmax(self) -> float:
        """Get or set the upper contrast limit"""
        return self._vmax.value

    @vmax.setter
    def vmax(self, value: float):
        self._vmax.set_value(self, value)

    @property
    def interpolation(self) -> str:
        """Get or set  the image data interpolation method"""
        return self._interpolation.value

    @interpolation.setter
    def interpolation(self, value: str):
        self._interpolation.set_value(self, value)

    @property
    def cmap_interpolation(self) -> str | None:
        """Get or set the cmap interpolation method"""
        if self._cmap_interpolation is not None:
            return self._cmap_interpolation.value

    @cmap_interpolation.setter
    def cmap_interpolation(self, value: str):
        self._cmap_interpolation.set_value(self, value)

    @property
    def plane(self) -> tuple[float, float, float, float]:
        """Get or set displayed plane in the volume. Valid only for `slice` render mode."""
        return self._plane.value

    @plane.setter
    def plane(self, value: tuple[float, float, float, float]):
        if self.mode != "slice":
            raise TypeError("`plane` property is only valid for `slice` render mode.")

        self._plane.set_value(self, value)

    @property
    def threshold(self) -> float:
        """Get or set isosurface threshold, only for `iso` mode"""
        return self._threshold.value

    @threshold.setter
    def threshold(self, value: float):
        if self.mode != "iso":
            raise TypeError(
                "`threshold` property is only used for `iso` rendering mode"
            )

        self._threshold.set_value(self, value)

    @property
    def step_size(self) -> float:
        """Get or set isosurface step_size, only for `iso` mode"""
        return self._step_size.value

    @step_size.setter
    def step_size(self, value: float):
        if self.mode != "iso":
            raise TypeError(
                "`step_size` property is only used for `iso` rendering mode"
            )

        self._step_size.set_value(self, value)

    @property
    def substep_size(self) -> float:
        """Get or set isosurface substep_size, only for `iso` mode"""
        return self._substep_size.value

    @substep_size.setter
    def substep_size(self, value: float):
        if self.mode != "iso":
            raise TypeError(
                "`substep_size` property is only used for `iso` rendering mode"
            )

        self._substep_size.set_value(self, value)

    @property
    def emissive(self) -> pygfx.Color:
        """Get or set isosurface emissive color, only for `iso` mode. Pass a <str> color, RGBA array or pygfx.Color"""
        return self._emissive.value

    @emissive.setter
    def emissive(self, value: pygfx.Color | str | tuple | np.ndarray):
        if self.mode != "iso":
            raise TypeError("`emissive` property is only used for `iso` rendering mode")

        self._emissive.set_value(self, value)

    @property
    def shininess(self) -> int:
        """Get or set isosurface shininess"""
        return self._shininess.value

    @shininess.setter
    def shininess(self, value: int):
        if self.mode != "iso":
            raise TypeError(
                "`shininess` property is only used for `iso` rendering mode"
            )

        self._shininess.set_value(self, value)

    def reset_vmin_vmax(self):
        """
        Reset the vmin, vmax by *estimating* it from the data

        Returns
        -------
        None

        """

        vmin, vmax = quick_min_max(self.data.value)
        self.vmin = vmin
        self.vmax = vmax
