from abc import ABC, abstractmethod
import numpy as np
import pygfx
from typing import *
from .utils import get_cmap_texture, get_colors, map_labels_to_colors


class Graphic(ABC):
    def __init__(self, data, colors: np.ndarray = None, cmap: str = None, alpha: float = 1.0):
        self.data = data.astype(np.float32)

        if colors is None and cmap is None:  # just white
            self.colors = np.vstack([[1., 1., 1., 1.]] * data.shape[0])

        elif (colors is None) and (cmap is not None):
            self.colors = get_colors(n_colors=data.shape[0], cmap=cmap, alpha=alpha)

        elif (colors is not None) and (cmap is None):
            # assume it's already an RGBA array
            if colors.ndim == 2 and colors.shape[1] == 4 and colors.shape[0] == data.shape[0]:
                self.colors = colors

            else:
                raise ValueError(f"Colors array must have ndim == 2 and shape of [<n_datapoints>, 4]")

        elif (colors is not None) and (cmap is not None):
            if colors.ndim == 1 and np.issubdtype(colors.dtype, np.integer):
                # assume it's a mapping of colors
                self.colors = np.array(map_labels_to_colors(colors, cmap, alpha=alpha))

        else:
            raise ValueError("Unknown color format")

    def update_data(self, data: Any):
        pass


class Image(Graphic):
    def __init__(self, data: np.ndarray, vmin: int, vmax: int, cmap: str = 'plasma', *args, **kwargs):
        super().__init__(data, cmap=cmap, *args, **kwargs)

        self.world_object: pygfx.Image = pygfx.Image(
            pygfx.Geometry(grid=pygfx.Texture(self.data, dim=2)),
            pygfx.ImageBasicMaterial(clim=(vmin, vmax), map=get_cmap_texture(cmap))
        )

    @property
    def clim(self) -> Tuple[float, float]:
        return self.world_object.material.clim

    @clim.setter
    def clim(self, levels: Tuple[float, float]):
        self.world_object.material.clim = levels

    def update_data(self, data: np.ndarray):
        self.world_object.geometry.grid.data[:] = data
        self.world_object.geometry.grid.update_range((0, 0, 0), self.world_object.geometry.grid.size)

    def update_cmap(self, cmap: str, alpha: float = 1.0):
        self.world_object.material.map = get_cmap_texture(name=cmap)


class Scatter(Graphic):
    def __init__(self, data: np.ndarray, size: int = 1, colors: np.ndarray = None, cmap: str = None, *args, **kwargs):
        super(Scatter, self).__init__(data, colors=colors, cmap=cmap, *args, **kwargs)

        self.world_object: pygfx.Group = pygfx.Group()
        self.points_objects: List[pygfx.Points] = list()

        for color in np.unique(self.colors, axis=0):
            positions = self._process_positions(
                self.data[np.all(self.colors == color, axis=1)]
            )

            points = pygfx.Points(
                pygfx.Geometry(positions=positions),
                pygfx.PointsMaterial(size=10, color=color)
            )

            self.world_object.add(points)
            self.points_objects.append(points)

    def _process_positions(self, positions: np.ndarray):
        if positions.ndim == 1:
            positions = np.array([positions])

        return positions

    def update_data(self, data: np.ndarray):
        positions = self._process_positions(data).astype(np.float32)

        self.points_objects[0].geometry.positions.data[:] = positions
        self.points_objects[0].geometry.positions.update_range(positions.shape[0])



class Line(Graphic):
    def __init__(self, data: np.ndarray, size: float = 2.0, colors: np.ndarray = None, cmap: str = None, *args, **kwargs):
        super(Line, self).__init__(data, colors=colors, cmap=cmap, *args, **kwargs)

        if size < 1.1:
            material = pygfx.LineThinMaterial
        else:
            material = pygfx.LineMaterial

        self.data = np.ascontiguousarray(self.data)

        self.world_object: pygfx.Line = pygfx.Line(
            geometry=pygfx.Geometry(positions=self.data, colors=self.colors),
            material=material(thickness=size, vertex_colors=True)
        )

    def update_data(self, data: Any):
        pass
