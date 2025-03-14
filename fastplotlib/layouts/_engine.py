from functools import partial

import numpy as np
import pygfx

from ._subplot import Subplot
from ._rect import RectManager


class UnderlayCamera(pygfx.Camera):
    """
    Same as pygfx.ScreenCoordsCamera but y-axis is inverted.

    So top left corner is (0, 0). This is easier to manage because we
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


class BaseLayout:
    def __init__(
        self,
        renderer: pygfx.WgpuRenderer,
        subplots: np.ndarray[Subplot],
        canvas_rect: tuple[float, float],
        moveable: bool,
        resizeable: bool,
    ):
        """
        Base layout engine, subclass to create a usable layout engine.
        """
        self._renderer = renderer
        self._subplots: np.ndarray[Subplot] = subplots.ravel()
        self._canvas_rect = canvas_rect

        self._last_pointer_pos: np.ndarray[np.float64, np.float64] = np.array(
            [np.nan, np.nan]
        )

        # the current user action, move or resize
        self._active_action: str | None = None
        # subplot that is currently in action, i.e. currently being moved or resized
        self._active_subplot: Subplot | None = None
        # subplot that is in focus, i.e. being hovered by the pointer
        self._subplot_focus: Subplot | None = None

        for subplot in self._subplots:
            # highlight plane when pointer enters it
            subplot.frame.plane.add_event_handler(
                partial(self._highlight_plane, subplot), "pointer_enter"
            )

            if resizeable:
                # highlight/unhighlight resize handler when pointer enters/leaves
                subplot.frame.resize_handle.add_event_handler(
                    partial(self._highlight_resize_handler, subplot), "pointer_enter"
                )
                subplot.frame.resize_handle.add_event_handler(
                    partial(self._unhighlight_resize_handler, subplot), "pointer_leave"
                )

    def _inside_render_rect(self, subplot: Subplot, pos: tuple[int, int]) -> bool:
        """whether the pos is within the render area, used for filtering out pointer events"""
        rect = subplot.frame.get_render_rect()

        x0, y0 = rect[:2]

        x1 = x0 + rect[2]
        y1 = y0 + rect[3]

        if (x0 < pos[0] < x1) and (y0 < pos[1] < y1):
            return True

        return False

    def canvas_resized(self, canvas_rect: tuple):
        """
        called by figure when canvas is resized

        Parameters
        ----------
        canvas_rect: (x, y, w, h)
            the rect that pygfx can render to, excludes any areas used by imgui.

        """

        self._canvas_rect = canvas_rect
        for subplot in self._subplots:
            subplot.frame.canvas_resized(canvas_rect)

    def _highlight_resize_handler(self, subplot: Subplot, ev):
        if self._active_action == "resize":
            return

        ev.target.material.color = subplot.frame.resize_handle_color.highlight

    def _unhighlight_resize_handler(self, subplot: Subplot, ev):
        if self._active_action == "resize":
            return

        ev.target.material.color = subplot.frame.resize_handle_color.idle

    def _highlight_plane(self, subplot: Subplot, ev):
        if self._active_action is not None:
            return

        # reset color of previous focus
        if self._subplot_focus is not None:
            self._subplot_focus.frame.plane.material.color = (
                subplot.frame.plane_color.idle
            )

        self._subplot_focus = subplot
        ev.target.material.color = subplot.frame.plane_color.highlight

    def __len__(self):
        return len(self._subplots)


class WindowLayout(BaseLayout):
    def __init__(
        self,
        renderer,
        subplots: np.ndarray[Subplot],
        canvas_rect: tuple,
        moveable=True,
        resizeable=True,
    ):
        """
        Flexible layout engine that allows freely moving and resizing subplots.
        Subplots are not allowed to overlap.

        We use a screenspace camera to perform an underlay render pass to draw the
        subplot frames, there is no depth rendering so we do not allow overlaps.

        """

        super().__init__(renderer, subplots, canvas_rect, moveable, resizeable)

        self._last_pointer_pos: np.ndarray[np.float64, np.float64] = np.array(
            [np.nan, np.nan]
        )

        for subplot in self._subplots:
            if moveable:
                # start a move action
                subplot.frame.plane.add_event_handler(
                    partial(self._action_start, subplot, "move"), "pointer_down"
                )
                # start a resize action
                subplot.frame.resize_handle.add_event_handler(
                    partial(self._action_start, subplot, "resize"), "pointer_down"
                )

        if moveable or resizeable:
            # when pointer moves, do an iteration of move or resize action
            self._renderer.add_event_handler(self._action_iter, "pointer_move")

            # end the action when pointer button goes up
            self._renderer.add_event_handler(self._action_end, "pointer_up")

    def _new_extent_from_delta(self, delta: tuple[int, int]) -> np.ndarray:
        delta_x, delta_y = delta
        if self._active_action == "resize":
            # subtract only from x1, y1
            new_extent = self._active_subplot.frame.extent - np.asarray(
                [0, delta_x, 0, delta_y]
            )
        else:
            # moving
            new_extent = self._active_subplot.frame.extent - np.asarray(
                [delta_x, delta_x, delta_y, delta_y]
            )

        x0, x1, y0, y1 = new_extent
        w = x1 - x0
        h = y1 - y0

        # make sure width and height are valid
        # min width, height is 50px
        if w <= 50:  # width > 0
            new_extent[:2] = self._active_subplot.frame.extent[:2]

        if h <= 50:  # height > 0
            new_extent[2:] = self._active_subplot.frame.extent[2:]

        # ignore movement if this would cause an overlap
        for subplot in self._subplots:
            if subplot is self._active_subplot:
                continue

            if subplot.frame.rect_manager.overlaps(new_extent):
                # we have an overlap, need to ignore one or more deltas
                # ignore x
                if not subplot.frame.rect_manager.is_left_of(
                    x0
                ) or not subplot.frame.rect_manager.is_right_of(x1):
                    new_extent[:2] = self._active_subplot.frame.extent[:2]

                # ignore y
                if not subplot.frame.rect_manager.is_above(
                    y0
                ) or not subplot.frame.rect_manager.is_below(y1):
                    new_extent[2:] = self._active_subplot.frame.extent[2:]

        # make sure all vals are non-negative
        if (new_extent[:2] < 0).any():
            # ignore delta_x
            new_extent[:2] = self._active_subplot.frame.extent[:2]

        if (new_extent[2:] < 0).any():
            # ignore delta_y
            new_extent[2:] = self._active_subplot.frame.extent[2:]

        # canvas extent
        cx0, cy0, cw, ch = self._canvas_rect

        # check if new x-range is beyond canvas x-max
        if (new_extent[:2] > cx0 + cw).any():
            new_extent[:2] = self._active_subplot.frame.extent[:2]

        # check if new y-range is beyond canvas y-max
        if (new_extent[2:] > cy0 + ch).any():
            new_extent[2:] = self._active_subplot.frame.extent[2:]

        return new_extent

    def _action_start(self, subplot: Subplot, action: str, ev):
        if self._inside_render_rect(subplot, pos=(ev.x, ev.y)):
            return

        if ev.button == 1:  # left mouse button
            self._active_action = action
            if action == "resize":
                subplot.frame.resize_handle.material.color = (
                    subplot.frame.resize_handle_color.action
                )
            elif action == "move":
                subplot.frame.plane.material.color = subplot.frame.plane_color.action
            else:
                raise ValueError

            self._active_subplot = subplot
            self._last_pointer_pos[:] = ev.x, ev.y

    def _action_iter(self, ev):
        if self._active_action is None:
            return

        delta_x, delta_y = self._last_pointer_pos - (ev.x, ev.y)
        new_extent = self._new_extent_from_delta((delta_x, delta_y))
        self._active_subplot.frame.extent = new_extent
        self._last_pointer_pos[:] = ev.x, ev.y

    def _action_end(self, ev):
        self._active_action = None
        if self._active_subplot is not None:
            self._active_subplot.frame.resize_handle.material.color = (
                self._active_subplot.frame.resize_handle_color.idle
            )
            self._active_subplot.frame.plane.material.color = (
                self._active_subplot.frame.plane_color.idle
            )
        self._active_subplot = None

        self._last_pointer_pos[:] = np.nan

    def set_rect(self, subplot: Subplot, rect: tuple | list | np.ndarray):
        """
        Set the rect of a Subplot

        Parameters
        ----------
        subplot: Subplot
            the subplot to set the rect of

        rect: (x, y, w, h)
            as absolute pixels or fractional.
            If width & height <= 1 the rect is assumed to be fractional.
            Conversely, if width & height > 1 the rect is assumed to be in absolute pixels.
            width & height must be > 0. Negative values are not allowed.

        """

        new_rect = RectManager(*rect, self._canvas_rect)
        extent = new_rect.extent
        # check for overlaps
        for s in self._subplots:
            if s is subplot:
                continue

            if s.frame.rect_manager.overlaps(extent):
                raise ValueError(f"Given rect: {rect} overlaps with another subplot.")

    def set_extent(self, subplot: Subplot, extent: tuple | list | np.ndarray):
        """
        Set the extent of a Subplot

        Parameters
        ----------
        subplot: Subplot
            the subplot to set the extent of

        extent: (xmin, xmax, ymin, ymax)
            as absolute pixels or fractional.
            If xmax & ymax <= 1 the extent is assumed to be fractional.
            Conversely, if xmax & ymax > 1 the extent is assumed to be in absolute pixels.
            Negative values are not allowed. xmax - xmin & ymax - ymin must be > 0.

        """

        new_rect = RectManager.from_extent(extent, self._canvas_rect)
        extent = new_rect.extent
        # check for overlaps
        for s in self._subplots:
            if s is subplot:
                continue

            if s.frame.rect_manager.overlaps(extent):
                raise ValueError(
                    f"Given extent: {extent} overlaps with another subplot."
                )


class GridLayout(WindowLayout):
    def __init__(
        self,
        renderer,
        subplots: np.ndarray[Subplot],
        canvas_rect: tuple[float, float, float, float],
        shape: tuple[int, int],
    ):
        """
        Grid layout engine that auto-sets Frame and Subplot rects such that they maintain
        a fixed grid layout. Does not allow freely moving or resizing subplots.

        """

        super().__init__(
            renderer, subplots, canvas_rect, moveable=False, resizeable=False
        )

        # {Subplot: (row_ix, col_ix)}, dict mapping subplots to their row and col index in the grid layout
        self._subplot_grid_position: dict[Subplot, tuple[int, int]]
        self._shape = shape

    @property
    def shape(self) -> tuple[int, int]:
        return self._shape

    def set_rect(self, subplot, rect: np.ndarray | list | tuple):
        raise NotImplementedError(
            "set_rect() not implemented for GridLayout which is an auto layout manager"
        )

    def set_extent(self, subplot, extent: np.ndarray | list | tuple):
        raise NotImplementedError(
            "set_extent() not implemented for GridLayout which is an auto layout manager"
        )

    def add_row(self):
        raise NotImplementedError("Not yet implemented")

    def add_column(self):
        raise NotImplementedError("Not yet implemented")

    def remove_row(self):
        raise NotImplementedError("Not yet implemented")

    def remove_column(self):
        raise NotImplementedError("Not yet implemented")

    def add_subplot(self):
        raise NotImplementedError(
            "Not implemented for GridLayout which is an auto layout manager"
        )

    def remove_subplot(self, subplot):
        raise NotImplementedError(
            "Not implemented for GridLayout which is an auto layout manager"
        )
