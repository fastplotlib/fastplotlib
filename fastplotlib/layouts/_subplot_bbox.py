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
    def __init__(self, figure, rect: np.ndarray = None, ranges: np.ndarray = None):
        """

        Parameters
        ----------
        figure
        rect: (x, y, w, h)
            in absolute screen space or fractional screen space, example if the canvas w, h is (100, 200)
            a fractional rect of (0.1, 0.1, 0.5, 0.5) is (10, 10, 50, 100) in absolute screen space

        ranges (xmin, xmax, ymin, ymax)
            in absolute screen coordinates or fractional screen coordinates
        """
        self.figure = figure
        self._canvas_rect = figure.get_pygfx_render_area()
        figure.canvas.add_event_handler(self._canvas_resized, "resize")

        self._rect_frac = np.zeros(4, dtype=np.float64)
        self._rect_screen_space = np.zeros(4, dtype=np.float64)

        if rect is None:
            if ranges is None:
                raise ValueError
            rect = self._ranges_to_rect(ranges)

        self._assign_rect(rect)

        x0, y0, w, h = self.rect

        geometry = pygfx.plane_geometry(1, 1)
        material = pygfx.MeshBasicMaterial()
        self._plane = pygfx.Mesh(geometry, material)

        self._resize_handler = pygfx.Points(
            pygfx.Geometry(positions=[[x0, -y0, 0]]),
            pygfx.PointsMarkerMaterial(marker="square", size=4, size_space="screen")
        )

        self._reset_plane()

        self._world_object = pygfx.Group()
        self._world_object.add(self._plane, self._resize_handler)

    def _ranges_to_rect(self, ranges) -> np.ndarray:
        """convert ranges to rect"""
        x0, x1, y0, y1 = ranges

        # width and height
        w = x1 - x0
        h = y1 - y0

        if x1 - x0 <= 0:
            raise ValueError
        if y1 - y0 <= 0:
            raise ValueError

        x, y, w, h = x0, y0, w, h

        return np.array([x, y, w, h])

    def _assign_rect(self, rect) -> np.ndarray[int]:
        for val, name in zip(rect, ["x-position", "y-position", "width", "height"]):
            if val < 0:
                raise ValueError(f"Invalid rect value < 0 for: {name}")

        rect = np.asarray(rect)

        _, _, cw, ch = self._canvas_rect
        mult = np.array([cw, ch, cw, ch])

        if (rect[2:] <= 1).all():  # fractional bbox
            # check that widths, heights are valid:
            if rect[0] + rect[2] > 1:
                raise ValueError("invalid fractional value: x + width > 1")
            if rect[1] + rect[3] > 1:
                raise ValueError("invalid fractional value: y + height > 1")

            # assign values, don't just change the reference
            self._rect_frac[:] = rect
            self._rect_screen_space[:] = self._rect_frac * mult

        # for screen coords allow (x, y) = 1 or 0, but w, h must be > 1
        elif (rect[2:] > 1).all():  # bbox in already in screen coords coordinates
            # check that widths, heights are valid
            if rect[0] + rect[2] > cw:
                raise ValueError("invalid value: x + width > 1")
            if rect[1] + rect[3] > ch:
                raise ValueError("invalid value: y + height > 1")

            self._rect_frac[:] = rect / mult
            self._rect_screen_space[:] = rect

        else:
            raise ValueError(f"Invalid rect: {rect}")

    @property
    def ranges(self) -> tuple[np.int64, np.int64, np.int64, np.int64]:
        return self.rect[0], self.rect[0] + self.rect[2], self.rect[1], self.rect[1] + self.rect[3]

    @ranges.setter
    def ranges(self, ranges: np.ndarray):
        rect = self._ranges_to_rect(ranges)
        self.rect = rect

    @property
    def rect(self) -> np.ndarray[int]:
        """rect in absolute screen space"""
        return self._rect_screen_space

    @rect.setter
    def rect(self, rect: np.ndarray):
        self._assign_rect(rect)
        self._reset_plane()

    def _reset_plane(self):
        """bbox is in screen coordinates, not fractional"""

        x0, y0, w, h = self.rect

        x1 = x0 + w
        y1 = y0 + h

        self._plane.geometry.positions.data[masks.x0] = x0
        self._plane.geometry.positions.data[masks.x1] = x1
        self._plane.geometry.positions.data[masks.y0] = -y0  # negative because UnderlayCamera y is inverted
        self._plane.geometry.positions.data[masks.y1] = -y1

        self._plane.geometry.positions.update_full()

        self._resize_handler.geometry.positions.data[0] = [x1, -y1, 0]
        self._resize_handler.geometry.positions.update_full()

    @property
    def plane(self) -> pygfx.Mesh:
        return self._plane

    def _canvas_resized(self, *ev):
        # render area, to account for any edge windows that might be present
        # remember this frame also encapsulates the imgui toolbar which is
        # part of the subplot so we do not subtract the toolbar height!
        self._canvas_rect = self.figure.get_pygfx_render_area()

        # set rect using existing rect_frac since this remains constant regardless of resize
        self.rect = self._rect_frac

    def __repr__(self):
        s = f"{self._rect_frac}\n{self.rect}"

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




































