import numpy as np
import pygfx

from ...utils import (
    make_colors,
    get_cmap_texture,
    parse_cmap_values,
    quick_min_max,
)
from ._base import (
    GraphicFeature,
    BufferManager,
    FeatureEvent,
)
from .utils import parse_colors


class ColorFeature(BufferManager):
    """
    Manages the color buffer for :class:`LineGraphic` or :class:`ScatterGraphic`

    **event pick info:**

     ==================== =============================== =========================================================================
      key                  type                            description
     ==================== =============================== =========================================================================
      "index"              ``numpy.ndarray`` or ``None``   changed indices in the buffer
      "new_data"           ``numpy.ndarray`` or ``None``   new buffer data at the changed indices
      "collection-index"   int                             the index of the graphic within the collection that triggered the event
      "world_object"       pygfx.WorldObject               world object
     ==================== =============================== =========================================================================

    """

    def __init__(
        self,
        colors,
        n_colors: int,
        alpha: float = None,
        isolated_buffer: bool = True,
    ):
        """
        ColorFeature

        Parameters
        ----------
        parent: Graphic or GraphicCollection

        colors: str, array, or iterable
            specify colors as a single human readable string, RGBA array,
            or an iterable of strings or RGBA arrays

        n_colors: int
            number of colors to hold, if passing in a single str or single RGBA array

        alpha: float
            alpha value for the colors

        """
        data = parse_colors(colors, n_colors, alpha)
        
        super().__init__(data=data, isolated_buffer=isolated_buffer)

    def __setitem__(
            self,
            key: int | slice | np.ndarray[int | bool] | tuple[slice, ...],
            value: str | np.ndarray | tuple[float, float, float, float] | list[str]
    ):
        # if key is tuple assume they want to edit [n_points, RGBA] directly
        # if key is slice | range | int | np.ndarray, they are slicing only n_points, get n_points and parse colors

        if isinstance(key, tuple):
            # directly setting RGBA values, we do no parsing
            if not isinstance(value, (int, float, np.ndarray)):
                raise TypeError(
                    "Can only set from int, float, or array to set colors directly by slicing the entire array"
                )

        elif isinstance(key, int):
            # set color of one point
            n_colors = 1
            value = parse_colors(value, n_colors)

        elif isinstance(key, slice):
            # find n_colors by converting slice to range and then parse colors
            start, stop, step = key.indices(self.value.shape[0])

            n_colors = len(range(start, stop, step))

            value = parse_colors(value, n_colors)

        elif isinstance(key, np.ndarray):
            # make sure it's 1D
            if not key.ndim == 1:
                raise TypeError("If slicing colors with an array, it must be a 1D array")

            if key.dtype == bool:
                # make sure len is same
                if not key.size == self.buffer.data.shape[0]:
                    raise IndexError
                n_colors = np.count_nonzero(key)

            elif np.issubdtype(key.dtype, np.integer):
                n_colors = key.size

            else:
                raise TypeError

            value = parse_colors(value, n_colors)

        else:
            raise TypeError

        self.buffer.data[key] = value

        self._update_range(key)
        # self._feature_changed(key, new_colors)

    def _feature_changed(self, key, new_data):
        key = cleanup_slice(key, self._upper_bound)
        if isinstance(key, int):
            indices = [key]
        elif isinstance(key, slice):
            indices = range(key.start, key.stop, key.step)
        elif isinstance(key, np.ndarray):
            indices = key
        else:
            raise TypeError("feature changed key must be slice or int")

        pick_info = {
            "index": indices,
            "collection-index": self._collection_index,
            "world_object": self._parent.world_object,
            "new_data": new_data,
        }

        event_data = FeatureEvent(type="colors", pick_info=pick_info)

        self._call_event_handlers(event_data)


