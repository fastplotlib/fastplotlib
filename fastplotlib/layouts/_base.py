from typing import *
import weakref

import numpy as np

import pygfx
from pygfx import Scene, OrthographicCamera, PerspectiveCamera, PanZoomController, OrbitController, \
    Viewport, WgpuRenderer
from pylinalg import vec_transform, vec_unproject
from wgpu.gui.auto import WgpuCanvas

from ..graphics._base import Graphic, GraphicCollection
from ..graphics.selectors._base_selector import BaseSelector

# dict to store Graphic instances
# this is the only place where the real references to Graphics are stored in a Python session
# {hex id str: Graphic}
GRAPHICS: Dict[str, Graphic] = dict()
SELECTORS: Dict[str, BaseSelector] = dict()


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

        # selectors are in their own list so they can be excluded from scene bbox calculations
        # managed similar to GRAPHICS for garbage collection etc.
        self._selectors: List[str] = list()

        self._name = name

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
    def graphics(self) -> Tuple[Graphic, ...]:
        """Graphics in the plot area. Always returns a proxy to the Graphic instances."""
        proxies = list()
        for loc in self._graphics:
            p = weakref.proxy(GRAPHICS[loc])
            proxies.append(p)

        return tuple(proxies)

    @property
    def selectors(self) -> Tuple[BaseSelector, ...]:
        """Selectors in the plot area. Always returns a proxy to the Graphic instances."""
        proxies = list()
        for loc in self._selectors:
            p = weakref.proxy(SELECTORS[loc])
            proxies.append(p)

        return tuple(proxies)

    @property
    def name(self) -> Any:
        return self._name

    @name.setter
    def name(self, name: Any):
        self._name = name

    def get_rect(self) -> Tuple[float, float, float, float]:
        """allows setting the region occupied by the viewport w.r.t. the parent"""
        raise NotImplementedError("Must be implemented in subclass")

    def map_screen_to_world(self, pos: Union[Tuple[float, float], pygfx.PointerEvent]) -> np.ndarray:
        """
        Map screen position to world position

        Parameters
        ----------
        pos: (float, float) | pygfx.PointerEvent
            ``(x, y)`` screen coordinates, or ``pygfx.PointerEvent``

        """
        if isinstance(pos, pygfx.PointerEvent):
            pos = pos.x, pos.y

        if not self.viewport.is_inside(*pos):
            return None

        vs = self.viewport.logical_size

        # get position relative to viewport
        pos_rel = (
            pos[0] - self.viewport.rect[0],
            pos[1] - self.viewport.rect[1],
        )

        # convert screen position to NDC
        pos_ndc = (
            pos_rel[0] / vs[0] * 2 - 1,
            -(pos_rel[1] / vs[1] * 2 - 1),
            0
        )

        # get world position
        pos_ndc += vec_transform(self.camera.world.position, self.camera.camera_matrix)
        pos_world = vec_unproject(pos_ndc[:2], self.camera.camera_matrix)

        # default z is zero for now
        return np.array([*pos_world[:2], 0])

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
        self._add_or_insert_graphic(graphic=graphic, center=center, action="add")

        graphic.position_z = len(self._graphics)

    def insert_graphic(
            self,
            graphic: Graphic,
            center: bool = True,
            index: int = 0,
            z_position: int = None
    ):
        """
        Insert graphic into scene at given position ``index`` in stored graphics.

        Parameters
        ----------
        graphic: Graphic or GraphicCollection
            Add a Graphic or a GraphicCollection to the plot area at a given position.
            Note: must be a real Graphic instance, not a weakref proxy to a Graphic

        center: bool, default True
            Center the camera on the newly added Graphic

        index: int, default 0
            Index to insert graphic. 

        z_position: int, default None
            z axis position to place Graphic. If ``None``, uses value of `index` argument

        """
        if index > len(self._graphics):
            raise IndexError(f"Position {index} is out of bounds for number of graphics currently "
                             f"in the PlotArea: {len(self._graphics)}\n"
                             f"Call `add_graphic` method to insert graphic in the last position of the stored graphics")

        self._add_or_insert_graphic(graphic=graphic, center=center, action="insert", index=index)

        if z_position is None:
            graphic.position_z = index
        else:
            graphic.position_z = z_position

    def _add_or_insert_graphic(
            self,
            graphic: Graphic,
            center: bool = True,
            action: str = Union["insert", "add"],
            index: int = 0
    ):
        """Private method to handle inserting or adding a graphic to a PlotArea."""
        if not isinstance(graphic, Graphic):
            raise TypeError(
                f"Can only add Graphic types to a PlotArea, you have passed a: {type(graphic)}"
            )

        if graphic.name is not None:  # skip for those that have no name
            self._check_graphic_name_exists(graphic.name)

        if isinstance(graphic, BaseSelector):
            # store in SELECTORS dict
            loc = graphic.loc
            SELECTORS[loc] = graphic # add hex id string for referencing this graphic instance
            # don't manage garbage collection of LineSliders for now
            if action == "insert":
                self._selectors.insert(index, loc)
            else:
                self._selectors.append(loc)
        else:
            # store in GRAPHICS dict
            loc = graphic.loc
            GRAPHICS[loc] = graphic # add hex id string for referencing this graphic instance

            if action == "insert":
                self._graphics.insert(index, loc)
            else:
                self._graphics.append(loc)

        # add world object to scene
        self.scene.add(graphic.world_object)

        if center:
            self.center_graphic(graphic)

        if hasattr(graphic, "_add_plot_area_hook"):
            graphic._add_plot_area_hook(self)

    def _check_graphic_name_exists(self, name):
        graphic_names = list()

        for g in self.graphics:
            graphic_names.append(g.name)

        for s in self.selectors:
            graphic_names.append(s.name)

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
        # hacky workaround for now until we decided if we want to put selectors in their own scene
        # remove all selectors from a scene to calculate scene bbox
        for selector in self.selectors:
            self.scene.remove(selector.world_object)

        self.center_scene()
        if not isinstance(maintain_aspect, bool):
            maintain_aspect = False  # assume False
        self.camera.maintain_aspect = maintain_aspect

        if len(self.scene.children) > 0:
            width, height, depth = np.ptp(self.scene.get_world_bounding_box(), axis=0)
        else:
            width, height, depth = (1, 1, 1)

        for selector in self.selectors:
            self.scene.add(selector.world_object)

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
        # TODO: proper gc of selectors, RAM is freed for regular graphics but not selectors
        # TODO: references to selectors must be lingering somewhere
        # get location
        loc = graphic.loc

        # check which dict it's in
        if loc in self._graphics:
            glist = self._graphics
            kind = "graphic"
        elif loc in self._selectors:
            kind = "selector"
            glist = self._selectors
        else:
            raise KeyError(f"Graphic with following address not found in plot area: {loc}")

        # remove from scene if necessary
        if graphic.world_object in self.scene.children:
            self.scene.remove(graphic.world_object)

        # remove from list of addresses
        glist.remove(loc)

        if kind == "graphic":
            del GRAPHICS[loc]
        elif kind == "selector":
            del SELECTORS[loc]

    def clear(self):
        """
        Clear the Plot or Subplot. Also performs garbage collection, i.e. runs ``delete_graphic`` on all graphics.
        """

        for g in self.graphics:
            self.delete_graphic(g)

        for s in self.selectors:
            self.delete_graphic(s)

    def __getitem__(self, name: str):
        for graphic in self.graphics:
            if graphic.name == name:
                return graphic

        for selector in self.selectors:
            if selector.name == name:
                return selector

        graphic_names = list()
        for g in self.graphics:
            graphic_names.append(g.name)
        for s in self.selectors:
            graphic_names.append(s.name)
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
