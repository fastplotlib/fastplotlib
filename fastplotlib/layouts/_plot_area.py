from inspect import getfullargspec
from typing import *
import weakref
from warnings import warn

import numpy as np

import pygfx
from pylinalg import vec_transform, vec_unproject
from wgpu.gui.auto import WgpuCanvas

from ._utils import create_camera, create_controller
from ..graphics._base import Graphic
from ..graphics.selectors._base_selector import BaseSelector
from ..legends import Legend

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
        camera: Union[pygfx.PerspectiveCamera],
        controller: Union[pygfx.Controller],
        scene: pygfx.Scene,
        canvas: WgpuCanvas,
        renderer: pygfx.WgpuRenderer,
        name: str = None,
    ):
        """
        Base class for plot creation and management. ``PlotArea`` is not intended to be instantiated by users
        but rather to provide functionality for ``subplot`` in ``gridplot`` and single ``plot``.

        Parameters
        ----------
        parent: PlotArea
            parent class of subclasses will be a ``PlotArea`` instance

        position: Any
            typical use will be for ``subplots`` in a ``gridplot``, position would correspond to the ``[row, column]``
            location of the ``subplot`` in its ``gridplot``

        camera: pygfx.PerspectiveCamera
            Use perspective camera for both perspective and orthographic views. Set fov = 0 for orthographic mode.

        controller: pygfx.Controller
            One of the pygfx controllers, panzoom, fly, orbit, or trackball

        scene: pygfx.Scene
            represents the root of a scene graph, will be viewed by the given ``camera``

        canvas: WgpuCanvas
            provides surface on which a scene will be rendered

        renderer: pygfx.WgpuRenderer
            renders the scene onto the canvas

        name: str, optional
            name this ``subplot`` or ``plot``
            
        """

        self._parent: PlotArea = parent
        self._position = position

        self._scene = scene
        self._canvas = canvas
        self._renderer = renderer
        if parent is None:
            self._viewport: pygfx.Viewport = pygfx.Viewport(renderer)
        else:
            self._viewport = pygfx.Viewport(parent.renderer)

        self._camera = camera
        self._controller = controller

        self.controller.add_camera(self._camera)
        self.controller.register_events(
            self.viewport,
        )

        self._animate_funcs_pre = list()
        self._animate_funcs_post = list()

        self.renderer.add_event_handler(self.set_viewport_rect, "resize")

        # list of hex id strings for all graphics managed by this PlotArea
        # the real Graphic instances are stored in the ``GRAPHICS`` dict
        self._graphics: List[str] = list()

        # selectors are in their own list so they can be excluded from scene bbox calculations
        # managed similar to GRAPHICS for garbage collection etc.
        self._selectors: List[str] = list()

        self.name = name

        # need to think about how to deal with children better
        self.children = list()

        self.set_viewport_rect()

    # several read-only properties
    @property
    def parent(self):
        """A parent if relevant, used by individual Subplots in GridPlot"""
        return self._parent

    @property
    def position(self) -> Union[Tuple[int, int], Any]:
        """Position of this plot area within a larger layout (such as GridPlot) if relevant"""
        return self._position

    @property
    def scene(self) -> pygfx.Scene:
        """The Scene where Graphics lie in this plot area"""
        return self._scene

    @property
    def canvas(self) -> WgpuCanvas:
        """Canvas associated to the plot area"""
        return self._canvas

    @property
    def renderer(self) -> pygfx.WgpuRenderer:
        """Renderer associated to the plot area"""
        return self._renderer

    @property
    def viewport(self) -> pygfx.Viewport:
        """The rectangular area of the renderer associated to this plot area"""
        return self._viewport

    @property
    def camera(self) -> pygfx.PerspectiveCamera:
        """camera used to view the scene"""
        return self._camera

    @camera.setter
    def camera(self, new_camera: Union[str, pygfx.PerspectiveCamera]):
        # user wants to set completely new camera, remove current camera from controller
        if isinstance(new_camera, pygfx.PerspectiveCamera):
            self.controller.remove_camera(self._camera)
            # add new camera to controller
            self.controller.add_camera(new_camera)

            self._camera = new_camera

        # modify FOV if necessary
        elif isinstance(new_camera, str):
            if new_camera == "2d":
                self._camera.fov = 0

            elif new_camera == "3d":
                # orthographic -> perspective only if fov = 0, i.e. if camera is in ortho mode
                # otherwise keep same FOV
                if self._camera.fov == 0:
                    self._camera.fov = 50

            else:
                raise ValueError("camera must be one of '2d', '3d' or a pygfx.PerspectiveCamera instance")
        else:
            raise ValueError("camera must be one of '2d', '3d' or a pygfx.PerspectiveCamera instance")

    # in the future we can think about how to allow changing the controller
    @property
    def controller(self) -> pygfx.Controller:
        """controller used to control the camera"""
        return self._controller

    @controller.setter
    def controller(self, new_controller: Union[str, pygfx.Controller]):
        new_controller = create_controller(new_controller, self._camera)

        cameras_list = list()

        # remove all the cameras associated to this controller
        for camera in self._controller.cameras:
            self._controller.remove_camera(camera)
            cameras_list.append(camera)

        # add the associated cameras to the new controller
        for camera in cameras_list:
            new_controller.add_camera(camera)

        new_controller.register_events(
            self.viewport
        )

        # TODO: monkeypatch until we figure out a better
        #  pygfx plans on refactoring viewports anyways
        if self.parent is not None:
            if self.parent.__class__.__name__ == "GridPlot":
                for subplot in self.parent:
                    if subplot.camera in cameras_list:
                        new_controller.register_events(subplot.viewport)
                        subplot._controller = new_controller

        self._controller = new_controller

    @property
    def graphics(self) -> Tuple[Graphic, ...]:
        """Graphics in the plot area. Always returns a proxy to the Graphic instances."""
        proxies = list()
        for loc in self._graphics:
            p = weakref.proxy(GRAPHICS[loc])
            if p.__class__.__name__ == "Legend":
                continue
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
    def legends(self) -> Tuple[Legend, ...]:
        """Legends in the plot area."""
        proxies = list()
        for loc in self._graphics:
            p = weakref.proxy(GRAPHICS[loc])
            if p.__class__.__name__ == "Legend":
                proxies.append(p)

        return tuple(proxies)

    @property
    def name(self) -> str:
        """The name of this plot area"""
        return self._name

    @name.setter
    def name(self, name: str):
        if not isinstance(name, str):
            raise TypeError("PlotArea `name` must be of type <str>")
        self._name = name

    def get_rect(self) -> Tuple[float, float, float, float]:
        """
        Returns the viewport rect to define the rectangle
        occupied by the viewport w.r.t. the Canvas.

        If this is a subplot within a GridPlot, it returns the rectangle
        for only this subplot w.r.t. the parent canvas.

        Must return: [x_pos, y_pos, width_viewport, height_viewport]

        """
        raise NotImplementedError("Must be implemented in subclass")

    def map_screen_to_world(
        self, pos: Union[Tuple[float, float], pygfx.PointerEvent]
    ) -> np.ndarray:
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
        pos_ndc = (pos_rel[0] / vs[0] * 2 - 1, -(pos_rel[1] / vs[1] * 2 - 1), 0)

        # get world position
        pos_ndc += vec_transform(self.camera.world.position, self.camera.camera_matrix)
        pos_world = vec_unproject(pos_ndc[:2], self.camera.camera_matrix)

        # default z is zero for now
        return np.array([*pos_world[:2], 0])

    def set_viewport_rect(self, *args):
        self.viewport.rect = self.get_rect()

    def render(self):
        self._call_animate_functions(self._animate_funcs_pre)

        # does not flush, flush must be implemented in user-facing Plot objects
        self.viewport.render(self.scene, self.camera)

        for child in self.children:
            child.render()

        self._call_animate_functions(self._animate_funcs_post)

    def _call_animate_functions(self, funcs: Iterable[callable]):
        for fn in funcs:
            try:
                args = getfullargspec(fn).args

                if len(args) > 0:
                    if args[0] == "self" and not len(args) > 1:
                        fn()
                    else:
                        fn(self)
                else:
                    fn()
            except (ValueError, TypeError):
                warn(
                    f"Could not resolve argspec of {self.__class__.__name__} animation function: {fn}, "
                    f"calling it without arguments."
                )
                fn()

    def add_animations(
        self,
        *funcs: Iterable[callable],
        pre_render: bool = True,
        post_render: bool = False,
    ):
        """
        Add function(s) that are called on every render cycle.
        These are called at the Subplot level.

        Parameters
        ----------
        *funcs: callable or iterable of callable
            function(s) that are called on each render cycle

        pre_render: bool, default ``True``, optional keyword-only argument
            if true, these function(s) are called before a render cycle

        post_render: bool, default ``False``, optional keyword-only argument
            if true, these function(s) are called after a render cycle

        """
        for f in funcs:
            if not callable(f):
                raise TypeError(
                    f"all positional arguments to add_animations() must be callable types, you have passed a: {type(f)}"
                )
            if pre_render:
                self._animate_funcs_pre += funcs
            if post_render:
                self._animate_funcs_post += funcs

    def remove_animation(self, func):
        """
        Removes the passed animation function from both pre and post render.

        Parameters
        ----------
        func: callable
            The function to remove, raises a error if it's not registered as a pre or post animation function.

        """
        if func not in self._animate_funcs_pre and func not in self._animate_funcs_post:
            raise KeyError(
                f"The passed function: {func} is not registered as an animation function. These are the animation "
                f" functions that are currently registered:\n"
                f"pre: {self._animate_funcs_pre}\n\npost: {self._animate_funcs_post}"
            )

        if func in self._animate_funcs_pre:
            self._animate_funcs_pre.remove(func)

        if func in self._animate_funcs_post:
            self._animate_funcs_post.remove(func)

    def add_graphic(self, graphic: Graphic, center: bool = True):
        """
        Add a Graphic to the scene

        Parameters
        ----------
        graphic: Graphic or `:ref:GraphicCollection`
            Add a Graphic or a GraphicCollection to the plot area.
            Note: this must be a real Graphic instance and not a proxy

        center: bool, default True
            Center the camera on the newly added Graphic

        """

        if graphic in self:
            # graphic is already in this plot but was removed from the scene, add it back
            self.scene.add(graphic.world_object)
            return

        self._add_or_insert_graphic(graphic=graphic, center=center, action="add")

        graphic.position_z = len(self)

    def insert_graphic(
        self,
        graphic: Graphic,
        center: bool = True,
        index: int = 0,
        z_position: int = None,
    ):
        """
        Insert graphic into scene at given position ``index`` in stored graphics.

        Parameters
        ----------
        graphic: Graphic
            Add a Graphic to the plot area at a given position.
            Note: must be a real Graphic instance, not a weakref proxy to a Graphic

        center: bool, default True
            Center the camera on the newly added Graphic

        index: int, default 0
            Index to insert graphic.

        z_position: int, default None
            z axis position to place Graphic. If ``None``, uses value of `index` argument

        """
        if index > len(self._graphics):
            raise IndexError(
                f"Position {index} is out of bounds for number of graphics currently "
                f"in the PlotArea: {len(self._graphics)}\n"
                f"Call `add_graphic` method to insert graphic in the last position of the stored graphics"
            )

        self._add_or_insert_graphic(
            graphic=graphic, center=center, action="insert", index=index
        )

        if z_position is None:
            graphic.position_z = index
        else:
            graphic.position_z = z_position

    def _add_or_insert_graphic(
        self,
        graphic: Graphic,
        center: bool = True,
        action: str = Union["insert", "add"],
        index: int = 0,
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
            SELECTORS[
                loc
            ] = graphic  # add hex id string for referencing this graphic instance
            # don't manage garbage collection of LineSliders for now
            if action == "insert":
                self._selectors.insert(index, loc)
            else:
                self._selectors.append(loc)
        else:
            # store in GRAPHICS dict
            loc = graphic.loc
            GRAPHICS[
                loc
            ] = graphic  # add hex id string for referencing this graphic instance

            if action == "insert":
                self._graphics.insert(index, loc)
            else:
                self._graphics.append(loc)

        # now that it's in the dict, just use the weakref
        graphic = weakref.proxy(graphic)

        # add world object to scene
        self.scene.add(graphic.world_object)

        if center:
            self.center_graphic(graphic)

        # if we don't use the weakref above, then the object lingers if a plot hook is used!
        if hasattr(graphic, "_add_plot_area_hook"):
            graphic._add_plot_area_hook(self)

    def _check_graphic_name_exists(self, name):
        graphic_names = list()

        for g in self.graphics:
            graphic_names.append(g.name)

        for s in self.selectors:
            graphic_names.append(s.name)

        for l in self.legends:
            graphic_names.append(l.name)

        if name in graphic_names:
            raise ValueError(
                f"graphics must have unique names, current graphic names are:\n {graphic_names}"
            )

    def center_graphic(self, graphic: Graphic, zoom: float = 1.35):
        """
        Center the camera w.r.t. the passed graphic

        Parameters
        ----------
        graphic: Graphic
            The graphic instance to center on

        zoom: float, default 1.3
            zoom the camera after centering

        """

        self.camera.show_object(graphic.world_object)

        # camera.show_object can cause the camera width and height to increase so apply a zoom to compensate
        # probably because camera.show_object uses bounding sphere
        self.camera.zoom = zoom

    def center_scene(self, *, zoom: float = 1.35):
        """
        Auto-center the scene, does not scale.

        Parameters
        ----------
        zoom: float, default 1.3
            apply a zoom after centering the scene

        """
        if not len(self.scene.children) > 0:
            return

        # scale all cameras associated with this controller
        # else it looks wonky
        for camera in self.controller.cameras:
            camera.show_object(self.scene)

            # camera.show_object can cause the camera width and height to increase so apply a zoom to compensate
            # probably because camera.show_object uses bounding sphere
            camera.zoom = zoom

    def auto_scale(
            self,
            *,  # since this is often used as an event handler, don't want to coerce maintain_aspect = True
            maintain_aspect: Union[None, bool] = None,
            zoom: float = 0.8
    ):
        """
        Auto-scale the camera w.r.t to the scene

        Parameters
        ----------
        maintain_aspect: ``None`` or bool, default ``None``
            Maintain the camera aspect ratio for all dimensions. If ``None``, the aspect is left unchanged.
            if ``False`` the camera is scaled to the bounding box of the current scene.

        zoom: float, default 0.8
            zoom value for the camera after auto-scaling, if zoom = 1.0 then the graphics
            in the scene will fill the entire canvas.
        """
        if not len(self.scene.children) > 0:
            return
        # hacky workaround for now until we decide if we want to put selectors in their own scene
        # remove all selectors from a scene to calculate scene bbox
        for selector in self.selectors:
            self.scene.remove(selector.world_object)

        self.center_scene()

        if maintain_aspect is None:  # if not provided keep current setting
            maintain_aspect = self.camera.maintain_aspect

        # scale all cameras associated with this controller else it looks wonky
        for camera in self.controller.cameras:
            camera.maintain_aspect = maintain_aspect

        if len(self.scene.children) > 0:
            width, height, depth = np.ptp(self.scene.get_world_bounding_box(), axis=0)
        else:
            width, height, depth = (1, 1, 1)

        # make sure width and height are non-zero
        if width < 0.01:
            width = 1
        if height < 0.01:
            height = 1

        for selector in self.selectors:
            self.scene.add(selector.world_object)

        # scale all cameras associated with this controller else it looks wonky
        for camera in self.controller.cameras:
            camera.width = width
            camera.height = height

            camera.zoom = zoom

    def remove_graphic(self, graphic: Graphic):
        """
        Remove a ``Graphic`` from the scene. Note: This does not garbage collect the graphic,
        you can add it back to the scene after removing it. Use ``delete_graphic()`` to
        delete and garbage collect a ``Graphic``.

        Parameters
        ----------
        graphic: Graphic
            The graphic to remove from the scene

        """

        self.scene.remove(graphic.world_object)

    def delete_graphic(self, graphic: Graphic):
        """
        Delete the graphic, garbage collects and frees GPU VRAM.

        Parameters
        ----------
        graphic: Graphic
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
            raise KeyError(
                f"Graphic with following address not found in plot area: {loc}"
            )

        # remove from scene if necessary
        if graphic.world_object in self.scene.children:
            self.scene.remove(graphic.world_object)

        # remove from list of addresses
        glist.remove(loc)

        # cleanup
        graphic._cleanup()

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

        for legend in self.legends:
            if legend.name == name:
                return legend

        graphic_names = list()
        for g in self.graphics:
            graphic_names.append(g.name)

        selector_names = list()
        for s in self.selectors:
            selector_names.append(s.name)

        raise IndexError(
            f"No graphic or selector of given name.\n"
            f"The current graphics are:\n {graphic_names}\n"
            f"The current selectors are:\n {selector_names}"
        )

    def __contains__(self, item: Union[str, Graphic]):
        to_check = [*self.graphics, *self.selectors, *self.legends]

        if isinstance(item, Graphic):
            if item in to_check:
                return True
            else:
                return False

        elif isinstance(item, str):
            for graphic in to_check:
                # only check named graphics
                if graphic.name is None:
                    continue

                if graphic.name == item:
                    return True

            return False

        raise TypeError("PlotArea `in` operator accepts only `Graphic` or `str` types")
    
    def __str__(self):
        if self.name is None:
            name = "unnamed"
        else:
            name = self.name

        return f"{name}: {self.__class__.__name__} @ {hex(id(self))}"

    def __repr__(self):
        newline = "\n\t"

        return (
            f"{self}\n"
            f"  parent: {self.parent.__str__()}\n"
            f"  Graphics:\n"
            f"\t{newline.join(graphic.__repr__() for graphic in self.graphics)}"
            f"\n"
        )

    def __len__(self) -> int:
        return len(self._graphics) + len(self.selectors)
