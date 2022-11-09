from typing import Any

import numpy as np
import pygfx

from fastplotlib.utils import get_colors, map_labels_to_colors


class Graphic:
    def __init__(
            self,
            data,
            colors: np.ndarray = None,
            colors_length: int = None,
            cmap: str = None,
            alpha: float = 1.0,
            name: str = None
    ):
        self.data = data.astype(np.float32)
        self.colors = None

        self.name = name

        # if colors_length is None:
        #     colors_length = self.data.shape[0]

        if colors is not False:
            self._set_colors(colors, colors_length, cmap, alpha, )

    def _set_colors(self, colors, colors_length, cmap, alpha):
        if colors_length is None:
            colors_length = self.data.shape[0]

        if colors is None and cmap is None:  # just white
            self.colors = np.vstack([[1., 1., 1., 1.]] * colors_length).astype(np.float32)

        elif (colors is None) and (cmap is not None):
            self.colors = get_colors(n_colors=colors_length, cmap=cmap, alpha=alpha)

        elif (colors is not None) and (cmap is None):
            # assume it's already an RGBA array
            colors = np.array(colors)
            if colors.shape == (1, 4) or colors.shape == (4,):
                self.colors = np.vstack([colors] * colors_length).astype(np.float32)
            elif colors.ndim == 2 and colors.shape[1] == 4 and colors.shape[0] == colors_length:
                self.colors = colors.astype(np.float32)
            else:
                raise ValueError(f"Colors array must have ndim == 2 and shape of [<n_datapoints>, 4]")

        elif (colors is not None) and (cmap is not None):
            if colors.ndim == 1 and np.issubdtype(colors.dtype, np.integer):
                # assume it's a mapping of colors
                self.colors = np.array(map_labels_to_colors(colors, cmap, alpha=alpha)).astype(np.float32)

        else:
            raise ValueError("Unknown color format")

    @property
    def children(self) -> pygfx.WorldObject:
        return self.world_object.children

    def update_data(self, data: Any):
        pass

    def __repr__(self):
        if self.name is not None:
            print("Graphic Name: " + self.name + "\n")
            print("Graphic Location: " + hex(id(self)) + "\n")
        else:
            print("Graphic Location: " + hex(id(self)) + "\n")
        print("Data:\n")
        print(self.data)
        return ""

