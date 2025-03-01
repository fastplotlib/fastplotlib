from functools import partial

import numpy as np
import pygfx


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
    def __init__(self, figure, rect: np.ndarray = None, extent: np.ndarray = None):
        """

        Parameters
        ----------
        figure
        rect: (x, y, w, h)
            in absolute screen space or fractional screen space, example if the canvas w, h is (100, 200)
            a fractional rect of (0.1, 0.1, 0.5, 0.5) is (10, 10, 50, 100) in absolute screen space

        extent: (xmin, xmax, ymin, ymax)
            range in absolute screen coordinates or fractional screen coordinates
        """
        self.figure = figure

        # canvas (x, y, w, h)
        self._canvas_rect = figure.get_pygfx_render_area()
        figure.canvas.add_event_handler(self._canvas_resized, "resize")

        # initialize rect state arrays
        # used to store internal state of the rect in both fractional screen space and absolute screen space
        # the purpose of storing the fractional rect is that it remains constant when the canvas resizes
        self._rect_frac = np.zeros(4, dtype=np.float64)
        self._rect_screen_space = np.zeros(4, dtype=np.float64)

        if rect is None:
            if extent is None:
                raise ValueError("Must provide rect or ranges")

            valid, error = self._validate_extent(extent)
            if not valid:
                raise ValueError(error)
            # convert ranges to rect
            rect = self._extent_to_rect(extent)

        # assign the internal state of the rect by parsing the user passed rect
        self._assign_rect(rect)

        # init mesh of size 1 to graphically represent rect
        geometry = pygfx.plane_geometry(1, 1)
        material = pygfx.MeshBasicMaterial(pick_write=True)
        self._plane = pygfx.Mesh(geometry, material)

        # create resize handler at point (x1, y1)
        x1, y1 = self.extent[[1, 3]]
        self._resize_handler = pygfx.Points(
            pygfx.Geometry(positions=[[x1, -y1, 0]]),  # y is inverted in UnderlayCamera
            pygfx.PointsMarkerMaterial(marker="square", size=4, size_space="screen", pick_write=True)
        )

        self._reset_plane()

        self._world_object = pygfx.Group()
        self._world_object.add(self._plane, self._resize_handler)

    def _extent_to_rect(self, extent) -> np.ndarray:
        """convert extent to rect"""
        x0, x1, y0, y1 = extent

        # width and height
        w = x1 - x0
        h = y1 - y0

        x, y, w, h = x0, y0, w, h

        return np.array([x, y, w, h])

    def _assign_rect(self, rect) -> np.ndarray[int]:
        """
        Using the passed rect which is either absolute screen space or fractional,
        set the internal fractional and absolute screen space rects
        """
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
                raise ValueError(f"invalid value: x + width > 1: {rect}")
            if rect[1] + rect[3] > ch:
                raise ValueError(f"invalid value: y + height > 1: {rect}")

            self._rect_frac[:] = rect / mult
            self._rect_screen_space[:] = rect

        else:
            raise ValueError(f"Invalid rect: {rect}")

    @property
    def extent(self) -> np.ndarray:
        """extent, (xmin, xmax, ymin, ymax)"""
        # not actually stored, computed when needed
        return np.asarray([self.rect[0], self.rect[0] + self.rect[2], self.rect[1], self.rect[1] + self.rect[3]])

    @extent.setter
    def extent(self, extent: np.ndarray):
        valid, error = self._validate_extent(extent)

        if not valid:
            raise ValueError(error)

        rect = self._extent_to_rect(extent)
        self.rect = rect

    def _validate_extent(self, extent: np.ndarray | tuple) -> tuple[bool, None | str]:
        x0, x1, y0, y1 = extent

        # width and height
        w = x1 - x0
        h = y1 - y0

        # make sure extent is valid
        if (np.asarray(extent) < 0).any():
            return False, f"extent ranges must be non-negative, you have passed: {extent}"

        # check if x1 - x0 <= 0
        if w <= 0:
            return False, f"extent x-range is invalid: {extent}"

        # check if y1 - y0 <= 0
        if h <= 0:
            return False, f"extent y-range is invalid: {extent}"

        # # calc canvas extent
        # cx0, cy0, cw, ch = self._canvas_rect
        # cx1 = cx0 + cw
        # cy1 = cy0 + ch
        # canvas_extent = np.asarray([cx0, cx1, cy0, cy1])

        # # check that extent is within the bounds of the canvas
        # if (x0 > canvas_extent[:2]).any() or (x1 > canvas_extent[:2]).any():  # is x0, x1 beyond canvas x-range
        #     return False, f"extent x-range is beyond the bounds of the canvas: {extent}"
        #
        # if (y0 > canvas_extent[2:]).any() or (y1 > canvas_extent[2:]).any():  # is y0, y1 beyond canvas x-range
        #     return False, f"extent y-range is beyond the bounds of the canvas: {extent}"

        return True, None

    @property
    def x_range(self) -> np.ndarray:
        return self.extent[:2]

    @property
    def y_range(self) -> np.ndarray:
        return self.extent[2:]

    @property
    def rect(self) -> np.ndarray[int]:
        """rect in absolute screen space, (x, y, w, h)"""
        return self._rect_screen_space

    @rect.setter
    def rect(self, rect: np.ndarray):
        self._assign_rect(rect)
        self._reset_plane()

    def _reset_plane(self):
        """reset the plane mesh using the current rect state"""

        x0, y0, w, h = self.rect

        x1 = x0 + w
        y1 = y0 + h

        self._plane.geometry.positions.data[masks.x0] = x0
        self._plane.geometry.positions.data[masks.x1] = x1
        self._plane.geometry.positions.data[masks.y0] = -y0  # negative y because UnderlayCamera y is inverted
        self._plane.geometry.positions.data[masks.y1] = -y1

        self._plane.geometry.positions.update_full()

        # note the negative y because UnderlayCamera y is inverted
        self._resize_handler.geometry.positions.data[0] = [x1, -y1, 0]
        self._resize_handler.geometry.positions.update_full()

    @property
    def plane(self) -> pygfx.Mesh:
        """the plane mesh"""
        return self._plane

    @property
    def resize_handler(self) -> pygfx.Points:
        """resize handler point"""
        return self._resize_handler

    def _canvas_resized(self, *ev):
        """triggered when canvas is resized"""
        # render area, to account for any edge windows that might be present
        # remember this frame also encapsulates the imgui toolbar which is
        # part of the subplot so we do not subtract the toolbar height!
        self._canvas_rect = self.figure.get_pygfx_render_area()

        # set new rect using existing rect_frac since this remains constant regardless of resize
        self.rect = self._rect_frac

    def is_above(self, y0) -> bool:
        # our bottom < other top
        return self.y_range[1] < y0

    def is_below(self, y1) -> bool:
        # our top > other bottom
        return self.y_range[0] > y1

    def is_left_of(self, x0) -> bool:
        # our right_edge < other left_edge
        # self.x1 < other.x0
        return self.x_range[1] < x0

    def is_right_of(self, x1) -> bool:
        # self.x0 > other.x1
        return self.x_range[0] > x1

    def overlaps(self, extent: np.ndarray) -> bool:
        """returns whether this subplot would overlap with the other extent"""
        x0, x1, y0, y1 = extent
        return not any([self.is_above(y0), self.is_below(y1), self.is_left_of(x0), self.is_right_of(x1)])

    def __repr__(self):
        s = f"{self._rect_frac}\n{self.rect}"

        return s


