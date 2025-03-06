from functools import partial

import numpy as np
import pygfx

from ._subplot import Subplot

# from ..graphics import TextGraphic


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


# class Frame:
#     def __init__(self, figure, rect: np.ndarray = None, extent: np.ndarray = None, subplot_title: str = None):
#         """
#
#         Parameters
#         ----------
#         figure
#         rect: (x, y, w, h)
#             in absolute screen space or fractional screen space, example if the canvas w, h is (100, 200)
#             a fractional rect of (0.1, 0.1, 0.5, 0.5) is (10, 10, 50, 100) in absolute screen space
#
#         extent: (xmin, xmax, ymin, ymax)
#             extent of the frame in absolute screen coordinates or fractional screen coordinates
#         """
#         self.figure = figure
#         figure.canvas.add_event_handler(self._canvas_resize_handler, "resize")
#
#         if rect is not None:
#             self._rect = RectManager(*rect, figure.get_pygfx_render_area())
#         elif extent is not None:
#             self._rect = RectManager.from_extent(extent, figure.get_pygfx_render_area())
#         else:
#             raise ValueError("Must provide `rect` or `extent`")
#
#         if subplot_title is None:
#             subplot_title = ""
#         self._subplot_title = TextGraphic(subplot_title, face_color="black")
#
#         # init mesh of size 1 to graphically represent rect
#         geometry = pygfx.plane_geometry(1, 1)
#         material = pygfx.MeshBasicMaterial(pick_write=True)
#         self._plane = pygfx.Mesh(geometry, material)
#
#         # otherwise text isn't visible
#         self._plane.world.z = 0.5
#
#         # create resize handler at point (x1, y1)
#         x1, y1 = self.extent[[1, 3]]
#         self._resize_handler = pygfx.Points(
#             pygfx.Geometry(positions=[[x1, -y1, 0]]),  # y is inverted in UnderlayCamera
#             pygfx.PointsMarkerMaterial(marker="square", size=12, size_space="screen", pick_write=True)
#         )
#
#         self._reset_plane()
#
#         self._world_object = pygfx.Group()
#         self._world_object.add(self._plane, self._resize_handler, self._subplot_title.world_object)
#
#     @property
#     def extent(self) -> np.ndarray:
#         """extent, (xmin, xmax, ymin, ymax)"""
#         # not actually stored, computed when needed
#         return self._rect.extent
#
#     @extent.setter
#     def extent(self, extent):
#         self._rect.extent = extent
#         self._reset_plane()
#
#     @property
#     def rect(self) -> np.ndarray[int]:
#         """rect in absolute screen space, (x, y, w, h)"""
#         return self._rect.rect
#
#     @rect.setter
#     def rect(self, rect: np.ndarray):
#         self._rect.rect = rect
#         self._reset_plane()
#
#     def _reset_plane(self):
#         """reset the plane mesh using the current rect state"""
#
#         x0, x1, y0, y1 = self._rect.extent
#         w = self._rect.w
#
#         self._plane.geometry.positions.data[masks.x0] = x0
#         self._plane.geometry.positions.data[masks.x1] = x1
#         self._plane.geometry.positions.data[masks.y0] = -y0  # negative y because UnderlayCamera y is inverted
#         self._plane.geometry.positions.data[masks.y1] = -y1
#
#         self._plane.geometry.positions.update_full()
#
#         # note the negative y because UnderlayCamera y is inverted
#         self._resize_handler.geometry.positions.data[0] = [x1, -y1, 0]
#         self._resize_handler.geometry.positions.update_full()
#
#         # set subplot title position
#         x = x0 + (w / 2)
#         y = y0 + (self.subplot_title.font_size / 2)
#         self.subplot_title.world_object.world.x = x
#         self.subplot_title.world_object.world.y = -y
#
#     @property
#     def _fpl_plane(self) -> pygfx.Mesh:
#         """the plane mesh"""
#         return self._plane
#
#     @property
#     def _fpl_resize_handler(self) -> pygfx.Points:
#         """resize handler point"""
#         return self._resize_handler
#
#     def _canvas_resize_handler(self, *ev):
#         """triggered when canvas is resized"""
#         # render area, to account for any edge windows that might be present
#         # remember this frame also encapsulates the imgui toolbar which is
#         # part of the subplot so we do not subtract the toolbar height!
#         canvas_rect = self.figure.get_pygfx_render_area()
#
#         self._rect._fpl_canvas_resized(canvas_rect)
#         self._reset_plane()
#
#     @property
#     def subplot_title(self) -> TextGraphic:
#         return self._subplot_title
#
#     def is_above(self, y0) -> bool:
#         # our bottom < other top
#         return self._rect.y1 < y0
#
#     def is_below(self, y1) -> bool:
#         # our top > other bottom
#         return self._rect.y0 > y1
#
#     def is_left_of(self, x0) -> bool:
#         # our right_edge < other left_edge
#         # self.x1 < other.x0
#         return self._rect.x1 < x0
#
#     def is_right_of(self, x1) -> bool:
#         # self.x0 > other.x1
#         return self._rect.x0 > x1
#
#     def overlaps(self, extent: np.ndarray) -> bool:
#         """returns whether this subplot overlaps with the given extent"""
#         x0, x1, y0, y1 = extent
#         return not any([self.is_above(y0), self.is_below(y1), self.is_left_of(x0), self.is_right_of(x1)])


