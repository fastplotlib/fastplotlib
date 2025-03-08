from typing import Literal, Union

import numpy as np

import pygfx
from rendercanvas import BaseRenderCanvas

from ._rect import RectManager
from ..graphics import TextGraphic
from ._utils import create_camera, create_controller, IMGUI, IMGUI_TOOLBAR_HEIGHT
from ._plot_area import PlotArea
from ._graphic_methods_mixin import GraphicMethodsMixin
from ..graphics._axes import Axes


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

    x0 = np.array(
        [
            [False, False, False],
            [True, False, False],
            [False, False, False],
            [True, False, False],
        ]
    )

    x1 = np.array(
        [
            [True, False, False],
            [False, False, False],
            [True, False, False],
            [False, False, False],
        ]
    )

    y0 = np.array(
        [
            [False, True, False],
            [False, True, False],
            [False, False, False],
            [False, False, False],
        ]
    )

    y1 = np.array(
        [
            [False, False, False],
            [False, False, False],
            [False, True, False],
            [False, True, False],
        ]
    )


masks = MeshMasks


class Subplot(PlotArea, GraphicMethodsMixin):
    def __init__(
        self,
        parent: Union["Figure"],
        camera: Literal["2d", "3d"] | pygfx.PerspectiveCamera,
        controller: pygfx.Controller,
        canvas: BaseRenderCanvas | pygfx.Texture,
        rect: np.ndarray = None,
        extent: np.ndarray = None,
        renderer: pygfx.WgpuRenderer = None,
        name: str = None,
    ):
        """
        General plot object is found within a ``Figure``. Each ``Figure`` instance will have [n rows, n columns]
        of subplots.

        .. important::
            ``Subplot`` is not meant to be constructed directly, it only exists as part of a ``Figure``

        Parameters
        ----------
        parent: 'Figure' | None
            parent Figure instance

        position: (int, int), optional
            corresponds to the [row, column] position of the subplot within a ``Figure``

        camera: str or pygfx.PerspectiveCamera, default '2d'
            indicates the FOV for the camera, '2d' sets ``fov = 0``, '3d' sets ``fov = 50``.
            ``fov`` can be changed at any time.

        controller: str or pygfx.Controller, optional
            | if ``None``, uses a PanZoomController for "2d" camera or FlyController for "3d" camera.
            | if ``str``, must be one of: `"panzoom", "fly", "trackball", or "orbit"`.
            | also accepts a pygfx.Controller instance

        canvas: BaseRenderCanvas, or a pygfx.Texture
            Provides surface on which a scene will be rendered.

        renderer: WgpuRenderer
            object used to render scenes using wgpu

        name: str, optional
            name of the subplot, will appear as ``TextGraphic`` above the subplot

        """

        super(GraphicMethodsMixin, self).__init__()

        camera = create_camera(camera)

        controller = create_controller(controller_type=controller, camera=camera)

        self._docks = dict()

        if IMGUI:
            self._toolbar = True
        else:
            self._toolbar = False

        super(Subplot, self).__init__(
            parent=parent,
            camera=camera,
            controller=controller,
            scene=pygfx.Scene(),
            canvas=canvas,
            renderer=renderer,
            name=name,
        )

        for pos in ["left", "top", "right", "bottom"]:
            dv = Dock(self, pos, size=0)
            dv.name = pos
            self.docks[pos] = dv
            self.children.append(dv)

        self._axes = Axes(self)
        self.scene.add(self.axes.world_object)

        if rect is not None:
            self._rect = RectManager(*rect, self.get_figure().get_pygfx_render_area())
        elif extent is not None:
            self._rect = RectManager.from_extent(
                extent, self.get_figure().get_pygfx_render_area()
            )
        else:
            raise ValueError("Must provide `rect` or `extent`")

        if name is None:
            title_text = ""
        else:
            title_text = name
        self._title_graphic = TextGraphic(title_text, font_size=16, face_color="white")
        # self._title_graphic.world_object.material.weight_offset = 50

        # init mesh of size 1 to graphically represent rect
        geometry = pygfx.plane_geometry(1, 1)
        material = pygfx.MeshBasicMaterial(color=(0.1, 0.1, 0.1), pick_write=True)
        self._plane = pygfx.Mesh(geometry, material)

        # otherwise text isn't visible
        self._plane.world.z = 0.5

        # create resize handler at point (x1, y1)
        x1, y1 = self.extent[[1, 3]]
        self._resize_handle = pygfx.Points(
            pygfx.Geometry(positions=[[x1, -y1, 0]]),  # y is inverted in UnderlayCamera
            pygfx.PointsMarkerMaterial(
                color=(0.5, 0.5, 0.5), marker="square", size=8, size_space="screen", pick_write=True
            ),
        )

        self._reset_plane()
        self._reset_viewport_rect()

        self._world_object = pygfx.Group()
        self._world_object.add(
            self._plane, self._resize_handle, self._title_graphic.world_object
        )

    @property
    def axes(self) -> Axes:
        return self._axes

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, name: str):
        if name is None:
            self._name = None
            return

        for subplot in self.get_figure(self):
            if (subplot is self) or (subplot is None):
                continue
            if subplot.name == name:
                raise ValueError("subplot names must be unique")

        self._name = name

    @property
    def docks(self) -> dict:
        """
        The docks of this plot area. Each ``dock`` is basically just a PlotArea too.

        The docks are: ["left", "top", "right", "bottom"]

        Returns
        -------
        Dict[str, Dock]
            {dock_name: Dock}

        """
        return self._docks

    @property
    def toolbar(self) -> bool:
        """show/hide toolbar"""
        return self._toolbar

    @toolbar.setter
    def toolbar(self, visible: bool):
        self._toolbar = bool(visible)
        self.get_figure()._set_viewport_rects(self)

    def _render(self):
        self.axes.update_using_camera()
        super()._render()

    @property
    def title(self) -> TextGraphic:
        """subplot title"""
        return self._title_graphic

    @title.setter
    def title(self, text: str):
        text = str(text)
        self._title_graphic.text = text

    @property
    def extent(self) -> np.ndarray:
        """extent, (xmin, xmax, ymin, ymax)"""
        # not actually stored, computed when needed
        return self._rect.extent

    @extent.setter
    def extent(self, extent):
        self._rect.extent = extent
        self._reset_plane()
        self._reset_viewport_rect()

    @property
    def rect(self) -> np.ndarray[int]:
        """rect in absolute screen space, (x, y, w, h)"""
        return self._rect.rect

    @rect.setter
    def rect(self, rect: np.ndarray):
        self._rect.rect = rect
        self._reset_plane()
        self._reset_viewport_rect()

    def _reset_viewport_rect(self):
        # get rect of the render area
        x, y, w, h = self._fpl_get_render_rect()

        s_left = self.docks["left"].size
        s_top = self.docks["top"].size
        s_right = self.docks["right"].size
        s_bottom = self.docks["bottom"].size

        # top and bottom have same width
        # subtract left and right dock sizes
        w_top_bottom = w - s_left - s_right
        # top and bottom have same x pos
        x_top_bottom = x + s_left

        # set dock rects
        self.docks["left"].viewport.rect = x, y, s_left, h
        self.docks["top"].viewport.rect = x_top_bottom, y, w_top_bottom, s_top
        self.docks["bottom"].viewport.rect = x_top_bottom, y + h - s_bottom, w_top_bottom, s_bottom
        self.docks["right"].viewport.rect = x + w - s_right, y, s_right, h

        # calc subplot rect by adjusting for dock sizes
        x += s_left
        y += s_top
        w -= s_left + s_right
        h -= s_top + s_bottom

        # set subplot rect
        self.viewport.rect = x, y, w, h

    def _fpl_get_render_rect(self) -> tuple[float, float, float, float]:
        """
        Get the actual render area of the subplot, including the docks.

        Excludes area taken by the subplot title and toolbar. Also adds a small amount of spacing around the subplot.
        """
        x, y, w, h = self.rect

        x += 1  # add 1 so a 1 pixel edge is visible
        w -= 2  # subtract 2, so we get a 1 pixel edge on both sides

        y = y + 4 + self.title.font_size + 4  # add 4 pixels above and below title for better spacing

        if self.toolbar:
            toolbar_space = IMGUI_TOOLBAR_HEIGHT
        else:
            toolbar_space = 0

        # adjust for spacing and 4 pixels for more spacing
        h = h - 4 - self.title.font_size - toolbar_space - 4 - 4

        return x, y, w, h

    def _reset_plane(self):
        """reset the plane mesh using the current rect state"""

        x0, x1, y0, y1 = self._rect.extent
        w = self._rect.w

        self._plane.geometry.positions.data[masks.x0] = x0
        self._plane.geometry.positions.data[masks.x1] = x1
        self._plane.geometry.positions.data[masks.y0] = (
            -y0
        )  # negative y because UnderlayCamera y is inverted
        self._plane.geometry.positions.data[masks.y1] = -y1

        self._plane.geometry.positions.update_full()

        # note the negative y because UnderlayCamera y is inverted
        self._resize_handle.geometry.positions.data[0] = [x1, -y1, 0]
        self._resize_handle.geometry.positions.update_full()

        # set subplot title position
        x = x0 + (w / 2)
        y = y0 + (self.title.font_size / 2)
        self.title.world_object.world.x = x
        self.title.world_object.world.y = -y - 4  # add 4 pixels for spacing

    @property
    def _fpl_plane(self) -> pygfx.Mesh:
        """the plane mesh"""
        return self._plane

    @property
    def _fpl_resize_handle(self) -> pygfx.Points:
        """resize handler point"""
        return self._resize_handle

    def _fpl_canvas_resized(self, canvas_rect):
        """called by layout is resized"""
        self._rect._fpl_canvas_resized(canvas_rect)
        self._reset_plane()
        self._reset_viewport_rect()

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
        return not any(
            [
                self.is_above(y0),
                self.is_below(y1),
                self.is_left_of(x0),
                self.is_right_of(x1),
            ]
        )


class Dock(PlotArea):
    _valid_positions = ["right", "left", "top", "bottom"]

    def __init__(
        self,
        parent: Subplot,
        position: str,
        size: int,
    ):
        if position not in self._valid_positions:
            raise ValueError(
                f"the `position` of an AnchoredViewport must be one of: {self._valid_positions}"
            )

        self._size = size
        self._position = position

        super().__init__(
            parent=parent,
            camera=pygfx.OrthographicCamera(),
            controller=pygfx.PanZoomController(),
            scene=pygfx.Scene(),
            canvas=parent.canvas,
            renderer=parent.renderer,
        )

    @property
    def position(self) -> str:
        return self._position

    @property
    def size(self) -> int:
        """Get or set the size of this dock"""
        return self._size

    @size.setter
    def size(self, s: int):
        self._size = s
        self.parent._reset_viewport_rect()

    def _render(self):
        if self.size == 0:
            return

        super()._render()
