import numpy as np

from ._base import GraphicFeatureIndexable, cleanup_slice
from pygfx import Color


class ColorFeature(GraphicFeatureIndexable):
    def __init__(self, parent, colors, n_colors, alpha: float = 1.0):
        """
        ColorFeature

        Parameters
        ----------
        parent: Graphic or GraphicCollection

        colors: str, array, or iterable
            specify colors as a single human readable string, RGBA array,
            or an iterable of strings or RGBA arrays

        n_colors: number of colors to hold, if passing in a single str or single RGBA array
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
        else:
            # assume it's a single color, use pygfx.Color to parse it
            c = Color(colors)
            data = np.repeat(np.array([c]), n_colors, axis=0)

        if alpha != 1.0:
            data[:, -1] = alpha

        super(ColorFeature, self).__init__(parent, data)

    @property
    def _buffer(self):
        return self._parent.world_object.geometry.colors

    def __setitem__(self, key, value):
        # parse numerical slice indices
        if isinstance(key, slice):
            _key = cleanup_slice(key, self._upper_bound)
            indices = range(_key.start, _key.stop, _key.step)

        # or single numerical index
        elif isinstance(key, int):
            if key > self._upper_bound:
                raise IndexError("Index out of bounds")
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
            self._buffer.data[key] = value

            # update range
            # first slice obj is going to be the indexing so use key[0]
            # key[1] is going to be RGBA so get rid of it to pass to _update_range
            # _key = cleanup_slice(key[0], self._upper_bound)
            self._update_range(key)
            return

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

        self._buffer.data[key] = new_colors

        self._update_range(key)

    def _update_range(self, key):
        self._update_range_indices(key)
        # if isinstance(key, int):
        #     self._buffer.update_range(key, size=1)
        #     return
        #
        # # else assume it's a slice
        # if key.step == 1:  # we cleaned up the slice obj so step of None becomes 1
        #     # update range according to size using the offset
        #     self._buffer.update_range(offset=key.start, size=key.stop - key.start)
        #
        # else:
        #     step = key.step
        #     # convert slice to indices
        #     ixs = range(key.start, key.stop, step)
        #     for ix in ixs:
        #         self._buffer.update_range(ix, size=1)

    def __getitem__(self, item):
        return self._buffer.data[item]

    def __repr__(self):
        return repr(self._buffer.data)