# class CmapFeature(ColorFeature):
#     """
#     Indexable colormap feature, mostly wraps colors and just provides a way to set colormaps.
#
#     Same event pick info as :class:`ColorFeature`
#     """
#
#     def __init__(self, parent, colors, cmap_name: str, cmap_values: np.ndarray):
#         # Skip the ColorFeature's __init__
#         super(ColorFeature, self).__init__(parent, colors)
#
#         self._cmap_name = cmap_name
#         self._cmap_values = cmap_values
#
#     def __setitem__(self, key, cmap_name):
#         key = cleanup_slice(key, self._upper_bound)
#         if not isinstance(key, (slice, np.ndarray)):
#             raise TypeError(
#                 "Cannot set cmap on single indices, must pass a slice object, "
#                 "numpy.ndarray or set it on the entire data."
#             )
#
#         if isinstance(key, slice):
#             n_colors = len(range(key.start, key.stop, key.step))
#
#         else:
#             # numpy array
#             n_colors = key.size
#
#         colors = parse_cmap_values(
#             n_colors=n_colors, cmap_name=cmap_name, cmap_values=self._cmap_values
#         )
#
#         self._cmap_name = cmap_name
#         super().__setitem__(key, colors)
#
#     @property
#     def name(self) -> str:
#         return self._cmap_name
#
#     @property
#     def values(self) -> np.ndarray:
#         return self._cmap_values
#
#     @values.setter
#     def values(self, values: np.ndarray):
#         if not isinstance(values, np.ndarray):
#             values = np.array(values)
#
#         colors = parse_cmap_values(
#             n_colors=self().shape[0], cmap_name=self._cmap_name, cmap_values=values
#         )
#
#         self._cmap_values = values
#
#         super().__setitem__(slice(None), colors)
#
#     def __repr__(self) -> str:
#         s = f"CmapFeature for {self._parent}, to get name or values: `<graphic>.cmap.name`, `<graphic>.cmap.values`"
#         return s
#
#
# class ImageCmapFeature(GraphicFeature):
#     """
#     Colormap for :class:`ImageGraphic`.
#
#     <graphic>.cmap() returns the Texture buffer for the cmap.
#
#     <graphic>.cmap.name returns the cmap name as a str.
#
#     **event pick info:**
#
#      ================ =================== ===============
#       key              type                description
#      ================ =================== ===============
#       "index"          ``None``            not used
#       "name"           ``str``             colormap name
#       "world_object"   pygfx.WorldObject   world object
#       "vmin"           ``float``           minimum value
#       "vmax"           ``float``           maximum value
#      ================ =================== ===============
#
#     """
#
#     def __init__(self, parent, cmap: str):
#         cmap_texture_view = get_cmap_texture(cmap)
#         super().__init__(parent, cmap_texture_view)
#         self._name = cmap
#
#     def _set(self, cmap_name: str):
#         if self._parent.data().ndim > 2:
#             return
#
#         self._parent.world_object.material.map.data[:] = make_colors(256, cmap_name)
#         self._parent.world_object.material.map.update_range((0, 0, 0), size=(256, 1, 1))
#         self._name = cmap_name
#
#         self._feature_changed(key=None, new_data=self._name)
#
#     @property
#     def name(self) -> str:
#         return self._name
#
#     @property
#     def vmin(self) -> float:
#         """Minimum contrast limit."""
#         return self._parent.world_object.material.clim[0]
#
#     @vmin.setter
#     def vmin(self, value: float):
#         """Minimum contrast limit."""
#         self._parent.world_object.material.clim = (
#             value,
#             self._parent.world_object.material.clim[1],
#         )
#         self._feature_changed(key=None, new_data=None)
#
#     @property
#     def vmax(self) -> float:
#         """Maximum contrast limit."""
#         return self._parent.world_object.material.clim[1]
#
#     @vmax.setter
#     def vmax(self, value: float):
#         """Maximum contrast limit."""
#         self._parent.world_object.material.clim = (
#             self._parent.world_object.material.clim[0],
#             value,
#         )
#         self._feature_changed(key=None, new_data=None)
#
#     def reset_vmin_vmax(self):
#         """Reset vmin vmax values based on current data"""
#         self.vmin, self.vmax = quick_min_max(self._parent.data())
#
#     def _feature_changed(self, key, new_data):
#         # this is a non-indexable feature so key=None
#
#         pick_info = {
#             "index": None,
#             "world_object": self._parent.world_object,
#             "name": self._name,
#             "vmin": self.vmin,
#             "vmax": self.vmax,
#         }
#
#         event_data = FeatureEvent(type="cmap", pick_info=pick_info)
#
#         self._call_event_handlers(event_data)
#
#     def __repr__(self) -> str:
#         s = f"ImageCmapFeature for {self._parent}. Use `<graphic>.cmap.name` to get str name of cmap."
#         return s
#
#
# class HeatmapCmapFeature(ImageCmapFeature):
#     """
#     Colormap for :class:`HeatmapGraphic`
#
#     Same event pick info as :class:`ImageCmapFeature`
#     """
#
#     def _set(self, cmap_name: str):
#         # in heatmap we use one material for all ImageTiles
#         self._parent._material.map.data[:] = make_colors(256, cmap_name)
#         self._parent._material.map.update_range((0, 0, 0), size=(256, 1, 1))
#         self._name = cmap_name
#
#         self._feature_changed(key=None, new_data=self.name)
#
#     @property
#     def vmin(self) -> float:
#         """Minimum contrast limit."""
#         return self._parent._material.clim[0]
#
#     @vmin.setter
#     def vmin(self, value: float):
#         """Minimum contrast limit."""
#         self._parent._material.clim = (value, self._parent._material.clim[1])
#
#     @property
#     def vmax(self) -> float:
#         """Maximum contrast limit."""
#         return self._parent._material.clim[1]
#
#     @vmax.setter
#     def vmax(self, value: float):
#         """Maximum contrast limit."""
#         self._parent._material.clim = (self._parent._material.clim[0], value)
