from typing import Literal, Union

import pygfx

from rendercanvas import BaseRenderCanvas

from ..graphics import TextGraphic
from ._utils import create_camera, create_controller
from ._plot_area import PlotArea
from ._graphic_methods_mixin import GraphicMethodsMixin
from ..graphics._axes import Axes


class Subplot(PlotArea, GraphicMethodsMixin):
    def __init__(
        self,
        parent: Union["Figure"],
        camera: Literal["2d", "3d"] | pygfx.PerspectiveCamera,
        controller: pygfx.Controller,
        canvas: BaseRenderCanvas | pygfx.Texture,
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

        self._title_graphic: TextGraphic = None

        self._toolbar = True

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
        self.get_figure()._fpl_set_subplot_viewport_rect(self)

    def _render(self):
        self.axes.update_using_camera()
        super()._render()

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
        if self.position == "top":
            # TODO: treat title dock separately, do not allow user to change viewport stuff
            return

        self.get_figure(self.parent)._fpl_set_subplot_viewport_rect(self.parent)
        self.get_figure(self.parent)._fpl_set_subplot_dock_viewport_rect(self.parent, self._position)

    def _render(self):
        if self.size == 0:
            return

        super()._render()
