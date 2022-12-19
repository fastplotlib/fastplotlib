import numpy as np
import pygfx
from typing import *

from ._base import Graphic, CallbackData, Interaction

class LineGraphic(Graphic, Interaction):
    def __init__(self, data: np.ndarray, z_position: float = None, size: float = 2.0, colors: np.ndarray = None, cmap: str = None, *args, **kwargs):
        super(LineGraphic, self).__init__(data, colors=colors, cmap=cmap, *args, **kwargs)

        self.z_position = z_position

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
    def indices(self) -> Any:
        return None

    @property
    def features(self) -> List[str]:
        return None

    def _set_feature(self, feature: str, new_data: Any, indices: Any = None):
        if feature in ["colors", "data"]:
            update_func = getattr(self, f"update_{feature}")
            update_func(new_data)
        else:
            raise ValueError("name arg is not a valid feature")

    def _reset_feature(self, feature: str, old_data: Any, indices: Any = None):
        if feature in ["colors", "data"]:
            update_func = getattr(self, f"update_{feature}")
            update_func(old_data)
        else:
            raise ValueError("name arg is not a valid feature")

