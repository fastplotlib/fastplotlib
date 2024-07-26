from typing import Literal, Union

import numpy as np

import pygfx

from wgpu.gui import WgpuCanvasBase

from ..graphics import TextGraphic
from ._utils import make_canvas_and_renderer, create_camera, create_controller
from ._plot_area import PlotArea
from ._graphic_methods_mixin import GraphicMethodsMixin
from ..graphics._axes import Axes


class Subplot(PlotArea, GraphicMethodsMixin):
    def __init__(
        self,
        parent: Union["Figure", None] = None,
        position: tuple[int, int] = None,
        parent_dims: tuple[int, int] = None,
        camera: Literal["2d", "3d"] | pygfx.PerspectiveCamera = "2d",
        controller: (
            Literal["panzoom", "fly", "trackball", "orbit"] | pygfx.Controller
        ) = None,
        canvas: (
            Literal["glfw", "jupyter", "qt", "wx"] | WgpuCanvasBase | pygfx.Texture
        ) = None,
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

        parent_dims: (int, int), optional
            dimensions of the parent ``Figure``

        camera: str or pygfx.PerspectiveCamera, default '2d'
            indicates the FOV for the camera, '2d' sets ``fov = 0``, '3d' sets ``fov = 50``.
            ``fov`` can be changed at any time.

        controller: str or pygfx.Controller, optional
            | if ``None``, uses a PanZoomController for "2d" camera or FlyController for "3d" camera.
            | if ``str``, must be one of: `"panzoom", "fly", "trackball", or "orbit"`.
            | also accepts a pygfx.Controller instance

        canvas: one of "jupyter", "glfw", "qt", "ex, a WgpuCanvas, or a pygfx.Texture, optional
            Provides surface on which a scene will be rendered. Can optionally provide a WgpuCanvas instance or a str
            to force the PlotArea to use a specific canvas from one of the following options: "jupyter", "glfw", "qt".
            Can also provide a pygfx Texture to render to.

        renderer: WgpuRenderer, optional
            object used to render scenes using wgpu

        name: str, optional
            name of the subplot, will appear as ``TextGraphic`` above the subplot

        """

        super(GraphicMethodsMixin, self).__init__()

        canvas, renderer = make_canvas_and_renderer(canvas, renderer)

        if position is None:
            position = (0, 0)

        if parent_dims is None:
            parent_dims = (1, 1)

        self.nrows, self.ncols = parent_dims

        camera = create_camera(camera)

        controller = create_controller(controller_type=controller, camera=camera)

        self._docks = dict()

        self.spacing = 2

        self._title_graphic: TextGraphic = None

        super(Subplot, self).__init__(
            parent=parent,
            position=position,
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

        if self.name is not None:
            self.set_title(self.name)

        self._axes = Axes(self)
        self.scene.add(self.axes.world_object)

    @property
    def axes(self) -> Axes:
        return self._axes

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, name: str):
        self._name = name
        self.set_title(name)

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

    def render(self):
        # self.axes.update_using_camera()
        super().render()

    def set_title(self, text: str):
        """Sets the plot title, stored as a ``TextGraphic`` in the "top" dock area"""
        if text is None:
            return

        text = str(text)
        if self._title_graphic is not None:
            self._title_graphic.text = text
        else:
            tg = TextGraphic(text=text, font_size=18)
            self._title_graphic = tg

            self.docks["top"].size = 35
            self.docks["top"].add_graphic(tg)

            self.center_title()

    def center_title(self):
        """Centers name of subplot."""
        if self._title_graphic is None:
            raise AttributeError("No title graphic is set")

        self._title_graphic.world_object.position = (0, 0, 0)
        self.docks["top"].center_graphic(self._title_graphic, zoom=1.5)
        self._title_graphic.world_object.position_y = -3.5

    def get_rect(self):
        """Returns the bounding box that defines the Subplot within the canvas."""
        row_ix, col_ix = self.position
        width_canvas, height_canvas = self.canvas.get_logical_size()

        x_pos = (
            (width_canvas / self.ncols) + ((col_ix - 1) * (width_canvas / self.ncols))
        ) + self.spacing
        y_pos = (
            (height_canvas / self.nrows) + ((row_ix - 1) * (height_canvas / self.nrows))
        ) + self.spacing
        width_subplot = (width_canvas / self.ncols) - self.spacing
        height_subplot = (height_canvas / self.nrows) - self.spacing

        rect = np.array([x_pos, y_pos, width_subplot, height_subplot])

        for dv in self.docks.values():
            rect = rect + dv.get_parent_rect_adjust()

        return rect


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

        super().__init__(
            parent=parent,
            position=position,
            camera=pygfx.OrthographicCamera(),
            controller=pygfx.PanZoomController(),
            scene=pygfx.Scene(),
            canvas=parent.canvas,
            renderer=parent.renderer,
        )

    @property
    def size(self) -> int:
        """Get or set the size of this dock"""
        return self._size

    @size.setter
    def size(self, s: int):
        self._size = s
        self.parent.set_viewport_rect()
        self.set_viewport_rect()

    def get_rect(self, *args):
        if self.size == 0:
            self.viewport.rect = None
            return

        row_ix_parent, col_ix_parent = self.parent.position
        width_canvas, height_canvas = self.parent.renderer.logical_size

        spacing = 2  # spacing in pixels

        if self.position == "right":
            x_pos = (
                (width_canvas / self.parent.ncols)
                + ((col_ix_parent - 1) * (width_canvas / self.parent.ncols))
                + (width_canvas / self.parent.ncols)
                - self.size
            )
            y_pos = (
                (height_canvas / self.parent.nrows)
                + ((row_ix_parent - 1) * (height_canvas / self.parent.nrows))
            ) + spacing
            width_viewport = self.size
            height_viewport = (height_canvas / self.parent.nrows) - spacing

        elif self.position == "left":
            x_pos = (width_canvas / self.parent.ncols) + (
                (col_ix_parent - 1) * (width_canvas / self.parent.ncols)
            )
            y_pos = (
                (height_canvas / self.parent.nrows)
                + ((row_ix_parent - 1) * (height_canvas / self.parent.nrows))
            ) + spacing
            width_viewport = self.size
            height_viewport = (height_canvas / self.parent.nrows) - spacing

        elif self.position == "top":
            x_pos = (
                (width_canvas / self.parent.ncols)
                + ((col_ix_parent - 1) * (width_canvas / self.parent.ncols))
                + spacing
            )
            y_pos = (
                (height_canvas / self.parent.nrows)
                + ((row_ix_parent - 1) * (height_canvas / self.parent.nrows))
            ) + spacing
            width_viewport = (width_canvas / self.parent.ncols) - spacing
            height_viewport = self.size

        elif self.position == "bottom":
            x_pos = (
                (width_canvas / self.parent.ncols)
                + ((col_ix_parent - 1) * (width_canvas / self.parent.ncols))
                + spacing
            )
            y_pos = (
                (
                    (height_canvas / self.parent.nrows)
                    + ((row_ix_parent - 1) * (height_canvas / self.parent.nrows))
                )
                + (height_canvas / self.parent.nrows)
                - self.size
            )
            width_viewport = (width_canvas / self.parent.ncols) - spacing
            height_viewport = self.size
        else:
            raise ValueError("invalid position")

        return [x_pos, y_pos, width_viewport, height_viewport]

    def get_parent_rect_adjust(self):
        if self.position == "right":
            return np.array(
                [
                    0,  # parent subplot x-position is same
                    0,
                    -self.size,  # width of parent subplot is `self.size` smaller
                    0,
                ]
            )

        elif self.position == "left":
            return np.array(
                [
                    self.size,  # `self.size` added to parent subplot x-position
                    0,
                    -self.size,  # width of parent subplot is `self.size` smaller
                    0,
                ]
            )

        elif self.position == "top":
            return np.array(
                [
                    0,
                    self.size,  # `self.size` added to parent subplot y-position
                    0,
                    -self.size,  # height of parent subplot is `self.size` smaller
                ]
            )

        elif self.position == "bottom":
            return np.array(
                [
                    0,
                    0,  # parent subplot y-position is same,
                    0,
                    -self.size,  # height of parent subplot is `self.size` smaller
                ]
            )

    def render(self):
        if self.size == 0:
            return

        super().render()
