import os
from itertools import product, chain
from multiprocessing import Queue
from pathlib import Path
from time import time

import numpy as np
from typing import Literal, Iterable
from inspect import getfullargspec
from warnings import warn

import pygfx

from wgpu.gui import WgpuCanvasBase
from wgpu.gui.base import log_exception

from ._video_writer import VideoWriterAV
from ._utils import make_canvas_and_renderer, create_controller, create_camera
from ._utils import controller_types as valid_controller_types
from ._subplot import Subplot
from .. import ImageGraphic


class Figure:
    def __init__(
        self,
        shape: tuple[int, int] = (1, 1),
        cameras: (
            Literal["2d", "3d"]
            | Iterable[Iterable[Literal["2d", "3d"]]]
            | pygfx.PerspectiveCamera
            | Iterable[Iterable[pygfx.PerspectiveCamera]]
        ) = "2d",
        controller_types: (
            Iterable[Iterable[Literal["panzoom", "fly", "trackball", "orbit"]]]
            | Iterable[Literal["panzoom", "fly", "trackball", "orbit"]]
        ) = None,
        controller_ids: (
            Literal["sync"]
            | Iterable[int]
            | Iterable[Iterable[int]]
            | Iterable[Iterable[str]]
        ) = None,
        controllers: pygfx.Controller | Iterable[Iterable[pygfx.Controller]] = None,
        canvas: str | WgpuCanvasBase | pygfx.Texture = None,
        renderer: pygfx.WgpuRenderer = None,
        size: tuple[int, int] = (500, 300),
        names: list | np.ndarray = None,
    ):
        """
        A grid of subplots.

        Parameters
        ----------
        shape: (int, int), default (1, 1)
            (n_rows, n_cols)

        cameras: "2d", "3", list of "2d" | "3d", Iterable of camera instances, or Iterable of "2d" | "3d", optional
            | if str, one of ``"2d"`` or ``"3d"`` indicating 2D or 3D cameras for all subplots
            | Iterable/list/array of ``2d`` and/or ``3d`` that specifies the camera type for each subplot
            | Iterable/list/array of pygfx.PerspectiveCamera instances

        controller_types: str, Iterable, optional
            list/array that specifies the controller type for each subplot.
            Valid controller types: "panzoom", "fly", "trackball", "orbit".
            If not specified a default controller is chosen based on the camera type.
            Orthographic projections, i.e. "2d" cameras, use a "panzoom" controller by default.
            Perspective projections with a FOV > 0, i.e. "3d" cameras, use a "fly" controller by default.

        controller_ids: str, list of int, np.ndarray of int, or list with sublists of subplot str names, optional
            | If `None` a unique controller is created for each subplot
            | If "sync" all the subplots use the same controller
            | If array/list it must be reshapeable to ``grid_shape``.

            This allows custom assignment of controllers

            | Example with integers:
            | sync first 2 plots, and sync last 2 plots: [[0, 0, 1], [2, 3, 3]]
            | Example with str subplot names:
            | list of lists of subplot names, each sublist is synced: [[subplot_a, subplot_b, subplot_e], [subplot_c, subplot_d]]
            | this syncs subplot_a, subplot_b and subplot_e together; syncs subplot_c and subplot_d together

        controllers: pygfx.Controller | list[pygfx.Controller] | np.ndarray[pygfx.Controller], optional
            directly provide pygfx.Controller instances(s). Useful if you want to use a controller from an existing
            plot/subplot. Other controller kwargs, i.e. ``controller_types`` and ``controller_ids`` are ignored if
            ``controllers`` are provided.

        canvas: WgpuCanvas, optional
            Canvas for drawing

        renderer: pygfx.Renderer, optional
            pygfx renderer instance

        size: (int, int), optional
            starting size of canvas, default (500, 300)

        names: list or array of str, optional
            subplot names
        """

        self._shape = shape

        if names is not None:
            if len(list(chain(*names))) != len(self):
                raise ValueError(
                    "must provide same number of subplot `names` as specified by Figure `shape`"
                )

            subplot_names = np.asarray(names).reshape(self.shape)
        else:
            subplot_names = None

        canvas, renderer = make_canvas_and_renderer(canvas, renderer)

        if isinstance(cameras, str):
            # create the array representing the views for each subplot in the grid
            cameras = np.array([cameras] * len(self)).reshape(self.shape)

        # list -> array if necessary
        cameras = np.asarray(cameras).reshape(self.shape)

        if cameras.shape != self.shape:
            raise ValueError("Number of cameras does not match the number of subplots")

        # create the cameras
        subplot_cameras = np.empty(self.shape, dtype=object)
        for i, j in product(range(self.shape[0]), range(self.shape[1])):
            subplot_cameras[i, j] = create_camera(camera_type=cameras[i, j])

        # if controller instances have been specified for each subplot
        if controllers is not None:

            # one controller for all subplots
            if isinstance(controllers, pygfx.Controller):
                controllers = [controllers] * len(self)
                # subplot_controllers[:] = controllers
                # # subplot_controllers = np.asarray([controllers] * len(self), dtype=object)

            # individual controller instance specified for each subplot
            else:
                # I found that this is better than list(*chain(<list/array>)) because chain doesn't give the right
                # result we want for arrays
                for item in controllers:
                    if isinstance(item, pygfx.Controller):
                        pass
                    elif all(isinstance(c, pygfx.Controller) for c in item):
                        pass
                    else:
                        raise TypeError(
                            "controllers argument must be a single pygfx.Controller instance, or a Iterable of "
                            "pygfx.Controller instances"
                        )

            try:
                controllers = np.asarray(controllers).reshape(shape)
            except ValueError:
                raise ValueError(
                    f"number of controllers passed must be the same as the number of subplots specified "
                    f"by shape: {self.shape}. You have passed: <{controllers.size}> controllers"
                ) from None

            subplot_controllers: np.ndarray[pygfx.Controller] = np.empty(
                self.shape, dtype=object
            )

            for i, j in product(range(self.shape[0]), range(self.shape[1])):
                subplot_controllers[i, j] = controllers[i, j]
                subplot_controllers[i, j].add_camera(subplot_cameras[i, j])

        # parse controller_ids and controller_types to make desired controller for each supblot
        else:
            if controller_ids is None:
                # individual controller for each subplot
                controller_ids = np.arange(len(self)).reshape(self.shape)

            elif isinstance(controller_ids, str):
                if controller_ids == "sync":
                    # this will eventually make one controller for all subplots
                    controller_ids = np.zeros(self.shape, dtype=int)
                else:
                    raise ValueError(
                        f"`controller_ids` must be one of 'sync', an array/list of subplot names, or an array/list of "
                        f"integer ids. See the docstring for more details."
                    )

            # list controller_ids
            elif isinstance(controller_ids, (list, np.ndarray)):
                ids_flat = list(chain(*controller_ids))

                # list of str of subplot names, convert this to integer ids
                if all([isinstance(item, str) for item in ids_flat]):
                    if subplot_names is None:
                        raise ValueError(
                            "must specify subplot `names` to use list of str for `controller_ids`"
                        )

                    # make sure each controller_id str is a subplot name
                    if not all([n in subplot_names for n in ids_flat]):
                        raise KeyError(
                            f"all `controller_ids` strings must be one of the subplot names"
                        )

                    if len(ids_flat) > len(set(ids_flat)):
                        raise ValueError(
                            "id strings must not appear twice in `controller_ids`"
                        )

                    # initialize controller_ids array
                    ids_init = np.arange(len(self)).reshape(self.shape)

                    # set id based on subplot position for each synced sublist
                    for i, sublist in enumerate(controller_ids):
                        for name in sublist:
                            ids_init[subplot_names == name] = -(
                                i + 1
                            )  # use negative numbers because why not

                    controller_ids = ids_init

                # integer ids
                elif all([isinstance(item, (int, np.integer)) for item in ids_flat]):
                    controller_ids = np.asarray(controller_ids).reshape(self.shape)

                else:
                    raise TypeError(
                        f"list argument to `controller_ids` must be a list of `str` or `int`, "
                        f"you have passed: {controller_ids}"
                    )

            if controller_ids.shape != self.shape:
                raise ValueError(
                    "Number of controller_ids does not match the number of subplots"
                )

            if controller_types is None:
                # `create_controller()` will auto-determine controller for each subplot based on defaults
                controller_types = np.array(["default"] * len(self)).reshape(self.shape)

            # valid controller types
            if isinstance(controller_types, str):
                controller_types = [[controller_types]]

            types_flat = list(chain(*controller_types))
            # str controller_type or pygfx instances
            valid_str = list(valid_controller_types.keys()) + ["default"]

            # make sure each controller type is valid
            for controller_type in types_flat:
                if controller_type is None:
                    continue

                if controller_type not in valid_str:
                    raise ValueError(
                        f"You have passed the invalid `controller_type`: {controller_type}. "
                        f"Valid `controller_types` arguments are:\n {valid_str}"
                    )

            controller_types: np.ndarray[pygfx.Controller] = np.asarray(
                controller_types
            ).reshape(self.shape)

            # make the real controllers for each subplot
            subplot_controllers = np.empty(shape=self.shape, dtype=object)
            for cid in np.unique(controller_ids):
                cont_type = controller_types[controller_ids == cid]
                if np.unique(cont_type).size > 1:
                    raise ValueError(
                        "Multiple controller types have been assigned to the same controller id. "
                        "All controllers with the same id must use the same type of controller."
                    )

                cont_type = cont_type[0]

                # get all the cameras that use this controller
                cams = subplot_cameras[controller_ids == cid].ravel()

                if cont_type == "default":
                    # hacky fix for now because of how `create_controller()` works
                    cont_type = None
                _controller = create_controller(
                    controller_type=cont_type, camera=cams[0]
                )

                subplot_controllers[controller_ids == cid] = _controller

                # add the other cameras that go with this controller
                if cams.size > 1:
                    for cam in cams[1:]:
                        _controller.add_camera(cam)

        self._canvas = canvas
        self._renderer = renderer

        nrows, ncols = self.shape

        self._subplots: np.ndarray[Subplot] = np.ndarray(
            shape=(nrows, ncols), dtype=object
        )

        for i, j in self._get_iterator():
            position = (i, j)
            camera = subplot_cameras[i, j]
            controller = subplot_controllers[i, j]

            if subplot_names is not None:
                name = subplot_names[i, j]
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

        self._animate_funcs_pre: list[callable] = list()
        self._animate_funcs_post: list[callable] = list()

        self._current_iter = None

        self._starting_size = size

        self._output = None

        if self.canvas.__class__.__name__ == "JupyterWgpuCanvas":
            self.recorder = FigureRecorder(self)
        else:
            self.recorder = None

    @property
    def toolbar(self):
        """ipywidget or QToolbar instance"""
        return self._output.toolbar

    @property
    def output(self):
        """ipywidget or QWidget that contains this plot"""
        return self._output

    @property
    def shape(self) -> tuple[int, int]:
        """[n_rows, n_cols]"""
        return self._shape

    @property
    def canvas(self) -> WgpuCanvasBase:
        """The canvas associated to this Figure"""
        return self._canvas

    @property
    def renderer(self) -> pygfx.WgpuRenderer:
        """The renderer associated to this Figure"""
        return self._renderer

    @property
    def controllers(self) -> np.ndarray[pygfx.Controller]:
        """controllers, read-only array, access individual subplots to change a controller"""
        controllers = np.asarray(
            [subplot.controller for subplot in self], dtype=object
        ).reshape(self.shape)
        controllers.flags.writeable = False
        return controllers

    @property
    def cameras(self) -> np.ndarray[pygfx.Camera]:
        """cameras, read-only array, access individual subplots to change a camera"""
        cameras = np.asarray(
            [subplot.camera for subplot in self], dtype=object
        ).reshape(self.shape)
        cameras.flags.writeable = False
        return cameras

    @property
    def names(self) -> np.ndarray[str]:
        """subplot names, read-only array, access individual subplots to change a name"""
        names = np.asarray([subplot.name for subplot in self]).reshape(self.shape)
        names.flags.writeable = False
        return names

    def __getitem__(self, index: tuple[int, int] | str) -> Subplot:
        if isinstance(index, str):
            for subplot in self._subplots.ravel():
                if subplot.name == index:
                    return subplot
            raise IndexError(f"no subplot with given name: {index}")
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

    def start_render(self):
        """start render cycle"""
        self.canvas.request_draw(self.render)
        self.canvas.set_logical_size(*self._starting_size)

    def show(
        self,
        autoscale: bool = True,
        maintain_aspect: bool = None,
        toolbar: bool = True,
        sidecar: bool = False,
        sidecar_kwargs: dict = None,
        add_widgets: list = None,
    ):
        """
        Begins the rendering event loop and shows the plot in the desired output context (jupyter, qt or glfw).

        Parameters
        ----------
        autoscale: bool, default ``True``
            autoscale the Scene

        maintain_aspect: bool, default ``True``
            maintain aspect ratio

        toolbar: bool, default ``True``
            show toolbar

        sidecar: bool, default ``True``
            display plot in a ``jupyterlab-sidecar``, only for jupyter output context

        sidecar_kwargs: dict, default ``None``
            kwargs for sidecar instance to display plot
            i.e. title, layout

        add_widgets: list of widgets
            a list of ipywidgets or QWidget that are vertically stacked below the plot

        Returns
        -------
        OutputContext
            In jupyter, it will display the plot in the output cell or sidecar

            In Qt, it will display the Plot, toolbar, etc. as stacked widget, use `Plot.widget` to access it.
        """

        # show was already called, return existing output context
        if self._output is not None:
            return self._output

        self.start_render()

        if sidecar_kwargs is None:
            sidecar_kwargs = dict()

        if add_widgets is None:
            add_widgets = list()

        # flip y-axis if ImageGraphics are present
        for subplot in self:
            for g in subplot.graphics:
                if isinstance(g, ImageGraphic):
                    subplot.camera.local.scale_y *= -1
                    break

        if autoscale:
            for subplot in self:
                if maintain_aspect is None:
                    _maintain_aspect = subplot.camera.maintain_aspect
                else:
                    _maintain_aspect = maintain_aspect
                subplot.auto_scale(maintain_aspect=_maintain_aspect, zoom=0.95)

        # used for generating images in docs using nbsphinx
        if "NB_SNAPSHOT" in os.environ.keys():
            if os.environ["NB_SNAPSHOT"] == "1":
                return self.canvas.snapshot()

        # return the appropriate OutputContext based on the current canvas
        if self.canvas.__class__.__name__ == "JupyterWgpuCanvas":
            from .output.jupyter_output import (
                JupyterOutputContext,
            )  # noqa - inline import

            self._output = JupyterOutputContext(
                frame=self,
                make_toolbar=toolbar,
                use_sidecar=sidecar,
                sidecar_kwargs=sidecar_kwargs,
                add_widgets=add_widgets,
            )

        elif self.canvas.__class__.__name__ == "QWgpuCanvas":
            from .output.qt_output import QOutputContext  # noqa - inline import

            self._output = QOutputContext(
                frame=self, make_toolbar=toolbar, add_widgets=add_widgets
            )

        else:  # assume GLFW, the output context is just the canvas
            self._output = self.canvas

        # return the output context, this call is required for jupyter but not for Qt
        return self._output

    def close(self):
        self.output.close()

    def _call_animate_functions(self, funcs: list[callable]):
        for fn in funcs:
            try:
                args = getfullargspec(fn).args
            except (ValueError, TypeError):
                warn(
                    f"Could not resolve argspec of {self.__class__.__name__} animation function: {fn}, "
                    f"calling it without arguments."
                )
                args = []

            if len(args) > 0:
                if args[0] == "self" and not len(args) > 1:
                    with log_exception(f"Animation Error in {fn}"):
                        fn()
                else:
                    with log_exception(f"Animation Error in {fn}"):
                        fn(self)
            else:
                with log_exception(f"Animation Error in {fn}"):
                    fn()

    def add_animations(
        self,
        *funcs: callable,
        pre_render: bool = True,
        post_render: bool = False,
    ):
        """
        Add function(s) that are called on every render cycle.
        These are called at the Figure level.

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

    def __len__(self):
        """number of subplots"""
        return self.shape[0] * self.shape[1]

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


class FigureRecorder:
    def __init__(self, figure: Figure):
        self._figure = figure
        self._video_writer: VideoWriterAV = None
        self._video_writer_queue = Queue()
        self._record_fps = 25
        self._record_timer = 0
        self._record_start_time = 0

    def _record(self):
        """
        Sends frame to VideoWriter through video writer queue
        """
        # current time
        t = time()

        # put frame in queue only if enough time as passed according to the desired framerate
        # otherwise it tries to record EVERY frame on every rendering cycle, which just blocks the rendering
        if t - self._record_timer < (1 / self._record_fps):
            return

        # reset timer
        self._record_timer = t

        if self._video_writer is not None:
            ss = self._figure.canvas.snapshot()
            # exclude alpha channel
            self._video_writer_queue.put(ss.data[..., :-1])

    def start(
        self,
        path: str | Path,
        fps: int = 25,
        codec: str = "mpeg4",
        pixel_format: str = "yuv420p",
        options: dict = None,
    ):
        """
        Start a recording, experimental. Call ``record_end()`` to end a recording.
        Note: playback duration does not exactly match recording duration.

        Requires PyAV: https://github.com/PyAV-Org/PyAV

        **Do not resize canvas during a recording, the width and height must remain constant!**

        Parameters
        ----------
        path: str or Path
            path to save the recording

        fps: int, default ``25``
            framerate, do not use > 25 within jupyter

        codec: str, default "mpeg4"
            codec to use, see ``ffmpeg`` list: https://www.ffmpeg.org/ffmpeg-codecs.html .
            In general, ``"mpeg4"`` should work on most systems. ``"libx264"`` is a
            better option if you have it installed.

        pixel_format: str, default "yuv420p"
            pixel format

        options: dict, optional
            Codec options. For example, if using ``"mpeg4"`` you can use ``{"q:v": "20"}`` to set the quality between
            1-31, where "1" is highest and "31" is lowest. If using ``"libx264"``` you can use ``{"crf": "30"}`` where
            the "crf" value is between "0" (highest quality) and "50" (lowest quality). See ``ffmpeg`` docs for more
            info on codec options

        Examples
        --------

        With ``"mpeg4"``

        .. code-block:: python

            # start recording video
            figure.recorder.start("./video.mp4", options={"q:v": "20"}

            # do stuff like interacting with the plot, change things, etc.

            # end recording
            figure.recorder.stop()

        With ``"libx264"``

        .. code-block:: python

            # start recording video
            figure.recorder.start("./vid_x264.mp4", codec="libx264", options={"crf": "25"})

            # do stuff like interacting with the plot, change things, etc.

            # end recording
            figure.recorder.stop()

        """

        if Path(path).exists():
            raise FileExistsError(f"File already exists at given path: {path}")

        # queue for sending frames to VideoWriterAV process
        self._video_writer_queue = Queue()

        # snapshot to get canvas width height
        ss = self._figure.canvas.snapshot()

        # writer process
        self._video_writer = VideoWriterAV(
            path=str(path),
            queue=self._video_writer_queue,
            fps=int(fps),
            width=ss.width,
            height=ss.height,
            codec=codec,
            pixel_format=pixel_format,
            options=options,
        )

        # start writer process
        self._video_writer.start()

        # 1.3 seems to work well to reduce that difference between playback time and recording time
        # will properly investigate later
        self._record_fps = fps * 1.3
        self._record_start_time = time()

        # record timer used to maintain desired framerate
        self._record_timer = time()

        self._figure.add_animations(self._record)

    def stop(self) -> float:
        """
        End a current recording. Returns the real duration of the recording

        Returns
        -------
        float
            recording duration
        """

        # tell video writer that recording has finished
        self._video_writer_queue.put(None)

        # wait for writer to finish
        self._video_writer.join(timeout=5)

        self._video_writer = None

        # so self._record() is no longer called on every render cycle
        self._figure.remove_animation(self._record)

        return time() - self._record_start_time
