from functools import partial

import numpy as np
import pygfx

from ..graphics import TextGraphic


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

Note how the y values of the plane mesh are negative, this is because of the UnderlayCamera.
We always just keep the positive y value, and make it negative only when setting the plane mesh.

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


class RectManager:
    def __init__(self, x: float, y: float, w: float, h: float, canvas_rect: tuple):
        # initialize rect state arrays
        # used to store internal state of the rect in both fractional screen space and absolute screen space
        # the purpose of storing the fractional rect is that it remains constant when the canvas resizes
        self._rect_frac = np.zeros(4, dtype=np.float64)
        self._rect_screen_space = np.zeros(4, dtype=np.float64)
        self._canvas_rect = np.asarray(canvas_rect)

        self._set((x, y, w, h))

    def _set(self, rect):
        """
        Using the passed rect which is either absolute screen space or fractional,
        set the internal fractional and absolute screen space rects
        """
        rect = np.asarray(rect)
        for val, name in zip(rect, ["x-position", "y-position", "width", "height"]):
            if val < 0:
                raise ValueError(f"Invalid rect value < 0 for: {name}")

        if (rect[2:] <= 1).all():  # fractional bbox
            self._set_from_fract(rect)

        elif (rect[2:] > 1).all():  # bbox in already in screen coords coordinates
            self._set_from_screen_space(rect)

        else:
            raise ValueError(f"Invalid rect: {rect}")

    def _set_from_fract(self, rect):
        """set rect from fractional representation"""
        _, _, cw, ch = self._canvas_rect
        mult = np.array([cw, ch, cw, ch])

        # check that widths, heights are valid:
        if rect[0] + rect[2] > 1:
            raise ValueError("invalid fractional value: x + width > 1")
        if rect[1] + rect[3] > 1:
            raise ValueError("invalid fractional value: y + height > 1")

        # assign values, don't just change the reference
        self._rect_frac[:] = rect
        self._rect_screen_space[:] = self._rect_frac * mult

    def _set_from_screen_space(self, rect):
        """set rect from screen space representation"""
        _, _, cw, ch = self._canvas_rect
        mult = np.array([cw, ch, cw, ch])
        # for screen coords allow (x, y) = 1 or 0, but w, h must be > 1
        # check that widths, heights are valid
        if rect[0] + rect[2] > cw:
            raise ValueError(f"invalid value: x + width > 1: {rect}")
        if rect[1] + rect[3] > ch:
            raise ValueError(f"invalid value: y + height > 1: {rect}")

        self._rect_frac[:] = rect / mult
        self._rect_screen_space[:] = rect

    @property
    def x(self) -> np.float64:
        return self._rect_screen_space[0]

    @property
    def y(self) -> np.float64:
        return self._rect_screen_space[1]

    @property
    def w(self) -> np.float64:
        return self._rect_screen_space[2]

    @property
    def h(self) -> np.float64:
        return self._rect_screen_space[3]

    @property
    def rect(self) -> np.ndarray:
        return self._rect_screen_space

    @rect.setter
    def rect(self, rect: np.ndarray | tuple):
        self._set(rect)

    def _fpl_canvas_resized(self, canvas_rect: tuple):
        # called by subplot when canvas is resized
        self._canvas_rect[:] = canvas_rect
        # set new rect using existing rect_frac since this remains constant regardless of resize
        self._set(self._rect_frac)

    @property
    def x0(self) -> np.float64:
        return self.x

    @property
    def x1(self) -> np.float64:
        return self.x + self.w

    @property
    def y0(self) -> np.float64:
        return self.y

    @property
    def y1(self) -> np.float64:
        return self.y + self.h

    @classmethod
    def from_extent(cls, extent, canvas_rect):
        rect = cls.extent_to_rect(extent, canvas_rect)
        return cls(*rect, canvas_rect)

    @property
    def extent(self) -> np.ndarray:
        """extent, (xmin, xmax, ymin, ymax)"""
        # not actually stored, computed when needed
        return np.asarray([self.x0, self.x1, self.y0, self.y1])

    @extent.setter
    def extent(self, extent):
        """convert extent to rect"""
        valid, error = RectManager.validate_extent(extent, self._canvas_rect)
        if not valid:
            raise ValueError(error)

        rect = RectManager.extent_to_rect(extent, canvas_rect=self._canvas_rect)

        self._set(rect)

    @staticmethod
    def extent_to_rect(extent, canvas_rect):
        RectManager.validate_extent(extent, canvas_rect)
        x0, x1, y0, y1 = extent

        # width and height
        w = x1 - x0
        h = y1 - y0

        x, y, w, h = x0, y0, w, h

        return x, y, w, h

    @staticmethod
    def validate_extent(extent: np.ndarray | tuple, canvas_rect: tuple) -> tuple[bool, None | str]:
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

    def __repr__(self):
        s = f"{self._rect_frac}\n{self.rect}"

        return s


