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
--------------(x0, -y0) --------------- (x1, -y0) --------
------------------------|||||||||||||||-------------------
------------------------|||||||||||||||-------------------
------------------------|||||||||||||||-------------------
------------------------|||rectangle|||-------------------
------------------------|||||||||||||||-------------------
------------------------|||||||||||||||-------------------
------------------------|||||||||||||||-------------------
--------------(x0, -y1) --------------- (x1, -y1)---------
----------------------------------------------------------
------------------------------------------- (canvas_width, canvas_height)

"""


class MeshMasks:
    """Used set the x1, x1, y0, y1 positions of the mesh"""
    x0 = np.array([
        [False, False, False],
        [True, False, False],
        [False, False, False],
        [True, False, False],
    ])

    x1 = np.array([
        [True, False, False],
        [False, False, False],
        [True, False, False],
        [False, False, False],
    ])

    y0 = np.array([
        [False, True, False],
        [False, True, False],
        [False, False, False],
        [False, False, False],
    ])

    y1 = np.array([
        [False, False, False],
        [False, False, False],
        [False, True, False],
        [False, True, False],
    ])


masks = MeshMasks


class SubplotFrame:
    def __init__(self, figure, bbox: np.ndarray = None, ranges: np.ndarray = None):
        self.figure = figure
        self._canvas_rect = figure.get_pygfx_render_area()
        figure.canvas.add_event_handler(self._canvas_resized, "resize")

        bbox = self._get_bbox_screen_coords(bbox)

        x0, y0, w, h = bbox
        self._bbox_screen = np.array(bbox, dtype=np.int64)

        geometry = pygfx.plane_geometry(1, 1)
        material = pygfx.MeshBasicMaterial()
        self._plane = pygfx.Mesh(geometry, material)

        self._resize_handler = pygfx.Points(
            pygfx.Geometry(positions=[[x0, -y0, 0]]),
            pygfx.PointsMarkerMaterial(marker="square", size=4, size_space="screen")
        )

        self.rect = bbox

        self._world_object = pygfx.Group()
        self._world_object.add(self._plane, self._resize_handler)

    def _get_bbox_screen_coords(self, bbox) -> np.ndarray[int]:
        for val, name in zip(bbox, ["x-position", "y-position", "width", "height"]):
            if val < 0:
                raise ValueError(f"Invalid bbox value < 0 for: {name}")

        bbox = np.asarray(bbox)

        _, _, cw, ch = self._canvas_rect
        mult = np.array([cw, ch, cw, ch])

        if (bbox < 1).all():  # fractional bbox
            # check that widths, heights are valid:
            if bbox[0] + bbox[2] > 1:
                raise ValueError("invalid fractional value: x + width > 1")
            if bbox[1] + bbox[3] > 1:
                raise ValueError("invalid fractional value: y + height > 1")

            self._bbox_frac = bbox.copy()
            bbox = self._bbox_frac * mult

        elif (bbox > 1).all():  # bbox in already in screen coords coordinates
            # check that widths, heights are valid
            if bbox[0] + bbox[2] > cw:
                raise ValueError("invalid value: x + width > 1")
            if bbox[1] + bbox[3] > ch:
                raise ValueError("invalid value: y + height > 1")

            self._bbox_frac = bbox / mult

        return bbox.astype(np.int64)

    @property
    def x(self) -> tuple[np.int64, np.int64]:
        return self.rect[0], self.rect[0] + self.rect[2]

    @property
    def y(self) -> tuple[np.int64, np.int64]:
        return self.rect[1], self.rect[1] + self.rect[3]

    @property
    def x_frac(self):
        pass

    @property
    def y_frac(self):
        pass

    @property
    def rect(self) -> np.ndarray[int]:
        return self._bbox_screen

    @rect.setter
    def rect(self, bbox: np.ndarray):
        bbox = self._get_bbox_screen_coords(bbox)
        self._set_plane(bbox)

    def _set_plane(self, bbox: np.ndarray):
        """bbox is in screen coordinates, not fractional"""

        x0, y0, w, h = bbox

        x1 = x0 + w
        y1 = y0 + h

        self._plane.geometry.positions.data[masks.x0] = x0
        self._plane.geometry.positions.data[masks.x1] = x1
        self._plane.geometry.positions.data[masks.y0] = -y0  # negative because UnderlayCamera y is inverted
        self._plane.geometry.positions.data[masks.y1] = -y1

        self._plane.geometry.positions.update_full()

        self._resize_handler.geometry.positions.data[0] = [x1, -y1, 0]
        self._resize_handler.geometry.positions.update_full()

        self._bbox_screen[:] = bbox

    @property
    def plane(self) -> pygfx.Mesh:
        return self._plane

    def _canvas_resized(self, *ev):
        # render area, to account for any edge windows that might be present
        # remember this frame also encapsulates the imgui toolbar which is
        # part of the subplot so we do not subtract the toolbar height!
        self._canvas_rect = self.figure.get_pygfx_render_area()

        # set rect using existing fractional bbox
        self.rect = self._bbox_frac

    def __repr__(self):
        s = f"{self._bbox_frac}\n{self.rect}"

        return s


class FlexLayoutManager:
    def __init__(self, figure, *frames: SubplotFrame):
        self.figure = figure
        self.figure.renderer.add_event_handler(self._figure_resized, "resize")

        # for subplot in

    def _subplot_changed(self):
        """
        Check that this subplot x_range, y_range does not overlap with any other

        Check that this x_min > all other x_
        """

    def _figure_resized(self, ev):
        w, h = ev["width"], ev["height"]



































