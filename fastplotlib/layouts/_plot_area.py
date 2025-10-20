from inspect import getfullargspec
from typing import Literal, Union
from warnings import warn

import numpy as np

import pygfx
from pylinalg import vec_transform, vec_unproject
from rendercanvas import BaseRenderCanvas

from ._utils import create_controller
from ..graphics._base import Graphic
from ..graphics import ImageGraphic
from ..graphics.selectors._base_selector import BaseSelector
from ._graphic_methods_mixin import GraphicMethodsMixin
from ..legends import Legend


try:
    get_ipython()
except NameError:
    IS_IPYTHON = False
    IPYTHON = None
else:
    IS_IPYTHON = True
    IPYTHON = get_ipython()


class PlotArea(GraphicMethodsMixin):
    def __init__(
        self,
        parent: Union["PlotArea", "Figure"],
        camera: pygfx.PerspectiveCamera,
        controller: pygfx.Controller,
        scene: pygfx.Scene,
        canvas: BaseRenderCanvas,
        renderer: pygfx.WgpuRenderer,
        name: str = None,
    ):
        """
        Base class for plot creation and management. ``PlotArea`` is not intended to be instantiated by users
        but rather to provide functionality for ``subplots`` in a user ``Figure``

        Parameters
        ----------
        parent: PlotArea or Figure
            parent object

        position: Any
            position of the plot area. In a ``subplot`` position would correspond to the ``[row, column]``
            index of the ``subplot``. In docks this would correspond to a str name, "top", "right", "bottom" or "left"

        camera: pygfx.PerspectiveCamera
            Use perspective camera for both perspective and orthographic views. Set fov = 0 for orthographic projection

        controller: pygfx.Controller
            One of the pygfx controllers: "panzoom", "fly", "trackball", "orbit"

        scene: pygfx.Scene
            represents the root of a scene graph, will be viewed by the given ``camera``

        canvas: BaseRenderCanvas
            provides surface on which a scene will be rendered

        renderer: pygfx.WgpuRenderer
            renders the scene onto the canvas

        name: str, optional
            name this plot area

        """

        self._parent = parent

        self._scene = scene
        self._canvas = canvas
        self._renderer = renderer
        self._viewport: pygfx.Viewport = pygfx.Viewport(renderer)

        self._camera = camera
        self._controller = controller

        self.controller.add_camera(self._camera)
        self.controller.register_events(
            self.viewport,
        )

        self._animate_funcs_pre: list[callable] = list()
        self._animate_funcs_post: list[callable] = list()

        # list of all graphics managed by this PlotArea
        self._graphics: list[Graphic] = list()

        # selectors are in their own list so they can be excluded from scene bbox calculations
        self._selectors: list[BaseSelector] = list()

        # legends, managed just like other graphics as explained above
        self._legends: list[Legend] = list()

        # keep all graphics in a separate group, makes bbox calculations etc. easier
        # this is the "real scene" excluding axes, selection tools etc.
        self._fpl_graphics_scene = pygfx.Group()
        self.scene.add(self._fpl_graphics_scene)

        self._name = name

        # need to think about how to deal with children better
        self.children = list()

        self._background_material = pygfx.BackgroundMaterial(
            (0.0, 0.0, 0.0, 1.0),
            (0.0, 0.0, 0.0, 1.0),
            (0.0, 0.0, 0.0, 1.0),
            (0.0, 0.0, 0.0, 1.0),
            alpha_mode="blend",
        )
        self._background = pygfx.Background(None, self._background_material)
        self.scene.add(self._background)

    def get_figure(self, obj=None):
        """Get Figure instance that contains this plot area"""
        if obj is None:
            obj = self

        if obj.parent.__class__.__name__.endswith("Figure"):
            return obj.parent
        else:
            if obj.parent is None:
                raise RecursionError

            return self.get_figure(obj=obj.parent)

    # several read-only properties
    @property
    def parent(self):
        """A parent if relevant"""
        return self._parent

    @property
    def scene(self) -> pygfx.Scene:
        """The Scene where Graphics lie in this plot area"""
        return self._scene

    @property
    def canvas(self) -> BaseRenderCanvas:
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
    def camera(self, new_camera: str | pygfx.PerspectiveCamera):
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
                raise ValueError(
                    "camera must be one of '2d', '3d' or a pygfx.PerspectiveCamera instance"
                )
        else:
            raise ValueError(
                "camera must be one of '2d', '3d' or a pygfx.PerspectiveCamera instance"
            )

    # in the future we can think about how to allow changing the controller
    @property
    def controller(self) -> pygfx.Controller:
        """controller used to control the camera"""
        return self._controller

    @controller.setter
    def controller(self, new_controller: str | pygfx.Controller):
        new_controller = create_controller(new_controller, self._camera)

        cameras_list = list()

        # remove all the cameras associated to this controller
        for camera in self._controller.cameras:
            self._controller.remove_camera(camera)
            cameras_list.append(camera)

        # add the associated cameras to the new controller
        for camera in cameras_list:
            new_controller.add_camera(camera)

        new_controller.register_events(self.viewport)

        # TODO: monkeypatch until we figure out a better
        #  pygfx plans on refactoring viewports anyways
        if self.parent is not None:
            if self.parent.__class__.__name__.endswith("Figure"):
                for subplot in self.parent:
                    if subplot.camera in cameras_list:
                        new_controller.register_events(subplot.viewport)
                        subplot._controller = new_controller

        self._controller = new_controller

    @property
    def graphics(self) -> tuple[Graphic, ...]:
        """Graphics in the plot area."""
        return tuple(self._graphics)

    @property
    def selectors(self) -> tuple[BaseSelector, ...]:
        """Selectors in the plot area."""
        return tuple(self._selectors)

    @property
    def legends(self) -> tuple[Legend, ...]:
        """Legends in the plot area."""
        return tuple(self._legends)

    @property
    def objects(self) -> tuple[Graphic | BaseSelector | Legend, ...]:
        return *self.graphics, *self.selectors, *self.legends

    @property
    def name(self) -> str:
        """The name of this plot area"""
        return self._name

    @name.setter
    def name(self, name: str):
        if name is None:
            self._name = None
            return

        if not isinstance(name, str):
            raise TypeError("PlotArea `name` must be of type <str>")
        self._name = name

    @property
    def background_color(self) -> tuple[pygfx.Color, ...]:
        """background colors, (top left, top right, bottom right, bottom left)"""
        return (
            self._background_material.color_top_left,
            self._background_material.color_top_right,
            self._background_material.color_bottom_right,
            self._background_material.color_bottom_left,
        )

    @background_color.setter
    def background_color(self, colors: str | tuple[float]):
        """1, 2, or 4 colors, each color must be acceptable by pygfx.Color"""
        self._background_material.set_colors(*colors)

    def map_screen_to_world(
        self, pos: tuple[float, float] | pygfx.PointerEvent, allow_outside: bool = False
    ) -> np.ndarray | None:
        """
        Map screen position to world position

        Parameters
        ----------
        pos: (float, float) | pygfx.PointerEvent
            ``(x, y)`` screen coordinates, or ``pygfx.PointerEvent``

        """
        if isinstance(pos, pygfx.PointerEvent):
            pos = pos.x, pos.y

        if not allow_outside and not self.viewport.is_inside(*pos):
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

    def _render(self):
        self._call_animate_functions(self._animate_funcs_pre)

        # does not flush, flush must be implemented in user-facing Plot objects
        self.viewport.render(self.scene, self.camera)

        for child in self.children:
            child._render()

        self._call_animate_functions(self._animate_funcs_post)

    def _call_animate_functions(self, funcs: list[callable]):
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
        *funcs: callable,
        pre_render: bool = True,
        post_render: bool = False,
    ):
        """
        Add function(s) that are called on every render cycle.
        These are called at the Subplot level.

        Parameters
        ----------
        *funcs: callable(s)
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

    def _sort_images_by_depth(self):
        """
        In general, we want to avoid setting the offset of a graphic, because the
        z-dimension may actually mean something; we cannot know whether the user is
        building a 3D scene or not. We could check whether the 3d dimension of line/point data
        is all zeros, but maybe this is intended, and *other* graphics in the same scene
        may be actually 3D. We could check camera.fov being zero, but maybe the user
        switches to a 3D camera later, or uses a 3D orthographic camera.

        The one exception, kindof, is images, which are inherently 2D, and for which
        layering helps a lot to get things rendered correctly. So we basically layer the
        images, in the order that they were added, pushing older images backwards (away
        from the camera).
        """
        count = 0
        for graphic in self._graphics:
            if isinstance(graphic, ImageGraphic):
                count += 1
                auto_depth = -count
                user_changed_depth = graphic.offset[2] % 1 > 0.0  # i.e. is not integer
                if not user_changed_depth:
                    graphic.offset = (*graphic.offset[:-1], auto_depth)

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
            self._fpl_graphics_scene.add(graphic.world_object)
            return

        self._add_or_insert_graphic(graphic=graphic, center=center, action="add")

        if isinstance(graphic, ImageGraphic):
            self._sort_images_by_depth()

    def insert_graphic(
        self,
        graphic: Graphic,
        center: bool = True,
        index: int = 0,
        auto_offset: int = None,
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

        auto_offset: bool, default True
            If True and using an orthographic projection, sets z-axis offset of graphic to `index`

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

        if isinstance(graphic, ImageGraphic):
            self._sort_images_by_depth()

    def _add_or_insert_graphic(
        self,
        graphic: Graphic,
        center: bool = True,
        action: Literal["insert", "add"] = "add",
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
            obj_list = self._selectors
            self.scene.add(graphic.world_object)

        elif isinstance(graphic, Legend):
            obj_list = self._legends
            self.scene.add(graphic.world_object)

        elif isinstance(graphic, Graphic):
            obj_list = self._graphics
            self._fpl_graphics_scene.add(graphic.world_object)

            # add to tooltip registry
            if self.get_figure().show_tooltips:
                self.get_figure().tooltip_manager.register(graphic)

        else:
            raise TypeError("graphic must be of type Graphic | BaseSelector | Legend")

        if action == "insert":
            obj_list.insert(index, graphic)
        elif action == "add":
            obj_list.append(graphic)
        else:
            raise ValueError("valid actions are 'insert' | 'add'")

        if center:
            self.center_graphic(graphic)

        graphic._fpl_add_plot_area_hook(self)

    def _check_graphic_name_exists(self, name):
        if name in self:
            raise ValueError(
                f"Graphic with given name already exists in subplot or plot area. "
                f"All graphics within a subplot or plot area must have a unique name."
            )

    def center_graphic(self, graphic: Graphic, zoom: float = 1.0):
        """
        Center the camera w.r.t. the passed graphic

        Parameters
        ----------
        graphic: Graphic
            The graphic instance to center on

        zoom: float
            zoom the camera after centering

        """

        self.camera.show_object(graphic.world_object)

        # camera.show_object can cause the camera width and height to increase so apply a zoom to compensate
        # probably because camera.show_object uses bounding sphere
        self.camera.zoom = zoom

    def center_scene(self, *, zoom: float = 1.0):
        """
        Auto-center the scene, does not scale.

        Parameters
        ----------
        zoom: float
            apply a zoom after centering the scene

        """

        if not len(self._fpl_graphics_scene.children) > 0:
            return

        # scale all cameras associated with this controller
        # else it looks wonky
        for camera in self.controller.cameras:
            camera.show_object(self._fpl_graphics_scene)

            # camera.show_object can cause the camera width and height to increase so apply a zoom to compensate
            # probably because camera.show_object uses bounding sphere
            camera.zoom = zoom

    def auto_scale(
        self,
        *,  # since this is often used as an event handler, don't want to coerce maintain_aspect = True
        maintain_aspect: None | bool = None,
        zoom: float = 0.75,
    ):
        """
        Auto-scale the camera w.r.t to the scene

        Parameters
        ----------
        maintain_aspect: ``None`` or bool, default ``None``
            Maintain the camera aspect ratio for all dimensions. If ``None``, the aspect is left unchanged.
            if ``False`` the camera is scaled to the bounding box of the current scene.

        zoom: float
            zoom value for the camera after auto-scaling

        """

        if not len(self._fpl_graphics_scene.children) > 0:
            return

        self.center_scene()

        if maintain_aspect is None:  # if not provided keep current setting
            maintain_aspect = self.camera.maintain_aspect

        # scale all cameras associated with this controller else it looks wonky
        for camera in self.controller.cameras:
            camera.maintain_aspect = maintain_aspect

        if len(self._fpl_graphics_scene.children) > 0:
            width, height, depth = np.ptp(
                self._fpl_graphics_scene.get_world_bounding_box(), axis=0
            )
        else:
            width, height, depth = (1, 1, 1)

        # make sure width and height are non-zero
        if width < 0.01:
            width = 1
        if height < 0.01:
            height = 1

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

        if isinstance(graphic, (BaseSelector, Legend)):
            self.scene.remove(graphic.world_object)

        elif isinstance(graphic, Graphic):
            self._fpl_graphics_scene.remove(graphic.world_object)

    def delete_graphic(self, graphic: Graphic):
        """
        Delete the graphic, garbage collects and frees GPU VRAM.

        Parameters
        ----------
        graphic: Graphic
            The graphic to delete

        """
        if graphic not in self:
            raise KeyError(f"Graphic not found in plot area: {graphic}")

        if isinstance(graphic, BaseSelector):
            self._selectors.remove(graphic)

        elif isinstance(graphic, Legend):
            self._legends.remove(graphic)

        elif isinstance(graphic, Graphic):
            self._graphics.remove(graphic)

        # remove from scene if necessary
        if graphic.world_object in self.scene.children:
            self.scene.remove(graphic.world_object)

        elif graphic.world_object in self._fpl_graphics_scene.children:
            self._fpl_graphics_scene.remove(graphic.world_object)

        # cleanup
        graphic._fpl_prepare_del()

        if IS_IPYTHON:
            # remove any references that ipython might have made
            # check both namespaces
            for namespace in [IPYTHON.user_ns, IPYTHON.user_ns_hidden]:
                # find the reference
                for ref, obj in namespace.items():
                    if graphic is obj:
                        # we found the reference, remove from ipython
                        IPYTHON.del_var(ref)
                        break

    def clear(self):
        """
        Clear the Plot or Subplot. Also performs garbage collection, i.e. runs ``delete_graphic`` on all graphics.
        """
        for g in self.objects:
            self.delete_graphic(g)

    def __getitem__(self, name: str):
        for graphic in self.objects:
            if graphic.name == name:
                return graphic

        raise IndexError(f"No graphic or selector of given name in plot area.\n")

    def __contains__(self, item: str | Graphic):
        if isinstance(item, Graphic):
            if item in self.objects:
                return True
            else:
                return False

        elif isinstance(item, str):
            for graphic in self.objects:
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

        return f"{name}: {self.__class__.__name__}"

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
