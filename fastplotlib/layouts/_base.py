from warnings import warn
from typing import *
import weakref

import numpy as np

from pygfx import Scene, OrthographicCamera, PerspectiveCamera, PanZoomController, OrbitController, \
    Viewport, WgpuRenderer
from wgpu.gui.auto import WgpuCanvas

from ..graphics._base import Graphic, GraphicCollection
from ..graphics.line_slider import LineSlider


# dict to store Graphic instances
# this is the only place where the real references to Graphics are stored in a Python session
# {hex id str: Graphic}
GRAPHICS: Dict[str, Graphic] = dict()


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

        self.controller.add_camera(self.camera)
        self.controller.register_events(
            self.viewport,
        )

        self.renderer.add_event_handler(self.set_viewport_rect, "resize")

        # list of hex id strings for all graphics managed by this PlotArea
        # the real Graphic instances are stored in the ``GRAPHICS`` dict
        self._graphics: List[str] = list()

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
        """Graphics in the plot area. Always returns a proxy to the Graphic instances."""
        proxies = list()
        for loc in self._graphics:
            p = weakref.proxy(GRAPHICS[loc])
            proxies.append(p)

        return tuple(proxies)

    def get_rect(self) -> Tuple[float, float, float, float]:
        """allows setting the region occupied by the viewport w.r.t. the parent"""
        raise NotImplementedError("Must be implemented in subclass")

    def set_viewport_rect(self, *args):
        self.viewport.rect = self.get_rect()

    def render(self):
        # does not flush
        self.viewport.render(self.scene, self.camera)

        for child in self.children:
            child.render()

    def add_graphic(self, graphic: Graphic, center: bool = True):
        """
        Add a Graphic to the scene

        Parameters
        ----------
        graphic: Graphic or GraphicCollection
            Add a Graphic or a GraphicCollection to the plot area.
            Note: this must be a real Graphic instance and not a proxy

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
            self._sliders.append(graphic)  # don't manage garbage collection of LineSliders for now
        else:
            # store in GRAPHICS dict
            loc = graphic.loc
            GRAPHICS[loc] = graphic
            self._graphics.append(loc)  # add hex id string for referencing this graphic instance

        # add world object to scene
        self.scene.add(graphic.world_object)

        if center:
            self.center_graphic(graphic)

        # if hasattr(graphic, "_add_plot_area_hook"):
        #     graphic._add_plot_area_hook(self.viewport, self.camera)

    def _check_graphic_name_exists(self, name):
        graphic_names = list()

        for g in self.graphics:
            graphic_names.append(g.name)

        if name in graphic_names:
            raise ValueError(f"graphics must have unique names, current graphic names are:\n {graphic_names}")

    def center_graphic(self, graphic: Graphic, zoom: float = 1.35):
        """
        Center the camera w.r.t. the passed graphic

        Parameters
        ----------
        graphic: Graphic or GraphicCollection
            The graphic instance to center on

        zoom: float, default 1.3
            zoom the camera after centering

        """

        self.camera.show_object(graphic.world_object)

        # camera.show_object can cause the camera width and height to increase so apply a zoom to compensate
        # probably because camera.show_object uses bounding sphere
        self.camera.zoom = zoom

    def center_scene(self, zoom: float = 1.35):
        """
        Auto-center the scene, does not scale.

        Parameters
        ----------
        zoom: float, default 1.3
            apply a zoom after centering the scene

        """
        if not len(self.scene.children) > 0:
            return

        self.camera.show_object(self.scene)

        # camera.show_object can cause the camera width and height to increase so apply a zoom to compensate
        # probably because camera.show_object uses bounding sphere
        self.camera.zoom = zoom

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

        self.camera.zoom = zoom

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

        # graphic_loc = hex(id(graphic.__repr__.__self__))

        # get location
        graphic_loc = graphic.loc

        if graphic_loc not in self._graphics:
            raise KeyError(f"Graphic with following address not found in plot area: {graphic_loc}")

        # remove from scene if necessary
        if graphic.world_object in self.scene.children:
            self.scene.remove(graphic.world_object)

        # remove from list of addresses
        self._graphics.remove(graphic_loc)

        # for GraphicCollection objects
        # if isinstance(graphic, GraphicCollection):
        #     # clear Group
        #     graphic.world_object.clear()
            # graphic.clear()
            # delete all child world objects in the collection
            # for g in graphic.graphics:
            #     subloc = hex(id(g))
            #     del WORLD_OBJECTS[subloc]

        # get mem location of graphic
        # loc = hex(id(graphic))
        # delete world object
        #del WORLD_OBJECTS[graphic_loc]

        del GRAPHICS[graphic_loc]

    def clear(self):
        """
        Clear the Plot or Subplot. Also performs garbage collection, i.e. runs ``delete_graphic`` on all graphics.
        """

        for g in self.graphics:
            self.delete_graphic(g)

    def __getitem__(self, name: str):
        for graphic in self.graphics:
            if graphic.name == name:
                return graphic

        graphic_names = list()
        for g in self.graphics:
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
               f"\t{newline.join(graphic.__repr__() for graphic in self.graphics)}" \
               f"\n"
