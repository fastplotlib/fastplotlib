from typing import *

import numpy as np
import pygfx

from fastplotlib.utils import get_colors, map_labels_to_colors
from ._graphic_attribute import GraphicFeature, ColorFeature


class Graphic:
    def __init__(
            self,
            data,
            colors: Any = False,
            n_colors: int = None,
            cmap: str = None,
            alpha: float = 1.0,
            name: str = None
    ):
        """

        Parameters
        ----------
        data
        colors: Any
            if ``False``, no color generation is performed, cmap is also ignored.
        n_colors
        cmap
        alpha
        name
        """
        self.data = data.astype(np.float32)
        self.colors = None

        self.name = name

        if n_colors is None:
            n_colors = self.data.shape[0]

        if cmap is not None and colors is not False:
            colors = get_colors(n_colors=n_colors, cmap=cmap, alpha=alpha)

        if colors is not False:
            self.colors = ColorFeature(parent=self, colors=colors, n_colors=n_colors, alpha=alpha)

        valid_features = ["visible"]
        for attr_name in self.__dict__.keys():
            attr = getattr(self, attr_name)
            if isinstance(attr, GraphicFeature):
                valid_features.append(attr_name)

        self._valid_features = tuple(valid_features)

    @property
    def world_object(self) -> pygfx.WorldObject:
        return self._world_object

    @property
    def valid_features(self) -> Tuple[str]:
        return self._valid_features

    @property
    def visible(self) -> bool:
        return self.world_object.visible

    @visible.setter
    def visible(self, v):
        self.world_object.visible = v

    @property
    def children(self) -> pygfx.WorldObject:
        return self.world_object.children

    def update_data(self, data: Any):
        pass

    def __setattr__(self, key, value):
        if hasattr(self, key):
            attr = getattr(self, key)
            if isinstance(attr, GraphicFeature):
                attr._set(value)
                return

        super().__setattr__(key, value)

    def __repr__(self):
        if self.name is not None:
            return f"'{self.name}' fastplotlib.{self.__class__.__name__} @ {hex(id(self))}"
        else:
            return f"fastplotlib.{self.__class__.__name__} @ {hex(id(self))}"
