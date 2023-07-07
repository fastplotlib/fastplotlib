from typing import *
from inspect import getfullargspec
from warnings import warn

import numpy as np

import pygfx
from pygfx import (
    Scene,
    OrthographicCamera,
    PanZoomController,
    OrbitController,
    AxesHelper,
    GridHelper,
    WgpuRenderer,
    Texture,
)
from wgpu.gui.auto import WgpuCanvas

from ..graphics import TextGraphic
from ._utils import make_canvas_and_renderer
from ._base import PlotArea
from ._defaults import create_camera, create_controller
from .graphic_methods_mixin import GraphicMethodsMixin


class Subplot(PlotArea, GraphicMethodsMixin):
    def __init__(
        self,
        parent: Any = None,
        position: Tuple[int, int] = None,
        parent_dims: Tuple[int, int] = None,
        camera: str = "2d",
        controller: Union[pygfx.Controller] = None,
        canvas: Union[str, WgpuCanvas, Texture] = None,
        renderer: WgpuRenderer = None,
        name: str = None,
        **kwargs,
    ):
        """
        General plot object that composes a ``Gridplot``. Each ``Gridplot`` instance will have [n rows, n columns]
        of subplots.

        .. important::
            ``Subplot`` is not meant to be constructed directly, it only exists as part of a ``GridPlot``

        Parameters
        ----------
        position: int tuple, optional
            corresponds to the [row, column] position of the subplot within a ``Gridplot``

        parent_dims: int tuple, optional
            dimensions of the parent ``GridPlot``

        camera: str, default '2d'
            indicates the kind of pygfx camera that will be instantiated, '2d' uses pygfx ``OrthographicCamera`` and
            '3d' uses pygfx ``PerspectiveCamera``

        controller: None, str, or a pygfx controller
            | if ``None``, uses a PanZoomController for "2d" camera or FlyController for "3d" camera.
            | if ``str``, must be one of: `"panzoom", "fly", "trackball", or "orbit"`.
            | also accepts a pygfx.Controller instance

        canvas: WgpuCanvas, Texture, or one of "jupyter", "glfw", "qt", optional
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

        # parse camera and controller
        camera = create_camera(camera)
        controller = create_controller(camera, controller)

        self._docks = dict()

        self.spacing = 2

        self._axes: AxesHelper = AxesHelper(size=100)
        for arrow in self._axes.children:
            self._axes.remove(arrow)

        self._grid: GridHelper = GridHelper(size=100, thickness=1)

        self._animate_funcs_pre = list()
        self._animate_funcs_post = list()

        super(Subplot, self).__init__(
            parent=parent,
            position=position,
            camera=create_camera(camera),
            controller=controller,
            scene=Scene(),
            canvas=canvas,
            renderer=renderer,
            name=name,
        )

        for pos in ["left", "top", "right", "bottom"]:
            dv = Dock(self, pos, size=0)
            dv.name = pos
            self.docks[pos] = dv
            self.children.append(dv)

        self._title_graphic: TextGraphic = None
        if self.name is not None:
            self.set_title(self.name)

    @property
    def name(self) -> Any:
        return self._name

    @name.setter
    def name(self, name: Any):
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

    def set_title(self, text: Any):
        """Sets the plot title, stored as a ``TextGraphic`` in the "top" dock area"""
        if text is None:
            return

        text = str(text)
        if self._title_graphic is not None:
            self._title_graphic.update_text(text)
        else:
            tg = TextGraphic(text)
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
        width_canvas, height_canvas = self.renderer.logical_size

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

    def render(self):
        self._call_animate_functions(self._animate_funcs_pre)

        super(Subplot, self).render()

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

    def set_axes_visibility(self, visible: bool):
        """Toggles axes visibility."""
        if visible:
            self.scene.add(self._axes)
        else:
            self.scene.remove(self._axes)

    def set_grid_visibility(self, visible: bool):
        """Toggles grid visibility."""
        if visible:
            self.scene.add(self._grid)
        else:
            self.scene.remove(self._grid)


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

        super(Dock, self).__init__(
            parent=parent,
            position=position,
            camera=OrthographicCamera(),
            controller=PanZoomController(),
            scene=Scene(),
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

        super(Dock, self).render()
