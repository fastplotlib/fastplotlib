from typing import Literal, Union

import numpy as np

import pygfx
from rendercanvas import BaseRenderCanvas

from ..graphics import TextGraphic
from ._utils import create_camera, create_controller
from ._plot_area import PlotArea
from ._frame import Frame
from ..graphics._axes import Axes


class Subplot(PlotArea):
    def __init__(
        self,
        parent: Union["Figure"],
        camera: Literal["2d", "3d"] | pygfx.PerspectiveCamera,
        controller: pygfx.Controller | str,
        canvas: BaseRenderCanvas | pygfx.Texture,
        rect: np.ndarray = None,
        extent: np.ndarray = None,
        resizeable: bool = True,
        renderer: pygfx.WgpuRenderer = None,
        name: str = None,
    ):
        """
        Subplot class.

        .. important::
            ``Subplot`` is not meant to be constructed directly, it only exists as part of a ``Figure``

        Parameters
        ----------
        parent: 'Figure' | None
            parent Figure instance

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

        camera = create_camera(camera)

        controller = create_controller(controller_type=controller, camera=camera)

        self._docks = dict()

        if "Imgui" in parent.__class__.__name__:
            toolbar_visible = True
        else:
            toolbar_visible = False

        super().__init__(
            parent=parent,
            camera=camera,
            controller=controller,
            scene=pygfx.Scene(),
            canvas=canvas,
            renderer=renderer,
            name=name,
        )

        for pos in ["left", "top", "right", "bottom"]:
            dv = Dock(self, size=0)
            dv.name = pos
            self.docks[pos] = dv
            self.children.append(dv)

        self._axes = Axes(self)
        self.scene.add(self.axes.world_object)

        self._frame = Frame(
            viewport=self.viewport,
            rect=rect,
            extent=extent,
            resizeable=resizeable,
            title=name,
            docks=self.docks,
            toolbar_visible=toolbar_visible,
            canvas_rect=parent.get_pygfx_render_area(),
        )

    @property
    def axes(self) -> Axes:
        """Axes object"""
        return self._axes

    @property
    def name(self) -> str:
        """Subplot name"""
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
        return self.frame.toolbar_visible

    @toolbar.setter
    def toolbar(self, visible: bool):
        self.frame.toolbar_visible = visible
        self.frame.reset_viewport()

    def _render(self):
        self.axes.update_using_camera()
        super()._render()

    @property
    def title(self) -> TextGraphic:
        """subplot title"""
        return self._frame.title_graphic

    @title.setter
    def title(self, text: str):
        text = str(text)
        self.title.text = text

    @property
    def frame(self) -> Frame:
        """Frame that the subplot lives in"""
        return self._frame


class Dock(PlotArea):
    def __init__(
        self,
        parent: Subplot,
        size: int,
    ):
        self._size = size

        super().__init__(
            parent=parent,
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
        self.get_figure()._fpl_reset_layout()

    def _render(self):
        if self.size == 0:
            return

        super()._render()
