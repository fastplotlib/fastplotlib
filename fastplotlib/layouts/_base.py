import numpy as np
from pygfx import Scene, OrthographicCamera, PerspectiveCamera, PanZoomController, OrbitController, \
    Viewport, WgpuRenderer
from wgpu.gui.auto import WgpuCanvas
from warnings import warn
from ..graphics._base import Graphic, WORLD_OBJECTS
from ..graphics.line_slider import LineSlider
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
        """
        Base class for plot creation and management. ``PlotArea`` is not intended to be instantiated by users
        but rather to provide functionallity for ``subplot`` in ``gridplot`` and single ``plot``.

        Parameters
        ----------
        parent: PlotArea
            parent class of subclasses will be a ``PlotArea`` instance
        position: Any
            typical use will be for ``subplots`` in a ``gridplot``, position would correspond to the ``[row, column]``
            location of the ``subplot`` in its ``gridplot``
        camera: pygfx OrthographicCamera or pygfx PerspectiveCamera
            ``OrthographicCamera`` type is used to visualize 2D content and ``PerspectiveCamera`` type is used to view
            3D content, used to view the scene
        controller: pygfx PanZoomController or pygfx OrbitController
            ``PanZoomController`` type is used for 2D pan-zoom camera control and ``OrbitController`` type is used for
            rotating the camera around a center position, used to control the camera
        scene: pygfx Scene
            represents the root of a scene graph, will be viewed by the given ``camera``
        canvas: WgpuCanvas
            provides surface on which a scene will be rendered
        renderer: WgpuRenderer
            object used to render scenes using wgpu
        name: str, optional
            name of ``subplot`` or ``plot`` subclass being instantiated
        """
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

        # hacky workaround for now to exclude from bbox calculations
        self._sliders: List[LineSlider] = list()

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
        """controller used to control camera"""
        return self._controller

    @property
    def graphics(self) -> Tuple[Graphic]:
        """returns the Graphics in the plot area"""
        return tuple(self._graphics)

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
        Add a Graphic to the scene

        Parameters
        ----------
        graphic: Graphic or GraphicCollection
            Add a Graphic or a GraphicCollection to the plot area

        center: bool, default True
            Center the camera on the newly added Graphic

        """
        if not isinstance(graphic, Graphic):
            raise TypeError(
                f"Can only add Graphic types to a PlotArea, you have passed a: {type(graphic)}"
            )

        if graphic.name is not None:  # skip for those that have no name
            self._check_graphic_name_exists(graphic.name)

        # TODO: need to refactor LineSlider entirely
        if isinstance(graphic, LineSlider):
            self._sliders.append(graphic)
        else:
            self._graphics.append(graphic)

        self.scene.add(graphic.world_object)

        if center:
            self.center_graphic(graphic)

        # if hasattr(graphic, "_add_plot_area_hook"):
        #     graphic._add_plot_area_hook(self.viewport, self.camera)

    def _check_graphic_name_exists(self, name):
        graphic_names = list()

        for g in self._graphics:
            graphic_names.append(g.name)

        if name in graphic_names:
            raise ValueError(f"graphics must have unique names, current graphic names are:\n {graphic_names}")

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
        # hacky workaround for now until I figure out how to put it in its own scene
        for slider in self._sliders:
            self.scene.remove(slider.world_object)

        self.center_scene()
        if not isinstance(maintain_aspect, bool):
            maintain_aspect = False  # assume False
        self.camera.maintain_aspect = maintain_aspect

        if len(self.scene.children) > 0:
            width, height, depth = np.ptp(self.scene.get_world_bounding_box(), axis=0)
        else:
            width, height, depth = (1, 1, 1)

        for slider in self._sliders:
            self.scene.add(slider.world_object)

        self.camera.width = width
        self.camera.height = height

        # self.controller.distance = 0

        self.controller.zoom(zoom / self.controller.zoom_value)

    def remove_graphic(self, graphic: Graphic):
        """
        Remove a ``Graphic`` from the scene. Note: This does not garbage collect the graphic,
        you can add it back to the scene after removing it. Use ``delete_graphic()`` to
        delete and garbage collect a ``Graphic``.

        Parameters
        ----------
        graphic: Graphic or GraphicCollection
            The graphic to remove from the scene

        """

        self.scene.remove(graphic.world_object)

    def delete_graphic(self, graphic: Graphic):
        """
        Delete the graphic, garbage collects and frees GPU VRAM.

        Parameters
        ----------
        graphic: Graphic or GraphicCollection
            The graphic to delete

        """

        if graphic not in self._graphics:
            raise KeyError

        if graphic.world_object in self.scene.children:
            self.scene.remove(graphic.world_object)

        self._graphics.remove(graphic)

        # delete associated world object to free GPU VRAM
        loc = hex(id(graphic))
        del WORLD_OBJECTS[loc]

        del graphic

    def clear(self):
        """
        Clear the Plot or Subplot. Also performs garbage collection, i.e. runs ``delete_graphic`` on all graphics.
        """

        for g in self._graphics:
            self.delete_graphic(g)

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
               f"\t{newline.join(graphic.__repr__() for graphic in self._graphics)}" \
               f"\n"
