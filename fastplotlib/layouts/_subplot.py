from typing import Literal, Union

import numpy as np

import pygfx
from rendercanvas import BaseRenderCanvas

from ..graphics import TextGraphic
from ._utils import create_camera, create_controller
from ._plot_area import PlotArea
from ._frame import Frame
from ..axes import Axes


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

        # imgui windows confined to this subplot, keyed by location
        self._imgui_windows = {loc: None for loc in ["left", "right", "top", "bottom", "toolbar"]}

        self._axes = Axes(self)
        self.scene.add(self.axes.world_object)

        self._frame = Frame(
            viewport=self.viewport,
            rect=rect,
            extent=extent,
            resizeable=resizeable,
            title=name,
            docks=self.docks,
            imgui_windows=self._imgui_windows,
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

    @property
    def imgui_windows(self) -> dict:
        """
        The imgui windows of this subplot, keyed by location.

        The locations are the four edges ["left", "right", "top", "bottom"] and "toolbar"

        Returns
        -------
        dict[str, ImguiWindow]
            {location: ImguiWindow}

        """
        return self._imgui_windows

    def add_imgui_window(
        self,
        window=None,
        *,
        location: str = None,
        size: int = None,
        title: str = "GUI Window",
        window_flags=None,
    ):
        """
        Add an imgui window confined to this subplot. Can also be used as a decorator, see the
        ``Figure.add_imgui_window`` examples.

        Edge windows ("left", "right", "top", "bottom") reserve space outboard of the subplot dock on that edge.
        The "toolbar" location replaces the subplot toolbar. An existing window at a ``location`` is replaced.

        Parameters
        ----------
        window: ImguiWindow, optional
            an ``ImguiWindow`` instance, omit when decorating

        location: str, "left" | "right" | "top" | "bottom" | "toolbar"
            edge windows reserve canvas space, "toolbar" replaces the subplot toolbar

        size: int
            edge or toolbar thickness in pixels, required for edge windows

        title: str
            window title, used when decorating

        window_flags: imgui.WindowFlags_, optional
            imgui window flags, used when decorating, uses the ``ImguiWindow`` default flags if not provided

        """
        figure = self.get_figure()
        if "Imgui" not in figure.__class__.__name__:
            raise TypeError("imgui windows can only be added to a subplot of an ImguiFigure")

        from ..ui._base import ImguiWindow, EDGES, _wrap_update_call

        valid = EDGES + ["toolbar"]
        if location not in valid:
            raise ValueError(
                f"subplot imgui window location must be one of: {valid}, you have passed: {location}"
            )
        if location in EDGES and size is None:
            raise ValueError(f"must provide `size` for an edge window, location: {location}")

        hook_kwargs = dict(figure=figure, subplot=self, location=location, size=size, title=title)
        if window_flags is not None:
            hook_kwargs["window_flags"] = window_flags

        def decorator(_window):
            if isinstance(_window, ImguiWindow):
                win = _window
            elif callable(_window):
                win = ImguiWindow(update_call=_wrap_update_call(_window, self))
            else:
                raise TypeError(
                    "add_imgui_window() must be used as a decorator on a function, or given an `ImguiWindow` instance"
                )

            win._fpl_add_hook(**hook_kwargs)
            self._imgui_windows[location] = win

            # edge windows reserve space, reset the layout
            if location in EDGES:
                figure._fpl_reset_layout()

            return _window

        if window is None:
            return decorator

        decorator(window)
        return window

    def append_imgui_window(self, gui=None, *, location: str = None):
        """
        Append imgui elements to an existing window of this subplot. Can also be used as a decorator. Useful for
        appending elements to the subplot toolbar with ``location="toolbar"``.

        Parameters
        ----------
        gui: callable, optional
            function that draws imgui elements, omit when decorating

        location: str, "left" | "right" | "top" | "bottom" | "toolbar"
            location of the existing window to append to

        """
        from ..ui._base import _wrap_update_call

        window = self._imgui_windows.get(location)
        if window is None:
            raise ValueError(f"no imgui window at location to append to: {location}")

        def decorator(_gui):
            window._update_calls.append(_wrap_update_call(_gui, self))
            return _gui

        if gui is None:
            return decorator

        return decorator(gui)

    def remove_imgui_window(self, location: str):
        """
        Remove and return the imgui window at the given location

        Parameters
        ----------
        location: str
            "left" | "right" | "top" | "bottom" | "toolbar"

        Returns
        -------
        ImguiWindow
            the removed window, it can be added again later

        """
        from ..ui._base import EDGES

        window = self._imgui_windows.get(location)
        self._imgui_windows[location] = None

        # edge windows reserve space, reset the layout
        if location in EDGES:
            self.get_figure()._fpl_reset_layout()

        return window


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