class BaseLayout:
    def __init__(self, renderer: pygfx.WgpuRenderer, subplots: list[Subplot]):
        self._renderer = renderer
        self._subplots = subplots

    def set_rect(self, subplot, rect: np.ndarray | list | tuple):
        raise NotImplementedError

    def set_extent(self, subplot, extent: np.ndarray | list | tuple):
        raise NotImplementedError

    def _canvas_resize_handler(self, ev):
        pass

    @property
    def spacing(self) -> int:
        pass

    def __len__(self):
        return len(self._subplots)


class FlexLayout(BaseLayout):
    def __init__(self, renderer, get_canvas_rect: callable, subplots: list[Subplot]):
        super().__init__(renderer, subplots)

        self._last_pointer_pos: np.ndarray[np.float64, np.float64] = np.array([np.nan, np.nan])

        self._get_canvas_rect = get_canvas_rect

        self._active_action: str | None = None
        self._active_subplot: Subplot | None = None

        for frame in self._subplots:
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
            new_extent = self._active_subplot.extent - np.asarray([0, delta_x, 0, delta_y])
        else:
            # moving
            new_extent = self._active_subplot.extent - np.asarray([delta_x, delta_x, delta_y, delta_y])

        x0, x1, y0, y1 = new_extent
        w = x1 - x0
        h = y1 - y0

        # make sure width and height are valid
        # min width, height is 50px
        if w <= 50:  # width > 0
            new_extent[:2] = self._active_subplot.extent[:2]

        if h <= 50:  # height > 0
            new_extent[2:] = self._active_subplot.extent[2:]

        # ignore movement if this would cause an overlap
        for frame in self._subplots:
            if frame is self._active_subplot:
                continue

            if frame.overlaps(new_extent):
                # we have an overlap, need to ignore one or more deltas
                # ignore x
                if not frame.is_left_of(x0) or not frame.is_right_of(x1):
                    new_extent[:2] = self._active_subplot.extent[:2]

                # ignore y
                if not frame.is_above(y0) or not frame.is_below(y1):
                    new_extent[2:] = self._active_subplot.extent[2:]

        # make sure all vals are non-negative
        if (new_extent[:2] < 0).any():
            # ignore delta_x
            new_extent[:2] = self._active_subplot.extent[:2]

        if (new_extent[2:] < 0).any():
            # ignore delta_y
            new_extent[2:] = self._active_subplot.extent[2:]

        # canvas extent
        cx0, cy0, cw, ch = self._get_canvas_rect()

        # check if new x-range is beyond canvas x-max
        if (new_extent[:2] > cx0 + cw).any():
            new_extent[:2] = self._active_subplot.extent[:2]

        # check if new y-range is beyond canvas y-max
        if (new_extent[2:] > cy0 + ch).any():
            new_extent[2:] = self._active_subplot.extent[2:]

        return new_extent

    def _action_start(self, subplot: Subplot, action: str, ev):
        if ev.button == 1:
            self._active_action = action
            if action == "resize":
                subplot._fpl_resize_handler.material.color = (1, 0, 0)
            elif action == "move":
                pass
            else:
                raise ValueError

            self._active_subplot = subplot
            self._last_pointer_pos[:] = ev.x, ev.y

    def _action_iter(self, ev):
        if self._active_action is None:
            return

        delta_x, delta_y = self._last_pointer_pos - (ev.x, ev.y)
        new_extent = self._new_extent_from_delta((delta_x, delta_y))
        self._active_subplot.extent = new_extent
        self._last_pointer_pos[:] = ev.x, ev.y

    def _action_end(self, ev):
        self._active_action = None
        self._active_subplot._fpl_resize_handler.material.color = (1, 1, 1)
        self._last_pointer_pos[:] = np.nan

    def _highlight_resize_handler(self, ev):
        if self._active_action == "resize":
            return

        ev.target.material.color = (1, 1, 0)

    def _unhighlight_resize_handler(self, ev):
        if self._active_action == "resize":
            return

        ev.target.material.color = (1, 1, 1)

    def add_subplot(self):
        pass

    def remove_subplot(self):
        pass


class GridLayout(FlexLayout):
    def __init__(self, renderer, get_canvas_rect: callable, subplots: list[Subplot]):
        super().__init__(renderer, subplots)

        # {Subplot: (row_ix, col_ix)}, dict mapping subplots to their row and col index in the grid layout
        self._subplot_grid_position: dict[Subplot, tuple[int, int]]

    @property
    def shape(self) -> tuple[int, int]:
        pass

    def set_rect(self, subplot, rect: np.ndarray | list | tuple):
        raise NotImplementedError("set_rect() not implemented for GridLayout which is an auto layout manager")

    def set_extent(self, subplot, extent: np.ndarray | list | tuple):
        raise NotImplementedError("set_extent() not implemented for GridLayout which is an auto layout manager")

    def _fpl_set_subplot_viewport_rect(self):
        pass

    def _fpl_set_subplot_dock_viewport_rect(self):
        pass

    def add_row(self):
        pass

    def add_column(self):
        pass

    def remove_row(self):
        pass

    def remove_column(self):
        pass
