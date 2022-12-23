import numpy as np
from pygfx import Scene, OrthographicCamera, PerspectiveCamera, PanZoomController, OrbitController, \
    Viewport, WgpuRenderer
from wgpu.gui.auto import WgpuCanvas
from warnings import warn
from ..graphics._base import Graphic
from typing import *


class PlotArea:
    def __init__(
            self,
            parent,
            position: Any,
            camera: Union[OrthographicCamera, PerspectiveCamera],
            controller: Union[PanZoomController, OrbitController],
            scene: Scene,
            canvas: WgpuCanvas,
            renderer: WgpuRenderer,
            name: str = None,
    ):
        self._parent: PlotArea = parent
        self._position = position

        self._scene = scene
        self._canvas = canvas
        self._renderer = renderer
        if parent is None:
            self._viewport: Viewport = Viewport(renderer)
        else:
            self._viewport = Viewport(parent.renderer)

        self._camera = camera
        self._controller = controller

        self.controller.add_default_event_handlers(
            self.viewport,
            self.camera
        )

        # camera.far and camera.near clipping planes get
        # wonky with setting controller.distance = 0
        if isinstance(self.camera, OrthographicCamera):
            self.controller.distance = 0
            # also set a initial zoom
            self.controller.zoom(0.8 / self.controller.zoom_value)

        self.renderer.add_event_handler(self.set_viewport_rect, "resize")

        self._graphics: List[Graphic] = list()

        self.name = name

        # need to think about how to deal with children better
        self.children = list()

        self.set_viewport_rect()

    # several read-only properties
    @property
    def parent(self):
        """The parent PlotArea"""
        return self._parent

    @property
    def position(self) -> Union[Tuple[int, int], Any]:
        """Used by subclass to manage its own referencing system"""
        return self._position

    @property
    def scene(self) -> Scene:
        """The Scene where Graphics live"""
        return self._scene

    @property
    def canvas(self) -> WgpuCanvas:
        """Canvas associated to the plot area"""
        return self._canvas

    @property
    def renderer(self) -> WgpuRenderer:
        """Renderer associated to the plot area"""
        return self._renderer

    @property
    def viewport(self) -> Viewport:
        return self._viewport

    @property
    def camera(self) -> Union[OrthographicCamera, PerspectiveCamera]:
        """camera used to view the scene"""
        return self._camera

    # in the future we can think about how to allow changing the controller
    @property
    def controller(self) -> Union[PanZoomController, OrbitController]:
        return self._controller

    def get_rect(self) -> Tuple[float, float, float, float]:
        """allows setting the region occupied by the viewport w.r.t. the parent"""
        raise NotImplementedError("Must be implemented in subclass")

    def set_viewport_rect(self, *args):
        self.viewport.rect = self.get_rect()

    def render(self):
        # does not flush
        self.controller.update_camera(self.camera)
        self.viewport.render(self.scene, self.camera)

        for child in self.children:
            child.render()

    def add_graphic(self, graphic: Graphic, center: bool = True):
        """
        Add a Graphic to the scne

        Parameters
        ----------
        graphic: Graphic or GraphicCollection
            Add a Graphic or a GraphicCollection to the plot area

        center: bool, default True
            Center the camera on the newly added Graphic

        """
        if graphic.name is not None:  # skip for those that have no name
            graphic_names = list()

            for g in self._graphics:
                graphic_names.append(g.name)

            if graphic.name in graphic_names:
                raise ValueError(f"graphics must have unique names, current graphic names are:\n {graphic_names}")

        self._graphics.append(graphic)
        self.scene.add(graphic.world_object)

        if center:
            self.center_graphic(graphic)

    def _refresh_camera(self):
        self.controller.update_camera(self.camera)
        if sum(self.renderer.logical_size) > 0:
            scene_lsize = self.viewport.rect[2], self.viewport.rect[3]
        else:
            scene_lsize = (1, 1)

        self.camera.set_view_size(*scene_lsize)
        self.camera.update_projection_matrix()

    def center_graphic(self, graphic: Graphic, zoom: float = 1.3):
        """
        Center the camera w.r.t. the passed graphic

        Parameters
        ----------
        graphic: Graphic or GraphicCollection
            The graphic instance to center on

        zoom: float, default 1.3
            zoom the camera after centering

        """
        if not isinstance(self.camera, OrthographicCamera):
            warn("`center_graphic()` not yet implemented for `PerspectiveCamera`")
            return

        self._refresh_camera()

        self.controller.show_object(self.camera, graphic.world_object)

        self.controller.zoom(zoom)

    def center_scene(self, zoom: float = 1.3):
        """
        Auto-center the scene, does not scale.

        Parameters
        ----------
        zoom: float, default 1.3
            apply a zoom after centering the scene

        """
        if not len(self.scene.children) > 0:
            return

        if not isinstance(self.camera, OrthographicCamera):
            warn("`center_scene()` not yet implemented for `PerspectiveCamera`")
            return

        self._refresh_camera()

        self.controller.show_object(self.camera, self.scene)

        self.controller.zoom(zoom)

    def auto_scale(self, maintain_aspect: bool = False, zoom: float = 0.8):
        """
        Auto-scale the camera w.r.t to the scene

        Parameters
        ----------
        maintain_aspect: bool, default ``False``
            maintain the camera aspect ratio for all dimensions, if ``False`` the camera
            is scaled according to the bounds in each dimension.

        zoom: float, default 0.8
            zoom value for the camera after auto-scaling, if zoom = 1.0 then the graphics
            in the scene will fill the entire canvas.
        """
        self.center_scene()
        self.camera.maintain_aspect = maintain_aspect

        width, height, depth = np.ptp(self.scene.get_world_bounding_box(), axis=0)

        self.camera.width = width
        self.camera.height = height

        # self.controller.distance = 0

        self.controller.zoom(zoom / self.controller.zoom_value)

    def get_graphics(self):
        """
        Get all the Graphic instances in the Scene

        Returns
        -------

        """
        return self._graphics

    def remove_graphic(self, graphic: Graphic):
        """
        Remove a graphic from the scene. Note: This does not garbage collect the graphic,
        you can add it back to the scene after removing it.

        Parameters
        ----------
        graphic: Graphic or GraphicCollection
            The graphic to remove from the scene

        """
        self.scene.remove(graphic.world_object)

    def __getitem__(self, name: str):
        for graphic in self._graphics:
            if graphic.name == name:
                return graphic

        graphic_names = list()
        for g in self._graphics:
            graphic_names.append(g.name)
        raise IndexError(f"no graphic of given name, the current graphics are:\n {graphic_names}")

    def __str__(self):
        if self.name is None:
            name = "unnamed"
        else:
            name = self.name

        return f"{name}: {self.__class__.__name__} @ {hex(id(self))}"

    def __repr__(self):
        newline = "\n\t"

        return f"{self}\n" \
               f"  parent: {self.parent}\n" \
               f"  Graphics:\n" \
               f"\t{newline.join(graphic.__repr__() for graphic in self.get_graphics())}" \
               f"\n"
