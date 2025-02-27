import fastplotlib as fpl
import pygfx
import numpy as np


class UnderlayCamera(pygfx.Camera):
    """
    Same as pygfx.ScreenCoordsCamera but y-axis is inverted.

    So top right is (0, 0). This is easier to manage because we
    often resize using the bottom right corner.
    """

    def _update_projection_matrix(self):
        width, height = self._view_size
        sx, sy, sz = 2 / width, 2 / height, 1
        dx, dy, dz = -1, 1, 0  # pygfx is -1, -1, 0
        m = sx, 0, 0, dx, 0, sy, 0, dy, 0, 0, sz, dz, 0, 0, 0, 1
        proj_matrix = np.array(m, dtype=float).reshape(4, 4)
        proj_matrix.flags.writeable = False
        return proj_matrix


"""
Each subplot is defined by a 2D plane mesh, a rectangle.
The rectangles are viewed using the UnderlayCamera  where (0, 0) is the top left corner.
We can control the bbox of this rectangle by changing the x and y boundaries of the rectangle.

Note how the y values are negative.

Illustration:

(0, 0) ---------------------------------------------------
----------------------------------------------------------
----------------------------------------------------------
--------------(x1, -y1) --------------- (x2, -y1) --------
------------------------|||||||||||||||-------------------
------------------------|||||||||||||||-------------------
------------------------|||||||||||||||-------------------
------------------------|||rectangle|||-------------------
------------------------|||||||||||||||-------------------
------------------------|||||||||||||||-------------------
------------------------|||||||||||||||-------------------
--------------(x1, -y2) --------------- (x2, -y2)---------
----------------------------------------------------------
------------------------------------------- (canvas_width, canvas_height)

"""


class MeshMasks:
    """Used set the x1, x2, y1, y2 positions of the mesh"""
    x1 = np.array([
        [False, False, False],
        [True, False, False],
        [False, False, False],
        [True, False, False],
    ])

    x2 = np.array([
        [True, False, False],
        [False, False, False],
        [True, False, False],
        [False, False, False],
    ])

    y1 = np.array([
        [False, True, False],
        [False, True, False],
        [False, False, False],
        [False, False, False],
    ])

    y2 = np.array([
        [False, False, False],
        [False, False, False],
        [False, True, False],
        [False, True, False],
    ])


masks = MeshMasks


class SubplotFrame:
    def __init__(self, bbox: tuple):
        x1, y1, w, h = bbox
        geometry = pygfx.plane_geometry(1, 1)
        material = pygfx.MeshBasicMaterial()
        self._plane = pygfx.Mesh(geometry, material)

        self._resize_handler = pygfx.Points(
            pygfx.Geometry(positions=[[x1, -y1, 0]]),
            pygfx.PointsMarkerMaterial(marker="square", size=4, size_space="screen")
        )

        self.rect = bbox

        self._world_object = pygfx.Group()
        self._world_object.add(self._plane, self._resize_handler)

    def validate_bbox(self, bbox):
        for val, name in zip(bbox, ["x-position", "y-position", "width", "height"]):
            if val < 0:
                raise ValueError(f"Invalid bbox value < 0 for: {name}")

    @property
    def rect(self) -> tuple[float, float, float, float]:
        x = self.plane.geometry.positions.data[masks.x1][0]
        y = self.plane.geometry.positions.data[masks.y1][0]

        w = self.plane.geometry.positions.data[masks.x2][0] - x
        h = self.plane.geometry.positions.data[masks.y2][0] - y

        return x, -y, w, -h  # remember y is inverted

    @rect.setter
    def rect(self, bbox: tuple[float, float, float, float]):
        self.validate_bbox(bbox)
        x1, y1, w, h = bbox

        x2 = x1 + w
        y2 = y1 + h

        self._plane.geometry.positions.data[masks.x1] = x1
        self._plane.geometry.positions.data[masks.x2] = x2
        self._plane.geometry.positions.data[masks.y1] = -y1  # negative because UnderlayCamera y is inverted
        self._plane.geometry.positions.data[masks.y2] = -y2

        self._plane.geometry.positions.update_full()

        self._resize_handler.geometry.positions.data[0] = [x2, -y2, 0]
        self._resize_handler.geometry.positions.update_full()

    @property
    def plane(self) -> pygfx.Mesh:
        return self._plane






