class Frame:
    def __init__(self, figure, rect: np.ndarray = None, extent: np.ndarray = None, subplot_title: str = None):
        """

        Parameters
        ----------
        figure
        rect: (x, y, w, h)
            in absolute screen space or fractional screen space, example if the canvas w, h is (100, 200)
            a fractional rect of (0.1, 0.1, 0.5, 0.5) is (10, 10, 50, 100) in absolute screen space

        extent: (xmin, xmax, ymin, ymax)
            extent of the frame in absolute screen coordinates or fractional screen coordinates
        """
        self.figure = figure
        figure.canvas.add_event_handler(self._canvas_resize_handler, "resize")

        if rect is not None:
            self._rect = RectManager(*rect, figure.get_pygfx_render_area())
        elif extent is not None:
            self._rect = RectManager.from_extent(extent, figure.get_pygfx_render_area())
        else:
            raise ValueError("Must provide `rect` or `extent`")

        if subplot_title is None:
            subplot_title = ""
        self._subplot_title = TextGraphic(subplot_title, face_color="black")

        # init mesh of size 1 to graphically represent rect
        geometry = pygfx.plane_geometry(1, 1)
        material = pygfx.MeshBasicMaterial(pick_write=True)
        self._plane = pygfx.Mesh(geometry, material)

        # otherwise text isn't visible
        self._plane.world.z = 0.5

        # create resize handler at point (x1, y1)
        x1, y1 = self.extent[[1, 3]]
        self._resize_handler = pygfx.Points(
            pygfx.Geometry(positions=[[x1, -y1, 0]]),  # y is inverted in UnderlayCamera
            pygfx.PointsMarkerMaterial(marker="square", size=12, size_space="screen", pick_write=True)
        )

        self._reset_plane()

        self._world_object = pygfx.Group()
        self._world_object.add(self._plane, self._resize_handler, self._subplot_title.world_object)

    @property
    def extent(self) -> np.ndarray:
        """extent, (xmin, xmax, ymin, ymax)"""
        # not actually stored, computed when needed
        return self._rect.extent

    @extent.setter
    def extent(self, extent):
        self._rect.extent = extent
        self._reset_plane()

    @property
    def rect(self) -> np.ndarray[int]:
        """rect in absolute screen space, (x, y, w, h)"""
        return self._rect.rect

    @rect.setter
    def rect(self, rect: np.ndarray):
        self._rect.rect = rect
        self._reset_plane()

    def _reset_plane(self):
        """reset the plane mesh using the current rect state"""

        x0, x1, y0, y1 = self._rect.extent
        w = self._rect.w

        self._plane.geometry.positions.data[masks.x0] = x0
        self._plane.geometry.positions.data[masks.x1] = x1
        self._plane.geometry.positions.data[masks.y0] = -y0  # negative y because UnderlayCamera y is inverted
        self._plane.geometry.positions.data[masks.y1] = -y1

        self._plane.geometry.positions.update_full()

        # note the negative y because UnderlayCamera y is inverted
        self._resize_handler.geometry.positions.data[0] = [x1, -y1, 0]
        self._resize_handler.geometry.positions.update_full()

        # set subplot title position
        x = x0 + (w / 2)
        y = y0 + (self.subplot_title.font_size / 2)
        self.subplot_title.world_object.world.x = x
        self.subplot_title.world_object.world.y = -y

    @property
    def _fpl_plane(self) -> pygfx.Mesh:
        """the plane mesh"""
        return self._plane

    @property
    def _fpl_resize_handler(self) -> pygfx.Points:
        """resize handler point"""
        return self._resize_handler

    def _canvas_resize_handler(self, *ev):
        """triggered when canvas is resized"""
        # render area, to account for any edge windows that might be present
        # remember this frame also encapsulates the imgui toolbar which is
        # part of the subplot so we do not subtract the toolbar height!
        canvas_rect = self.figure.get_pygfx_render_area()

        self._rect._fpl_canvas_resized(canvas_rect)
        self._reset_plane()

    @property
    def subplot_title(self) -> TextGraphic:
        return self._subplot_title

    def is_above(self, y0) -> bool:
        # our bottom < other top
        return self._rect.y1 < y0

    def is_below(self, y1) -> bool:
        # our top > other bottom
        return self._rect.y0 > y1

    def is_left_of(self, x0) -> bool:
        # our right_edge < other left_edge
        # self.x1 < other.x0
        return self._rect.x1 < x0

    def is_right_of(self, x1) -> bool:
        # self.x0 > other.x1
        return self._rect.x0 > x1

    def overlaps(self, extent: np.ndarray) -> bool:
        """returns whether this subplot overlaps with the given extent"""
        x0, x1, y0, y1 = extent
        return not any([self.is_above(y0), self.is_below(y1), self.is_left_of(x0), self.is_right_of(x1)])


