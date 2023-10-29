from itertools import product
import numpy as np
from typing import *
from inspect import getfullargspec
from warnings import warn

import pygfx

from wgpu.gui.auto import WgpuCanvas

from ._frame import Frame
from ._utils import make_canvas_and_renderer
from ._defaults import create_controller
from ._subplot import Subplot
from ._record_mixin import RecordMixin


def to_array(a) -> np.ndarray:
    if isinstance(a, np.ndarray):
        return a

    if not isinstance(a, list):
        raise TypeError("must pass list or numpy array")

    return np.array(a)


valid_cameras = ["2d", "2d-big", "3d", "3d-big"]


class GridPlot(Frame, RecordMixin):
    def __init__(
        self,
        shape: Tuple[int, int],
        cameras: Union[np.ndarray, str] = "2d",
        controllers: Union[np.ndarray, str] = None,
        canvas: Union[str, WgpuCanvas, pygfx.Texture] = None,
        renderer: pygfx.WgpuRenderer = None,
        size: Tuple[int, int] = (500, 300),
        **kwargs,
    ):
        """
        A grid of subplots.

        Parameters
        ----------
        shape: tuple of int
            (n_rows, n_cols)

        cameras: np.ndarray or str, optional
            | One of ``"2d"`` or ``"3d"`` indicating 2D or 3D cameras for all subplots
            | OR
            | Array of ``2d`` and/or ``3d`` that specifies the camera type for each subplot

        controllers: np.ndarray or str, optional
            | If `None` a unique controller is created for each subplot
            | If "sync" all the subplots use the same controller
            | If ``numpy.array``, its shape must be the same as ``grid_shape``.

            This allows custom assignment of controllers

            | Example:
            | unique controllers for a 2x2 gridplot: np.array([[0, 1], [2, 3]])
            | same controllers for first 2 plots and last 2 plots: np.array([[0, 0, 1], [2, 3, 3]])

        canvas: WgpuCanvas, optional
            Canvas for drawing

        renderer: pygfx.Renderer, optional
            pygfx renderer instance

        size: (int, int)
            starting size of canvas, default (500, 300)

        """

        self.shape = shape

        canvas, renderer = make_canvas_and_renderer(canvas, renderer)

        if isinstance(cameras, str):
            if cameras not in valid_cameras:
                raise ValueError(
                    f"If passing a str, `cameras` must be one of: {valid_cameras}"
                )
            # create the array representing the views for each subplot in the grid
            cameras = np.array([cameras] * self.shape[0] * self.shape[1]).reshape(
                self.shape
            )

        if isinstance(controllers, str):
            if controllers == "sync":
                controllers = np.zeros(
                    self.shape[0] * self.shape[1], dtype=int
                ).reshape(self.shape)

        if controllers is None:
            controllers = np.arange(self.shape[0] * self.shape[1]).reshape(self.shape)

        controllers = to_array(controllers)

        if controllers.shape != self.shape:
            raise ValueError

        cameras = to_array(cameras)

        self._controllers = np.empty(shape=cameras.shape, dtype=object)

        if cameras.shape != self.shape:
            raise ValueError

        # create controllers if the arguments were integers
        if np.issubdtype(controllers.dtype, np.integer):
            if not np.all(
                np.sort(np.unique(controllers))
                == np.arange(np.unique(controllers).size)
            ):
                raise ValueError("controllers must be consecutive integers")

            for controller in np.unique(controllers):
                cam = np.unique(cameras[controllers == controller])
                if cam.size > 1:
                    raise ValueError(
                        f"Controller id: {controller} has been assigned to multiple different camera types"
                    )

                self._controllers[controllers == controller] = create_controller(cam[0])
        # else assume it's a single pygfx.Controller instance or a list of controllers
        else:
            if isinstance(controllers, pygfx.Controller):
                self._controllers = np.array(
                    [controllers] * shape[0] * shape[1]
                ).reshape(shape)
            else:
                self._controllers = np.array(controllers).reshape(shape)

        if canvas is None:
            canvas = WgpuCanvas()

        if renderer is None:
            renderer = pygfx.renderers.WgpuRenderer(canvas)

        if "names" in kwargs.keys():
            self.names = to_array(kwargs["names"])
            if self.names.shape != self.shape:
                raise ValueError
        else:
            self.names = None

        self._canvas = canvas
        self._renderer = renderer

        nrows, ncols = self.shape

        self._subplots: np.ndarray[Subplot] = np.ndarray(
            shape=(nrows, ncols), dtype=object
        )

        for i, j in self._get_iterator():
            position = (i, j)
            camera = cameras[i, j]
            controller = self._controllers[i, j]

            if self.names is not None:
                name = self.names[i, j]
            else:
                name = None

            self._subplots[i, j] = Subplot(
                parent=self,
                position=position,
                parent_dims=(nrows, ncols),
                camera=camera,
                controller=controller,
                canvas=canvas,
                renderer=renderer,
                name=name,
            )

        self._animate_funcs_pre: List[callable] = list()
        self._animate_funcs_post: List[callable] = list()

        self._current_iter = None

        self._starting_size = size

        RecordMixin.__init__(self)
        Frame.__init__(self)

    @property
    def canvas(self) -> WgpuCanvas:
        """The canvas associated to this GridPlot"""
        return self._canvas

    @property
    def renderer(self) -> pygfx.WgpuRenderer:
        """The renderer associated to this GridPlot"""
        return self._renderer

    def __getitem__(self, index: Union[Tuple[int, int], str]) -> Subplot:
        if isinstance(index, str):
            for subplot in self._subplots.ravel():
                if subplot.name == index:
                    return subplot
            raise IndexError("no subplot with given name")
        else:
            return self._subplots[index[0], index[1]]

    def render(self):
        # call the animation functions before render
        self._call_animate_functions(self._animate_funcs_pre)

        for subplot in self:
            subplot.render()

        self.renderer.flush()
        self.canvas.request_draw()

        # call post-render animate functions
        self._call_animate_functions(self._animate_funcs_post)

    def _call_animate_functions(self, funcs: Iterable[callable]):
        for fn in funcs:
            try:
                if len(getfullargspec(fn).args) > 0:
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
        These are called at the GridPlot level.

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

    def clear(self):
        """Clear all Subplots"""
        for subplot in self:
            subplot.clear()

    def _get_iterator(self):
        return product(range(self.shape[0]), range(self.shape[1]))

    def __iter__(self):
        self._current_iter = self._get_iterator()
        return self

    def __next__(self) -> Subplot:
        pos = self._current_iter.__next__()
        return self._subplots[pos]

    def __repr__(self):
        return f"fastplotlib.{self.__class__.__name__} @ {hex(id(self))}\n"
