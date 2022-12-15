import numpy as np
import pygfx
from typing import *

from ._base import Graphic

class LineGraphic(Graphic):
    def __init__(self, data: np.ndarray, zlevel: float = None, size: float = 2.0, colors: np.ndarray = None, cmap: str = None, *args, **kwargs):
        super(LineGraphic, self).__init__(data, colors=colors, cmap=cmap, *args, **kwargs)

        self.zlevel = zlevel

        self.fix_data()

        if size < 1.1:
            material = pygfx.LineThinMaterial
        else:
            material = pygfx.LineMaterial

        self.data = np.ascontiguousarray(self.data)

        self.world_object: pygfx.Line = pygfx.Line(
            geometry=pygfx.Geometry(positions=self.data, colors=self.colors),
            material=material(thickness=size, vertex_colors=True)
        )

        self.events = {}

    def fix_data(self):
        # TODO: data should probably be a property of any Graphic?? Or use set_data() and get_data()
        if self.data.ndim == 1:
            self.data = np.dstack([np.arange(self.data.size), self.data])[0]

        if self.data.shape[1] != 3:
            if self.data.shape[1] != 2:
                raise ValueError("Must pass 1D, 2D or 3D data")
            # make it 2D with zlevel
            if self.zlevel is None:
                self.zlevel = 0

            # zeros
            zs = np.full(self.data.shape[0], fill_value=self.zlevel, dtype=np.float32)

            self.data = np.dstack([self.data[:, 0], self.data[:, 1], zs])[0]

    def update_data(self, data: np.ndarray):
        self.data = data.astype(np.float32)
        self.fix_data()

        self.world_object.geometry.positions.data[:] = self.data
        self.world_object.geometry.positions.update_range()

    def update_colors(self, colors: np.ndarray):
        super(LineGraphic, self)._set_colors(colors=colors, colors_length=self.data.shape[0], cmap=None, alpha=None)

        self.world_object.geometry.colors.data[:] = self.colors
        self.world_object.geometry.colors.update_range()

    @property
    def indices(self) -> Any:
        return self.indices

    @property
    def features(self) -> List[str]:
        return self.features

    def _set_feature(self, name: str, new_data: Any, indices: Any):
        if name == "color":
            self.update_colors(new_data)
        elif name == "data":
            self.update_data(new_data)
        else:
            raise ValueError("name arg is not a valid feature")

    def link(self, event: str, target: Graphic, feature: str, new_data: Any, indices_mapper: callable = None):
        valid_events = ["click"]
        if event in valid_events:
            self.world_object.add_event_handler(self.event_handler, event)
        else:
            raise ValueError("event not possible")

        if event in self.events.keys():
            self.events[event].append((target, feature, new_data))
        else:
            self.events[event] = list()
            self.events[event].append((target, feature, new_data))

    def event_handler(self, event):
        if event.type in self.events.keys():
            for target_info in self.events[event.type]:
                target_info[0]._set_feature(name=target_info[1], new_data=target_info[2], indices=None)