class FlexLayoutManager:
    def __init__(self, figure, frames: SubplotFrame):
        self.figure = figure
        # self.figure.renderer.add_event_handler(self._figure_resized, "resize")

        self._frames = frames

        self._last_pointer_pos: np.ndarray[np.float64, np.float64] = np.array([np.nan, np.nan])

        self._moving = False
        self._resizing = False
        self._active_frame: SubplotFrame | None = None

        for frame in self._frames:
            frame.plane.add_event_handler(partial(self._action_start, frame, "move"), "pointer_down")
            frame.resize_handler.add_event_handler(partial(self._action_start, frame, "resize"), "pointer_down")

        self.figure.renderer.add_event_handler(self._action_iter, "pointer_move")
        self.figure.renderer.add_event_handler(self._action_end, "pointer_up")

    def _subplot_changed(self):
        """
        Check that this subplot x_range, y_range does not overlap with any other

        Check that this x_min > all other x_
        """
        pass

    # def _figure_resized(self, ev):
    #     w, h = ev["width"], ev["height"]

    def _new_extent_from_delta(self, delta: tuple[int, int]) -> np.ndarray:
        delta_x, delta_y = delta
        if self._resizing:
            # subtract only from x1, y1
            new_extent = self._active_frame.extent - np.asarray([0, delta_x, 0, delta_y])
        else:
            # moving
            new_extent = self._active_frame.extent - np.asarray([delta_x, delta_x, delta_y, delta_y])

        x0, x1, y0, y1 = new_extent
        w = x1 - x0
        h = y1 - y0

        # make sure width and height are valid
        if w <= 0:  # width > 0
            new_extent[:2] = self._active_frame.extent[:2]

        if h <= 0:  # height > 0
            new_extent[2:] = self._active_frame.extent[2:]

        # ignore movement if this would cause an overlap
        for frame in self._frames:
            if frame is self._active_frame:
                continue

            if frame.overlaps(new_extent):
                # we have an overlap, need to ignore one or more deltas
                # ignore x
                if not frame.is_left_of(x0) or not frame.is_right_of(x1):
                    new_extent[:2] = self._active_frame.extent[:2]

                # ignore y
                if not frame.is_above(y0) or not frame.is_below(y1):
                    new_extent[2:] = self._active_frame.extent[2:]

        # make sure all vals are non-negative
        if (new_extent[:2] < 0).any():
            # ignore delta_x
            new_extent[:2] = self._active_frame.extent[:2]

        if (new_extent[2:] < 0).any():
            # ignore delta_y
            new_extent[2:] = self._active_frame.extent[2:]

        # canvas extent
        cx0, cy0, cw, ch = self._active_frame._canvas_rect

        # check if new x-range is beyond canvas x-max
        if (new_extent[:2] > cx0 + cw).any():
            new_extent[:2] = self._active_frame.extent[:2]

        # check if new y-range is beyond canvas y-max
        if (new_extent[2:] > cy0 + ch).any():
            new_extent[2:] = self._active_frame.extent[2:]

        return new_extent

    def _action_start(self, frame: SubplotFrame, action: str, ev):
        if ev.button == 1:
            if action == "move":
                self._moving = True
            elif action == "resize":
                self._resizing = True
                frame.resize_handler.material.color = (1, 0, 0)
            else:
                raise ValueError

            self._active_frame = frame
            self._last_pointer_pos[:] = ev.x, ev.y

    def _action_iter(self, ev):
        if not any((self._moving, self._resizing)):
            return

        delta_x, delta_y = self._last_pointer_pos - (ev.x, ev.y)
        new_extent = self._new_extent_from_delta((delta_x, delta_y))
        self._active_frame.extent = new_extent
        self._last_pointer_pos[:] = ev.x, ev.y

    def _action_end(self, ev):
        self._moving = False
        self._resizing = False
        self._active_frame.resize_handler.material.color = (0, 0, 0)
        self._last_pointer_pos[:] = np.nan
