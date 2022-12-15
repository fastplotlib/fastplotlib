<<<<<<< HEAD
<<<<<<< HEAD
from typing import *
=======
from typing import Any, List
>>>>>>> 95e77a1 (reorg)
=======
from typing import *
>>>>>>> 71eb48f (small changes and reorg)

import pygfx

from ..utils import get_colors
from .features import GraphicFeature, DataFeature, ColorFeature, PresentFeature

from abc import ABC, abstractmethod
from dataclasses import dataclass

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
        data: array-like
            data to show in the graphic, must be float32.
            Automatically converted to float32 for numpy arrays.
            Tensorflow Tensors also work but this is not fully
            tested and might not be supported in the future.

        colors: Any
            if ``False``, no color generation is performed, cmap is also ignored.

        n_colors

        cmap: str
            name of colormap to use

        alpha: float, optional
            alpha value for the colors

        name: str, optional
            name this graphic, makes it indexable within plots

        """
        # self.data = data.astype(np.float32)
        self.data = DataFeature(parent=self, data=data, graphic_name=self.__class__.__name__)
        self.colors = None

        self.name = name
        self.registered_callbacks = dict()

        if n_colors is None:
            n_colors = self.data.feature_data.shape[0]

        if cmap is not None and colors is not False:
            colors = get_colors(n_colors=n_colors, cmap=cmap, alpha=alpha)

        if colors is not False:
            self.colors = ColorFeature(parent=self, colors=colors, n_colors=n_colors, alpha=alpha)

        # different from visible, toggles the Graphic presence in the Scene
        # useful for bbox calculations to ignore these Graphics
        self.present = PresentFeature(parent=self)

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
    def interact_features(self) -> Tuple[str]:
        """The features for this ``Graphic`` that support interaction."""
        return self._valid_features

    @property
    def visible(self) -> bool:
        return self.world_object.visible

    @visible.setter
    def visible(self, v):
        """Toggle the visibility of this Graphic"""
        self.world_object.visible = v

    @property
    def children(self) -> pygfx.WorldObject:
        return self.world_object.children

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
<<<<<<< HEAD
=======

    def event_handler(self, event):
        if event.type in self.registered_callbacks.keys():
            for target_info in self.registered_callbacks[event.type]:
                target_info.target._set_feature(name=target_info.feature, new_data=target_info.new_data,
                                                indices=target_info.indices)

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

<<<<<<< HEAD
    @abstractmethod
    def event_handler(self, event):
        pass

<<<<<<< HEAD
>>>>>>> 2c00596 (beginning base logic for interactivity impl)
=======
=======
>>>>>>> 71eb48f (small changes and reorg)
@dataclass
class EventData:
    """Class for keeping track of the info necessary for interactivity after event occurs."""
    def __init__(self, target: Graphic, feature: str, new_data: Any, indices: Any):
        self.target = target
        self.feature = feature
        self.new_data = new_data
<<<<<<< HEAD
>>>>>>> 95e77a1 (reorg)
=======
        self.indices = indices
>>>>>>> 71eb48f (small changes and reorg)
