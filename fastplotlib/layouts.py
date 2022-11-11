from itertools import product
import numpy as np
import pygfx
from .defaults import create_controller
from .subplot import Subplot
from typing import *
from wgpu.gui.auto import WgpuCanvas
from ipywidgets import GridspecLayout, Textarea


def to_array(a) -> np.ndarray:
    if isinstance(a, np.ndarray):
        return a

    if not isinstance(a, list):
        raise TypeError("must pass list or numpy array")

    return np.array(a)


valid_cameras = ["2d", "2d-big", "3d", "3d-big"]


class GridPlot:
    def __init__(
            self,
            shape: Tuple[int, int],
            cameras: Union[np.ndarray, str] = '2d',
            controllers: Union[np.ndarray, str] = None,
            canvas: WgpuCanvas = None,
            renderer: pygfx.Renderer = None,
            **kwargs
    ):
        """
        Parameters
        ----------
        shape:
            nrows, ncols

        cameras: Union[np.ndarray, str]
            One of ``"2d"`` or ``"3d"`` indicating 2D or 3D plots

            OR

            Array of ``2d`` and/or ``3d`` that specifies camera type for each subplot:
            ``2d``: ``pygfx.OrthographicCamera``
            ``3d``: ``pygfx.PerspectiveCamera``

        controllers: np.ndarray
            numpy array of same shape as ``grid_shape`` that defines the controllers
            Example:
            unique controllers for a 2x2 gridplot: np.array([[0, 1], [2, 3]])
            same controllers for first 2 plots: np.array([[0, 0, 1], [2, 3, 4]])

            If `None` a unique controller is created for each subplot

            If "sync" all the subplots use the same controller

        canvas: WgpuCanvas
            Canvas for drawing

        renderer: pygfx.Renderer
            pygfx renderer instance
        """
        self.shape = shape

        if type(cameras) is str:
            if cameras not in valid_cameras:
                raise ValueError(f"If passing a str, `cameras` must be one of: {valid_cameras}")
            # create the array representing the views for each subplot in the grid
            cameras = np.array([cameras] * self.shape[0] * self.shape[1]).reshape(self.shape)

        if controllers == "sync":
            controllers = np.zeros(self.shape[0] * self.shape[1], dtype=int).reshape(self.shape)

        if controllers is None:
            controllers = np.arange(self.shape[0] * self.shape[1]).reshape(self.shape)

        controllers = to_array(controllers)

        if controllers.shape != self.shape:
            raise ValueError

        cameras = to_array(cameras)

        if cameras.shape != self.shape:
            raise ValueError

        if not np.all(np.sort(np.unique(controllers)) == np.arange(np.unique(controllers).size)):
            raise ValueError("controllers must be consecutive integers")

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

        self.canvas = canvas
        self.renderer = renderer

        nrows, ncols = self.shape

        self._subplots: np.ndarray[Subplot] = np.ndarray(shape=(nrows, ncols), dtype=object)
        # self.viewports: np.ndarray[Subplot] = np.ndarray(shape=(nrows, ncols), dtype=object)

        self._controllers: List[pygfx.PanZoomController] = [
            pygfx.PanZoomController() for i in range(np.unique(controllers).size)
        ]

        self._controllers = np.empty(shape=cameras.shape, dtype=object)

        for controller in np.unique(controllers):
            cam = np.unique(cameras[controllers == controller])
            if cam.size > 1:
                raise ValueError(f"Controller id: {controller} has been assigned to multiple different camera types")

            self._controllers[controllers == controller] = create_controller(cam[0])

        for i, j in self._get_iterator():
            position = (i, j)
            camera = cameras[i, j]
            controller = self._controllers[i, j]

            if self.names is not None:
                name = self.names[i, j]
            else:
                name = None

            self._subplots[i, j] = Subplot(
                position=position,
                parent_dims=(nrows, ncols),
                camera=camera,
                controller=controller,
                canvas=canvas,
                renderer=renderer,
                name=name
            )

        self._animate_funcs: List[callable] = list()
        self._current_iter = None

    def __getitem__(self, index: Union[Tuple[int, int], str]):
        if type(index) == str:
            for subplot in self._subplots.ravel():
                if subplot.name == index:
                    return subplot
            raise IndexError("no subplot with given name")
        else:
            return self._subplots[index[0], index[1]]

    def animate(self):
        for subplot in self:
            subplot.animate(self.canvas.get_logical_size())

        for f in self._animate_funcs:
            f()

        self.renderer.flush()
        self.canvas.request_draw()

    def add_animations(self, funcs: List[callable]):
        self._animate_funcs += funcs

    def show(self):
        self.canvas.request_draw(self.animate)

        for subplot in self:
            subplot.center_scene()

        return self.canvas

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