class BaseLayout:
    def __init__(self, renderer: pygfx.WgpuRenderer, frames: tuple[Frame]):
        self._renderer = renderer
        self._frames = frames

    def set_rect(self, subplot, rect: np.ndarray | list | tuple):
        raise NotImplementedError

    def set_extent(self, subplot, extent: np.ndarray | list | tuple):
        raise NotImplementedError

    def _canvas_resize_handler(self, ev):
        pass

    @property
    def spacing(self) -> int:
        pass


class GridLayout(BaseLayout):
    def __init__(self, figure, frames: tuple[Frame]):
        super().__init__(figure, frames)

    def set_rect(self, subplot, rect: np.ndarray | list | tuple):
        raise NotImplementedError("set_rect() not implemented for GridLayout which is an auto layout manager")

    def set_extent(self, subplot, extent: np.ndarray | list | tuple):
        raise NotImplementedError("set_extent() not implemented for GridLayout which is an auto layout manager")

    def _fpl_set_subplot_viewport_rect(self):
        pass

    def _fpl_set_subplot_dock_viewport_rect(self):
        pass


class FlexLayout(BaseLayout):
    def __init__(self, renderer, get_canvas_rect: callable, frames: tuple[Frame]):
        super().__init__(renderer, frames)

        self._last_pointer_pos: np.ndarray[np.float64, np.float64] = np.array([np.nan, np.nan])

        self._get_canvas_rect = get_canvas_rect

        self._active_action: str | None = None
        self._active_frame: Frame | None = None

        for frame in self._frames:
            frame._fpl_plane.add_event_handler(partial(self._action_start, frame, "move"), "pointer_down")
            frame._fpl_resize_handler.add_event_handler(
                partial(self._action_start, frame, "resize"), "pointer_down"
            )
            frame._fpl_resize_handler.add_event_handler(self._highlight_resize_handler, "pointer_enter")
            frame._fpl_resize_handler.add_event_handler(self._unhighlight_resize_handler, "pointer_leave")

        self._renderer.add_event_handler(self._action_iter, "pointer_move")
        self._renderer.add_event_handler(self._action_end, "pointer_up")

    def _new_extent_from_delta(self, delta: tuple[int, int]) -> np.ndarray:
        delta_x, delta_y = delta
        if self._active_action == "resize":
            # subtract only from x1, y1
            new_extent = self._active_frame.extent - np.asarray([0, delta_x, 0, delta_y])
        else:
            # moving
            new_extent = self._active_frame.extent - np.asarray([delta_x, delta_x, delta_y, delta_y])

        x0, x1, y0, y1 = new_extent
        w = x1 - x0
        h = y1 - y0

        # make sure width and height are valid
        # min width, height is 50px
        if w <= 50:  # width > 0
            new_extent[:2] = self._active_frame.extent[:2]

        if h <= 50:  # height > 0
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
        cx0, cy0, cw, ch = self._get_canvas_rect()

        # check if new x-range is beyond canvas x-max
        if (new_extent[:2] > cx0 + cw).any():
            new_extent[:2] = self._active_frame.extent[:2]

        # check if new y-range is beyond canvas y-max
        if (new_extent[2:] > cy0 + ch).any():
            new_extent[2:] = self._active_frame.extent[2:]

        return new_extent

    def _action_start(self, frame: Frame, action: str, ev):
        if ev.button == 1:
            self._active_action = action
            if action == "resize":
                frame._fpl_resize_handler.material.color = (1, 0, 0)
            elif action == "move":
                pass
            else:
                raise ValueError

            self._active_frame = frame
            self._last_pointer_pos[:] = ev.x, ev.y

    def _action_iter(self, ev):
        if self._active_action is None:
            return

        delta_x, delta_y = self._last_pointer_pos - (ev.x, ev.y)
        new_extent = self._new_extent_from_delta((delta_x, delta_y))
        self._active_frame.extent = new_extent
        self._last_pointer_pos[:] = ev.x, ev.y

    def _action_end(self, ev):
        self._active_action = None
        self._active_frame._fpl_resize_handler.material.color = (1, 1, 1)
        self._last_pointer_pos[:] = np.nan

    def _highlight_resize_handler(self, ev):
        if self._active_action == "resize":
            return

        ev.target.material.color = (1, 1, 0)

    def _unhighlight_resize_handler(self, ev):
        if self._active_action == "resize":
            return

        ev.target.material.color = (1, 1, 1)
