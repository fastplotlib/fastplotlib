import numpy as np
import pygfx
from typing import *
from ..utils import get_cmap_texture, get_colors, map_labels_to_colors, quick_min_max


class _Graphic:
    def __init__(
            self,
            data,
            colors: np.ndarray = None,
            colors_length: int = None,
            cmap: str = None,
            alpha: float = 1.0
    ):
        self.data = data.astype(np.float32)
        self.colors = None

        if colors_length is None:
            colors_length = self.data.shape[0]

        if colors is not False:
            self._set_colors(colors, colors_length, cmap, alpha, )

    def _set_colors(self, colors, colors_length, cmap, alpha):
        if colors is None and cmap is None:  # just white
            self.colors = np.vstack([[1., 1., 1., 1.]] * colors_length).astype(np.float32)

        elif (colors is None) and (cmap is not None):
            self.colors = get_colors(n_colors=colors_length, cmap=cmap, alpha=alpha)

        elif (colors is not None) and (cmap is None):
            # assume it's already an RGBA array
            if colors.ndim == 2 and colors.shape[1] == 4 and colors.shape[0] == colors_length:
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


class Image(_Graphic):
    def __init__(
            self,
            data: np.ndarray,
            vmin: int = None,
            vmax: int = None,
            cmap: str = 'plasma',
            *args,
            **kwargs
    ):
        if data.ndim != 2:
            raise ValueError("`data.ndim !=2`, you must pass only a 2D array to `data`")
            
        super().__init__(data, cmap=cmap, *args, **kwargs)

        if (vmin is None) or (vmax is None):
            vmin, vmax = quick_min_max(data)

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


class Scatter(_Graphic):
    def __init__(self, data: np.ndarray, zlevel: float = None, size: int = 1, colors: np.ndarray = None, cmap: str = None, *args, **kwargs):
        super(Scatter, self).__init__(data, colors=colors, cmap=cmap, *args, **kwargs)

        if self.data.shape[1] != 3:
            if self.data.shape[1] == 2:
                # make it 2D with zlevel
                if zlevel == None:
                    zlevel = 0

                # zeros
                zs = np.full(self.data.shape[0], fill_value=zlevel, dtype=np.float32)

                self.data = np.dstack([self.data[:, 0], self.data[:, 1], zs])[0]
            if self.data.shape[1] > 3 or self.data.shape[1] < 1:
                raise ValueError("Must pass 2D or 3D data or a single point")

        self.world_object: pygfx.Group = pygfx.Group()
        self.points_objects: List[pygfx.Points] = list()

        for color in np.unique(self.colors, axis=0):
            positions = self._process_positions(
                self.data[np.all(self.colors == color, axis=1)]
            )

            points = pygfx.Points(
                pygfx.Geometry(positions=positions),
                pygfx.PointsMaterial(size=size, color=color)
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


class Line(_Graphic):
    def __init__(self, data: np.ndarray, zlevel: float = None, size: float = 2.0, colors: np.ndarray = None, cmap: str = None, *args, **kwargs):
        super(Line, self).__init__(data, colors=colors, cmap=cmap, *args, **kwargs)

        if self.data.shape[1] != 3:
            if self.data.shape[1] != 2:
                raise ValueError("Must pass 2D or 3D data")
            # make it 2D with zlevel
            if zlevel == None:
                zlevel = 0

            # zeros
            zs = np.full(self.data.shape[0], fill_value=zlevel, dtype=np.float32)

            self.data = np.dstack([self.data[:, 0], self.data[:, 1], zs])[0]

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
        self.data = data.astype(np.float32)
        self.world_object.geometry.positions.data[:] = self.data
        self.world_object.geometry.positions.update_range()


class _HistogramBin(pygfx.Mesh):
    def __int__(self, *args, **kwargs):
        super(_HistogramBin, self).__init__(*args, **kwargs)
        self.bin_center: float = None
        self.frequency: Union[int, float] = None


class Histogram(_Graphic):
    def __init__(
            self,
            data: np.ndarray = None,
            bins: Union[int, str] = 'auto',
            pre_computed: Dict[str, np.ndarray] = None,
            colors: np.ndarray = None,
            draw_scale_factor: float = 100.0,
            draw_bin_width_scale: float = 1.0
    ):

        if pre_computed is None:
            self.hist, self.bin_edges = np.histogram(data, bins)
        else:
            if not set(pre_computed.keys()) == {'hist', 'bin_edges'}:
                raise ValueError("argument to `pre_computed` must be a `dict` with keys 'hist' and 'bin_edges'")
            if not all(type(v) is np.ndarray for v in pre_computed.values()):
                raise ValueError("argument to `pre_computed` must be a `dict` where the values are numpy.ndarray")
            self.hist, self.bin_edges = pre_computed["hist"], pre_computed["bin_edges"]

        self.bin_interval = (self.bin_edges[1] - self.bin_edges[0]) / 2
        self.bin_centers = (self.bin_edges + self.bin_interval)[:-1]

        # scale between 0 - draw_scale_factor
        scaled_bin_edges = ((self.bin_edges - self.bin_edges.min()) / (np.ptp(self.bin_edges))) * draw_scale_factor

        bin_interval_scaled = scaled_bin_edges[1] / 2
        # get the centers of the bins from the edges
        x_positions_bins = (scaled_bin_edges + bin_interval_scaled)[:-1].astype(np.float32)

        n_bins = x_positions_bins.shape[0]
        bin_width = (draw_scale_factor / n_bins) * draw_bin_width_scale

        self.hist = self.hist.astype(np.float32)
        data = np.vstack([x_positions_bins, self.hist])

        super(Histogram, self).__init__(data=data, colors=colors, colors_length=n_bins)

        self.world_object: pygfx.Group = pygfx.Group()

        for x_val, y_val, bin_center in zip(x_positions_bins, self.hist, self.bin_centers):
            geometry = pygfx.plane_geometry(
                width=bin_width,
                height=y_val,
            )

            material = pygfx.MeshBasicMaterial()
            hist_bin_graphic = _HistogramBin(geometry, material)
            hist_bin_graphic.position.set(x_val, (y_val) / 2, 0)
            hist_bin_graphic.bin_center = bin_center
            hist_bin_graphic.frequency = y_val

            self.world_object.add(hist_bin_graphic)
