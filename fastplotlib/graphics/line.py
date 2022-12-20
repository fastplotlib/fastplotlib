from typing import *
import numpy as np
import pygfx
from typing import *

from ._base import Graphic, CallbackData, Interaction

<<<<<<< HEAD
class LineGraphic(Graphic):
    def __init__(
            self,
            data: Any,
            z_position: float = 0.0,
            size: float = 2.0,
            colors: Union[str, np.ndarray, Iterable] = "w",
            cmap: str = None,
            *args,
            **kwargs
    ):
        """
        Create a line Graphic, 2d or 3d

        Parameters
        ----------
        data: array-like
            Line data to plot, 2D must be of shape [n_points, 2], 3D must be of shape [n_points, 3]

        z_position: float, optional
            z-axis position for placing the graphic

        size: float, optional
            thickness of the line

        colors: str, array, or iterable
            specify colors as a single human readable string, a single RGBA array,
            or an iterable of strings or RGBA arrays

        cmap: str, optional
            apply a colormap to the line instead of assigning colors manually

        args
            passed to Graphic
        kwargs
            passed to Graphic
        """
=======
class LineGraphic(Graphic, Interaction):
    def __init__(self, data: np.ndarray, z_position: float = None, size: float = 2.0, colors: np.ndarray = None, cmap: str = None, *args, **kwargs):
        super(LineGraphic, self).__init__(data, colors=colors, cmap=cmap, *args, **kwargs)

<<<<<<< HEAD
        self.zlevel = zlevel
>>>>>>> e203cff (updates to line, works w previous example)
=======
        self.z_position = z_position
>>>>>>> 70a3be6 (fixing z_position)

        super(LineGraphic, self).__init__(data, colors=colors, cmap=cmap, *args, **kwargs)

        if size < 1.1:
            material = pygfx.LineThinMaterial
        else:
            material = pygfx.LineMaterial

        # self.data = np.ascontiguousarray(self.data)

        self._world_object: pygfx.Line = pygfx.Line(
            # self.data.feature_data because data is a Buffer
            geometry=pygfx.Geometry(positions=self.data.feature_data, colors=self.colors.feature_data),
            material=material(thickness=size, vertex_colors=True)
        )

<<<<<<< HEAD
<<<<<<< HEAD
<<<<<<< HEAD
        self.world_object.position.z = z_position
=======
        self.events = {}
=======
        self.registered_callbacks = {}
>>>>>>> 95e77a1 (reorg)

=======
>>>>>>> 71eb48f (small changes and reorg)
    def fix_data(self):
        # TODO: data should probably be a property of any Graphic?? Or use set_data() and get_data()
        if self.data.ndim == 1:
            self.data = np.dstack([np.arange(self.data.size), self.data])[0]

        if self.data.shape[1] != 3:
            if self.data.shape[1] != 2:
                raise ValueError("Must pass 1D, 2D or 3D data")
            # make it 2D with zlevel
            if self.z_position is None:
                self.z_position = 0

            # zeros
            zs = np.full(self.data.shape[0], fill_value=self.z_position, dtype=np.float32)

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
    def features(self) -> List[str]:
        return ["colors", "data"]

    def _set_feature(self, feature: str, new_data: Any, indices: Any = None):
        if feature in self.features:
            update_func = getattr(self, f"update_{feature}")
            update_func(new_data)
        else:
            raise ValueError("name arg is not a valid feature")

<<<<<<< HEAD
<<<<<<< HEAD
<<<<<<< HEAD
    def link(self, event_type: str, target: Graphic, feature: str, new_data: Any, indices_mapper: callable = None):
        valid_events = ["click"]
        if event_type in valid_events:
            self.world_object.add_event_handler(self.event_handler, event_type)
        else:
            raise ValueError("event not possible")

        if event_type in self.registered_callbacks.keys():
            self.registered_callbacks[event_type].append(EventData(target=target, feature=feature, new_data=new_data))
        else:
<<<<<<< HEAD
            self.registered_callbacks[event] = list()
<<<<<<< HEAD
            self.registered_callbacks[event].append(EventData(target=target, feature=feature, new_data=new_data))

    def event_handler(self, event):
<<<<<<< HEAD
<<<<<<< HEAD
        for event in self.events[event]:
            event[0]._set_feature(name=event[1], new_data=event[2], indices=None)
>>>>>>> f19c9c1 (wip)
=======
        if event.type in self.events.keys():
            for target_info in self.events[event.type]:
                target_info[0]._set_feature(name=target_info[1], new_data=target_info[2], indices=None)
>>>>>>> ac6c67a (grrrrr)
=======
        if event.type in self.registered_callbacks.keys():
            for target_info in self.registered_callbacks[event.type]:
                target_info.target._set_feature(name=target_info.feature, new_data=target_info.new_data, indices=None)
>>>>>>> 95e77a1 (reorg)
=======
            self.registered_callbacks[event].append(EventData(target=target, feature=feature, new_data=new_data, indices=None))
>>>>>>> 71eb48f (small changes and reorg)
=======
            self.registered_callbacks[event_type] = list()
            self.registered_callbacks[event_type].append(EventData(target=target, feature=feature, new_data=new_data))
>>>>>>> e203cff (updates to line, works w previous example)
=======
    def _reset_feature():
        pass
>>>>>>> 0f22531 (small changes)
=======
    def _reset_feature(self, feature: str, old_data: Any, indices: Any = None):
        if feature in ["colors", "data"]:
=======
    def _reset_feature(self, feature: str, old_data: Any):
        if feature in self.features:
>>>>>>> 9309b41 (ugly but functional)
            update_func = getattr(self, f"update_{feature}")
            update_func(old_data)
        else:
            raise ValueError("name arg is not a valid feature")

>>>>>>> bc688fc (implementing reset_feature)
