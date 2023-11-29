from itertools import product, chain
import numpy as np
from typing import *
from inspect import getfullargspec
from warnings import warn

import pygfx

from wgpu.gui.auto import WgpuCanvas

from ._frame import Frame
from ._utils import make_canvas_and_renderer, create_controller, create_camera
from ._utils import controller_types as valid_controller_types
from ._subplot import Subplot
from ._record_mixin import RecordMixin


def to_array(a) -> np.ndarray:
    if isinstance(a, np.ndarray):
        return a

    if not isinstance(a, list):
        raise TypeError("must pass list or numpy array")

    return np.array(a)


class GridPlot(Frame, RecordMixin):
    def __init__(
        self,
        shape: Tuple[int, int],
        cameras: Union[str, list, np.ndarray] = "2d",
        controller_types: Union[str, list, np.ndarray] = None,
        controller_ids: Union[str, list, np.ndarray] = None,
        canvas: Union[str, WgpuCanvas, pygfx.Texture] = None,
        renderer: pygfx.WgpuRenderer = None,
        size: Tuple[int, int] = (500, 300),
        names: Union[list, np.ndarray] = None,
    ):
        """
        A grid of subplots.

        Parameters
        ----------
        shape: (int, int)
            (n_rows, n_cols)

        cameras: str, list, or np.ndarray, optional
            | One of ``"2d"`` or ``"3d"`` indicating 2D or 3D cameras for all subplots
            | list/array of ``2d`` and/or ``3d`` that specifies the camera type for each subplot
            | list/array of pygfx.PerspectiveCamera instances

        controller_types: str, list or np.ndarray, optional
            list or array that specifies the controller type for each subplot, or list/array of
            pygfx.Controller instances

        controller_ids: str, list or np.ndarray of int or str ids, optional
            | If `None` a unique controller is created for each subplot
            | If "sync" all the subplots use the same controller
            | If ``numpy.array``, its shape must be the same as ``grid_shape``.

            This allows custom assignment of controllers

            | Example with integers:
            | sync first 2 plots, and sync last 2 plots: [[0, 0, 1], [2, 3, 3]]
            | Example with str subplot names:
            | list of lists of subplot names, each sublist is synced: [[subplot_a, subplot_b], [subplot_f, subplot_c]]
            | this syncs subplot_a and subplot_b together; syncs subplot_f and subplot_c together

        canvas: WgpuCanvas, optional
            Canvas for drawing

        renderer: pygfx.Renderer, optional
            pygfx renderer instance

        size: (int, int), optional
            starting size of canvas, default (500, 300)

        names: list or array of str, optional
            subplot names
        """

        self.shape = shape

        if names is not None:
            if len(list(chain(*names))) != self.shape[0] * self.shape[1]:
                raise ValueError("must provide same number of subplot `names` as specified by gridplot shape")

            self.names = to_array(names).reshape(self.shape)
        else:
            self.names = None

        canvas, renderer = make_canvas_and_renderer(canvas, renderer)

        if isinstance(cameras, str):
            # create the array representing the views for each subplot in the grid
            cameras = np.array([cameras] * self.shape[0] * self.shape[1]).reshape(
                self.shape
            )

        # list -> array if necessary
        cameras = to_array(cameras).reshape(self.shape)

        if cameras.shape != self.shape:
            raise ValueError("Number of cameras does not match the number of subplots")

        # create the cameras
        self._cameras = np.empty(self.shape, dtype=object)
        for i, j in product(range(self.shape[0]), range(self.shape[1])):
            self._cameras[i, j] = create_camera(camera_type=cameras[i, j])

        if controller_ids is None:
            # individual controller for each subplot
            controller_ids = np.arange(self.shape[0] * self.shape[1]).reshape(self.shape)

        elif isinstance(controller_ids, str):
            if controller_ids == "sync":
                controller_ids = np.zeros(self.shape, dtype=int)
            else:
                raise ValueError(
                    f"`controller_ids` must be one of 'sync', an array/list of subplot names, or an array/list of "
                    f"integer ids. See the docstring for more details."
                )

        # list controller_ids
        elif isinstance(controller_ids, (list, np.ndarray)):
            flat = list(chain(*controller_ids))

            # list of str of subplot names, convert this to integer ids
            if all([isinstance(item, str) for item in flat]):
                if self.names is None:
                    raise ValueError("must specify subplot `names` to use list of str for `controller_ids`")

                # make sure each controller_id str is a subplot name
                if not all([n in self.names for n in flat]):
                    raise KeyError(
                        f"all `controller_ids` strings must be one of the subplot names"
                    )

                if len(flat) > len(set(flat)):
                    raise ValueError(
                        "id strings must not appear twice in `controller_ids`"
                    )

                # initialize controller_ids array
                ids_init = np.arange(self.shape[0] * self.shape[1]).reshape(self.shape)

                # set id based on subplot position for each synced sublist
                for i, sublist in enumerate(controller_ids):
                    for name in sublist:
                        ids_init[self.names == name] = -(i + 1)  # use negative numbers because why not

                controller_ids = ids_init

            # integer ids
            elif all([isinstance(item, (int, np.integer)) for item in flat]):
                controller_ids = to_array(controller_ids).reshape(self.shape)

            else:
                raise TypeError(
                    f"list argument to `controller_ids` must be a list of `str` or `int`, "
                    f"you have passed: {controller_ids}"
                )

        if controller_ids.shape != self.shape:
            raise ValueError("Number of controller_ids does not match the number of subplots")

        if controller_types is None:
            # `create_controller()` will auto-determine controller for each subplot based on defaults
            controller_types = np.array(["default"] * self.shape[0] * self.shape[1]).reshape(self.shape)

        # validate controller types
        flat = list(chain(*controller_types))
        # str controller_type or pygfx instances
        valid_str = list(valid_controller_types.keys()) + ["default"]
        valid_instances = tuple(valid_controller_types.values())

        # make sure each controller type is valid
        for controller_type in flat:
            if controller_type is None:
                continue

            if (controller_type not in valid_str) and (not isinstance(controller_type, valid_instances)):
                raise ValueError(
                    f"You have passed an invalid controller type, valid controller_types arguments are:\n"
                    f"{valid_str} or instances of {[c.__name__ for c in valid_instances]}"
                )

        controller_types = to_array(controller_types).reshape(self.shape)

        # make the real controllers for each subplot
        self._controllers = np.empty(shape=self.shape, dtype=object)
        for cid in np.unique(controller_ids):
            cont_type = controller_types[controller_ids == cid]
            if np.unique(cont_type).size > 1:
                raise ValueError(
                    "Multiple controller types have been assigned to the same controller id. "
                    "All controllers with the same id must use the same type of controller."
                )

            cont_type = cont_type[0]

            # get all the cameras that use this controller
            cams = self._cameras[controller_ids == cid].ravel()

            if cont_type == "default":
                # hacky fix for now because of how `create_controller()` works
                cont_type = None
            _controller = create_controller(controller_type=cont_type, camera=cams[0])

            self._controllers[controller_ids == cid] = _controller

            # add the other cameras that go with this controller
            if cams.size > 1:
                for cam in cams[1:]:
                    _controller.add_camera(cam)

        if canvas is None:
            canvas = WgpuCanvas()

        if renderer is None:
            renderer = pygfx.renderers.WgpuRenderer(canvas)

        self._canvas = canvas
        self._renderer = renderer

        nrows, ncols = self.shape

        self._subplots: np.ndarray[Subplot] = np.ndarray(
            shape=(nrows, ncols), dtype=object
        )

        for i, j in self._get_iterator():
            position = (i, j)
            camera = self._cameras[i, j]
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

    def __str__(self):
        return f"{self.__class__.__name__} @ {hex(id(self))}"

    def __repr__(self):
        newline = "\n\t"

        return (
            f"fastplotlib.{self.__class__.__name__} @ {hex(id(self))}\n"
            f"  Subplots:\n"
            f"\t{newline.join(subplot.__str__() for subplot in self)}"
            f"\n"
        )
