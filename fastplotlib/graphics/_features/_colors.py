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

    def __setitem__(self, key, value):
        if isinstance(key, (int, np.ndarray, tuple, slice, range)):
            key = self.cleanup_key(key)

        elif isinstance(key, tuple):
            # directly setting RGBA values on every datapoint
            if not isinstance(value, (float, int, np.ndarray)):
                raise ValueError(
                    "If using multiple-fancy indexing for color, you can only set numerical"
                    "values since this sets the RGBA array data directly."
                )

            if len(key) != 2:
                raise ValueError(
                    "fancy indexing for colors must be 2-dimension, i.e. [n_datapoints, RGBA]"
                )

            # set the user passed data directly
            self.buffer.data[key] = value

            # update range
            # first slice obj is going to be the datapoints to modify so use key[0]
            # key[1] is going to be RGBA so get rid of it to pass to _update_range
            key = self.cleanup_key(key[0])
            self._update_range(key)

            self._feature_changed(key, value)
            return

        else:
            raise TypeError(
                "Graphic features only support integer and numerical fancy indexing"
            )

        new_data_size = len(key)

        if not isinstance(value, np.ndarray):
            color = np.array(pygfx.Color(value))  # pygfx color parser
            # make it of shape [n_colors_modify, 4]
            new_colors = np.repeat(
                np.array([color]).astype(np.float32), new_data_size, axis=0
            )

        # if already a numpy array
        elif isinstance(value, np.ndarray):
            # if a single color provided as numpy array
            if value.shape == (4,):
                new_colors = value.astype(np.float32)
                # if there are more than 1 datapoint color to modify
                if new_data_size > 1:
                    new_colors = np.repeat(
                        np.array([new_colors]).astype(np.float32), new_data_size, axis=0
                    )

            elif value.ndim == 2:
                if value.shape[1] != 4 and value.shape[0] != new_data_size:
                    raise ValueError(
                        "numpy array passed to color must be of shape (4,) or (n_colors_modify, 4)"
                    )
                # if there is a single datapoint to change color of but user has provided shape [1, 4]
                if new_data_size == 1:
                    new_colors = value.ravel().astype(np.float32)
                else:
                    new_colors = value.astype(np.float32)

            else:
                raise ValueError(
                    "numpy array passed to color must be of shape (4,) or (n_colors_modify, 4)"
                )

        else:
            raise TypeError

        self.buffer.data[key] = new_colors

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

    def __repr__(self) -> str:
        s = f"ColorsFeature for {self._parent}. Call `<graphic>.colors()` to get values."
        return s


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
