import numpy as np

from ._base import GraphicFeature, GraphicFeatureIndexable, cleanup_slice, FeatureEvent, cleanup_array_slice
from ...utils import make_colors, get_cmap_texture, make_pygfx_colors, parse_cmap_values
from pygfx import Color


class ColorFeature(GraphicFeatureIndexable):
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
    @property
    def buffer(self):
        return self._parent.world_object.geometry.colors

    def __getitem__(self, item):
        return self.buffer.data[item]

    def __init__(self, parent, colors, n_colors: int, alpha: float = 1.0, collection_index: int = None):
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
        # if provided as a numpy array of str
        if isinstance(colors, np.ndarray):
            if colors.dtype.kind in ["U", "S"]:
                colors = colors.tolist()
        # if the color is provided as a numpy array
        if isinstance(colors, np.ndarray):
            if colors.shape == (4,):  # single RGBA array
                data = np.repeat(
                    np.array([colors]),
                    n_colors,
                    axis=0
                )
            # else assume it's already a stack of RGBA arrays, keep this directly as the data
            elif colors.ndim == 2:
                if colors.shape[1] != 4 and colors.shape[0] != n_colors:
                    raise ValueError(
                        "Valid array color arguments must be a single RGBA array or a stack of "
                        "RGBA arrays for each datapoint in the shape [n_datapoints, 4]"
                    )
                data = colors
            else:
                raise ValueError(
                    "Valid array color arguments must be a single RGBA array or a stack of "
                    "RGBA arrays for each datapoint in the shape [n_datapoints, 4]"
                )

        # if the color is provided as an iterable
        elif isinstance(colors, (list, tuple, np.ndarray)):
            # if iterable of str
            if all([isinstance(val, str) for val in colors]):
                if not len(colors) == n_colors:
                    raise ValueError(
                        f"Valid iterable color arguments must be a `tuple` or `list` of `str` "
                        f"where the length of the iterable is the same as the number of datapoints."
                    )

                data = np.vstack([np.array(Color(c)) for c in colors])

            # if it's a single RGBA array as a tuple/list
            elif len(colors) == 4:
                c = Color(colors)
                data = np.repeat(np.array([c]), n_colors, axis=0)

            else:
                raise ValueError(
                    f"Valid iterable color arguments must be a `tuple` or `list` representing RGBA values or "
                    f"an iterable of `str` with the same length as the number of datapoints."
                )
        elif isinstance(colors, str):
            if colors == "random":
                data = np.random.rand(n_colors, 4)
                data[:, -1] = alpha
            else:
                data = make_pygfx_colors(colors, n_colors)
        else:
            # assume it's a single color, use pygfx.Color to parse it
            data = make_pygfx_colors(colors, n_colors)

        if alpha != 1.0:
            data[:, -1] = alpha

        super(ColorFeature, self).__init__(parent, data, collection_index=collection_index)

    def __setitem__(self, key, value):
        # parse numerical slice indices
        if isinstance(key, slice):
            _key = cleanup_slice(key, self._upper_bound)
            indices = range(_key.start, _key.stop, _key.step)

        # or single numerical index
        elif isinstance(key, (int, np.integer)):
            key = cleanup_slice(key, self._upper_bound)
            indices = [key]

        elif isinstance(key, tuple):
            if not isinstance(value, (float, int, np.ndarray)):
                raise ValueError(
                    "If using multiple-fancy indexing for color, you can only set numerical"
                    "values since this sets the RGBA array data directly."
                )

            if len(key) != 2:
                raise ValueError("fancy indexing for colors must be 2-dimension, i.e. [n_datapoints, RGBA]")

            # set the user passed data directly
            self.buffer.data[key] = value

            # update range
            # first slice obj is going to be the indexing so use key[0]
            # key[1] is going to be RGBA so get rid of it to pass to _update_range
            # _key = cleanup_slice(key[0], self._upper_bound)
            self._update_range(key)
            self._feature_changed(key, value)
            return

        elif isinstance(key, np.ndarray):
            key = cleanup_array_slice(key, self._upper_bound)
            if key is None:
                return

            indices = key

        else:
            raise TypeError("Graphic features only support integer and numerical fancy indexing")

        new_data_size = len(indices)

        if not isinstance(value, np.ndarray):
            color = np.array(Color(value))  # pygfx color parser
            # make it of shape [n_colors_modify, 4]
            new_colors = np.repeat(
                np.array([color]).astype(np.float32),
                new_data_size,
                axis=0
            )

        # if already a numpy array
        elif isinstance(value, np.ndarray):
            # if a single color provided as numpy array
            if value.shape == (4,):
                new_colors = value.astype(np.float32)
                # if there are more than 1 datapoint color to modify
                if new_data_size > 1:
                    new_colors = np.repeat(
                        np.array([new_colors]).astype(np.float32),
                        new_data_size,
                        axis=0
                    )

            elif value.ndim == 2:
                if value.shape[1] != 4 and value.shape[0] != new_data_size:
                    raise ValueError("numpy array passed to color must be of shape (4,) or (n_colors_modify, 4)")
                # if there is a single datapoint to change color of but user has provided shape [1, 4]
                if new_data_size == 1:
                    new_colors = value.ravel().astype(np.float32)
                else:
                    new_colors = value.astype(np.float32)

            else:
                raise ValueError("numpy array passed to color must be of shape (4,) or (n_colors_modify, 4)")

        self.buffer.data[key] = new_colors

        self._update_range(key)
        self._feature_changed(key, new_colors)

    def _update_range(self, key):
        self._update_range_indices(key)

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


