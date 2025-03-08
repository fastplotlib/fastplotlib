from functools import partial

import numpy as np
import pygfx

from ._subplot import Subplot


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


class BaseLayout:
    def __init__(
        self,
        renderer: pygfx.WgpuRenderer,
        subplots: np.ndarray[Subplot],
        canvas_rect: tuple,
    ):
        self._renderer = renderer
        self._subplots: np.ndarray[Subplot] = subplots.ravel()
        self._canvas_rect = canvas_rect

    def _inside_render_rect(self, subplot: Subplot, pos: tuple[int, int]) -> bool:
        """whether the pos is within the render area, used for filtering out pointer events"""
        rect = subplot._fpl_get_render_rect()

        x0, y0 = rect[:2]

        x1 = x0 + rect[2]
        y1 = y0 + rect[3]

        if (x0 < pos[0] < x1) and (y0 < pos[1] < y1):
            return True

        return False

    def add_subplot(self):
        raise NotImplementedError

    def remove_subplot(self, subplot):
        raise NotImplementedError

    def set_rect(self, subplot, rect: np.ndarray | list | tuple):
        raise NotImplementedError

    def set_extent(self, subplot, extent: np.ndarray | list | tuple):
        raise NotImplementedError

    def _fpl_canvas_resized(self, canvas_rect: tuple):
        self._canvas_rect = canvas_rect
        for subplot in self._subplots:
            subplot._fpl_canvas_resized(canvas_rect)

    def __len__(self):
        return len(self._subplots)


class FlexLayout(BaseLayout):
    def __init__(
        self,
        renderer,
        subplots: list[Subplot],
        canvas_rect: tuple,
        moveable=True,
        resizeable=True,
    ):
        super().__init__(renderer, subplots, canvas_rect)

        self._last_pointer_pos: np.ndarray[np.float64, np.float64] = np.array(
            [np.nan, np.nan]
        )

        self._active_action: str | None = None
        self._active_subplot: Subplot | None = None
        self._subplot_focus: Subplot | None = None

        for subplot in self._subplots:
            # highlight plane when pointer enters it
            subplot._fpl_plane.add_event_handler(
                partial(self._highlight_plane, subplot), "pointer_enter"
            )

            if moveable:
                # start a move action
                subplot._fpl_plane.add_event_handler(
                    partial(self._action_start, subplot, "move"), "pointer_down"
                )
                # start a resize action
                subplot._fpl_resize_handle.add_event_handler(
                    partial(self._action_start, subplot, "resize"), "pointer_down"
                )

            if resizeable:
                # highlight/unhighlight resize handler when pointer enters/leaves
                subplot._fpl_resize_handle.add_event_handler(
                    partial(self._highlight_resize_handler, subplot), "pointer_enter"
                )
                subplot._fpl_resize_handle.add_event_handler(
                    partial(self._unhighlight_resize_handler, subplot), "pointer_leave"
                )

        if moveable or resizeable:
            # when pointer moves, do an iteration of move or resize action
            self._renderer.add_event_handler(self._action_iter, "pointer_move")

            # end the action when pointer button goes up
            self._renderer.add_event_handler(self._action_end, "pointer_up")

    def remove_subplot(self, subplot):
        if subplot is self._active_subplot:
            self._active_subplot = None
        if subplot is self._subplot_focus:
            self._subplot_focus = None

    def _new_extent_from_delta(self, delta: tuple[int, int]) -> np.ndarray:
        delta_x, delta_y = delta
        if self._active_action == "resize":
            # subtract only from x1, y1
            new_extent = self._active_subplot.extent - np.asarray(
                [0, delta_x, 0, delta_y]
            )
        else:
            # moving
            new_extent = self._active_subplot.extent - np.asarray(
                [delta_x, delta_x, delta_y, delta_y]
            )

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
        cx0, cy0, cw, ch = self._canvas_rect

        # check if new x-range is beyond canvas x-max
        if (new_extent[:2] > cx0 + cw).any():
            new_extent[:2] = self._active_subplot.extent[:2]

        # check if new y-range is beyond canvas y-max
        if (new_extent[2:] > cy0 + ch).any():
            new_extent[2:] = self._active_subplot.extent[2:]

        return new_extent

    def _action_start(self, subplot: Subplot, action: str, ev):
        if self._inside_render_rect(subplot, pos=(ev.x, ev.y)):
            return

        if ev.button == 1:
            self._active_action = action
            if action == "resize":
                subplot._fpl_resize_handle.material.color = (
                    subplot.resize_handle_color.action
                )
            elif action == "move":
                subplot._fpl_plane.material.color = subplot.plane_color.action
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
        if self._active_subplot is not None:
            self._active_subplot._fpl_resize_handle.material.color = (
                self._active_subplot.resize_handle_color.idle
            )
            self._active_subplot._fpl_plane.material.color = (
                self._active_subplot.plane_color.idle
            )
        self._active_subplot = None

        self._last_pointer_pos[:] = np.nan

    def _highlight_resize_handler(self, subplot: Subplot, ev):
        if self._active_action == "resize":
            return

        ev.target.material.color = subplot.resize_handle_color.highlight

    def _unhighlight_resize_handler(self, subplot: Subplot, ev):
        if self._active_action == "resize":
            return

        ev.target.material.color = subplot.resize_handle_color.idle

    def _highlight_plane(self, subplot: Subplot, ev):
        if self._active_action is not None:
            return

        # reset color of previous focus
        if self._subplot_focus is not None:
            self._subplot_focus._fpl_plane.material.color = subplot.plane_color.idle

        self._subplot_focus = subplot
        ev.target.material.color = subplot.plane_color.highlight


class GridLayout(FlexLayout):
    def __init__(
        self,
        renderer,
        subplots: list[Subplot],
        canvas_rect: tuple[float, float, float, float],
        shape: tuple[int, int],
    ):
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
        pass
        # new_shape = (self.shape[0] + 1, self.shape[1])
        # extents = get_extents_from_grid(new_shape)
        # for subplot, extent in zip(self._subplots, extents):
        #     subplot.extent = extent

    def add_column(self):
        pass

    def remove_row(self):
        pass

    def remove_column(self):
        pass

    def add_subplot(self):
        raise NotImplementedError

    def remove_subplot(self, subplot):
        raise NotImplementedError
