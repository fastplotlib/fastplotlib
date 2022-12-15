from typing import Any, List

import numpy as np
import pygfx

from fastplotlib.utils import get_colors, map_labels_to_colors

from abc import ABC, abstractmethod
from dataclasses import dataclass

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
            return f"'{self.name}' fastplotlib.{self.__class__.__name__} @ {hex(id(self))}"
        else:
            return f"fastplotlib.{self.__class__.__name__} @ {hex(id(self))}"

class Interaction(ABC):
    # make them abstract properties
    @property
    @abstractmethod
    def indices(self) -> Any:
        pass

    @indices.setter
    @abstractmethod
    def indices(self, indices: Any):
        pass

    @property
    @abstractmethod
    def features(self) -> List[str]:
        pass

    @abstractmethod
    def _set_feature(self, name: str, new_data: Any, indices: Any):
        pass

    @abstractmethod
    def link(self, event: str, target: Graphic, feature: str, new_data: Any, indices_mapper: callable = None):
        # event occurs, causes change in feature of current graphic to data indices from pick_info,
        # also causes change in target graphic to target feature at target data with corresponding or mapped
        # indices based on the indice_mapper function

        # events can be feature changes, when feature changes want to trigger an event

        # indice mapper takes in source features and maps to target features
        pass

    @abstractmethod
    def event_handler(self, event):
        pass

@dataclass
class EventData:
    """Class for keeping track of the info necessary for interactivity after event occurs."""
    def __init__(self, target: Graphic, feature: str, new_data: Any):
        self.target = target
        self.feature = feature
        self.new_data = new_data