class CmapFeature(ColorFeature):
    """
    Indexable colormap feature, mostly wraps colors and just provides a way to set colormaps.

    Same event pick info as :class:`ColorFeature`
    """
    def __init__(self, parent, colors, cmap_name: str, cmap_values: np.ndarray):
        super(ColorFeature, self).__init__(parent, colors)

        self._cmap_name = cmap_name
        self._cmap_values = cmap_values

    def __setitem__(self, key, cmap_name):
        key = cleanup_slice(key, self._upper_bound)
        if not isinstance(key, (slice, np.ndarray)):
            raise TypeError("Cannot set cmap on single indices, must pass a slice object, "
                            "numpy.ndarray or set it on the entire data.")

        if isinstance(key, slice):
            n_colors = len(range(key.start, key.stop, key.step))

        else:
            # numpy array
            n_colors = key.size

        colors = parse_cmap_values(
            n_colors=n_colors,
            cmap_name=cmap_name,
            cmap_values=self._cmap_values
        )

        self._cmap_name = cmap_name
        super(CmapFeature, self).__setitem__(key, colors)

    @property
    def values(self) -> np.ndarray:
        return self._cmap_values

    @values.setter
    def values(self, values: np.ndarray):
        if not isinstance(values, np.ndarray):
            values = np.array(values)

        colors = parse_cmap_values(
            n_colors=self().shape[0],
            cmap_name=self._cmap_name,
            cmap_values=values
        )

        self._cmap_values = values

        super(CmapFeature, self).__setitem__(slice(None), colors)


class ImageCmapFeature(GraphicFeature):
    """
    Colormap for :class:`ImageGraphic`

    **event pick info:**

     ================ =================== ===============
      key              type                description
     ================ =================== ===============
      "index"          ``None``            not used
      "name"           ``str``             colormap name
      "world_object"   pygfx.WorldObject   world object
      "vmin"           ``float``           minimum value
      "vmax"           ``float``           maximum value
     ================ =================== ===============


    """
    def __init__(self, parent, cmap: str):
        cmap_texture_view = get_cmap_texture(cmap)
        super(ImageCmapFeature, self).__init__(parent, cmap_texture_view)
        self.name = cmap

    def _set(self, cmap_name: str):
        if self._parent.data().ndim > 2:
            return

        self._parent.world_object.material.map.data[:] = make_colors(256, cmap_name)
        self._parent.world_object.material.map.update_range((0, 0, 0), size=(256, 1, 1))
        self.name = cmap_name

        self._feature_changed(key=None, new_data=self.name)

    @property
    def vmin(self) -> float:
        """Minimum contrast limit."""
        return self._parent.world_object.material.clim[0]

    @vmin.setter
    def vmin(self, value: float):
        """Minimum contrast limit."""
        self._parent.world_object.material.clim = (
            value,
            self._parent.world_object.material.clim[1]
        )
        self._feature_changed(key=None, new_data=None)

    @property
    def vmax(self) -> float:
        """Maximum contrast limit."""
        return self._parent.world_object.material.clim[1]

    @vmax.setter
    def vmax(self, value: float):
        """Maximum contrast limit."""
        self._parent.world_object.material.clim = (
            self._parent.world_object.material.clim[0],
            value
        )
        self._feature_changed(key=None, new_data=None)

    def _feature_changed(self, key, new_data):
        # this is a non-indexable feature so key=None

        pick_info = {
            "index": None,
            "world_object": self._parent.world_object,
            "name": self.name,
            "vmin": self.vmin,
            "vmax": self.vmax
        }

        event_data = FeatureEvent(type="cmap", pick_info=pick_info)

        self._call_event_handlers(event_data)


class HeatmapCmapFeature(ImageCmapFeature):
    """
    Colormap for :class:`HeatmapGraphic`

    Same event pick info as :class:`ImageCmapFeature`
    """

    def _set(self, cmap_name: str):
        self._parent._material.map.data[:] = make_colors(256, cmap_name)
        self._parent._material.map.update_range((0, 0, 0), size=(256, 1, 1))
        self.name = cmap_name

        self._feature_changed(key=None, new_data=self.name)
