from typing import *

import pygfx
from pygfx import WgpuRenderer, Texture

# default auto-determined canvas
from wgpu.gui.auto import WgpuCanvas
from wgpu.gui.base import WgpuCanvasBase


# TODO: this determination can be better
try:
    from wgpu.gui.jupyter import JupyterWgpuCanvas
except ImportError:
    JupyterWgpuCanvas = False

try:
    import PyQt6
    from wgpu.gui.qt import QWgpuCanvas
except ImportError:
    QWgpuCanvas = False

try:
    from wgpu.gui.glfw import GlfwWgpuCanvas
except ImportError:
    GlfwWgpuCanvas = False


CANVAS_OPTIONS = ["jupyter", "glfw", "qt"]
CANVAS_OPTIONS_AVAILABLE = {
    "jupyter": JupyterWgpuCanvas,
    "glfw": GlfwWgpuCanvas,
    "qt": QWgpuCanvas,
}


def auto_determine_canvas():
    try:
        ip = get_ipython()
        if ip.has_trait("kernel"):
            if hasattr(ip.kernel, "app"):
                if ip.kernel.app.__class__.__name__ == "QApplication":
                    return QWgpuCanvas
            else:
                return JupyterWgpuCanvas
    except NameError:
        pass

    else:
        if CANVAS_OPTIONS_AVAILABLE["qt"]:
            return QWgpuCanvas
        elif CANVAS_OPTIONS_AVAILABLE["glfw"]:
            return GlfwWgpuCanvas

    # We go with the wgpu auto guess
    # for example, offscreen canvas etc.
    return WgpuCanvas


def make_canvas_and_renderer(
    canvas: Union[str, WgpuCanvas, Texture, None], renderer: [WgpuRenderer, None]
):
    """
    Parses arguments and returns the appropriate canvas and renderer instances
    as a tuple (canvas, renderer)
    """

    if canvas is None:
        Canvas = auto_determine_canvas()
        canvas = Canvas(max_fps=60)

    elif isinstance(canvas, str):
        if canvas not in CANVAS_OPTIONS:
            raise ValueError(f"str canvas argument must be one of: {CANVAS_OPTIONS}")
        elif not CANVAS_OPTIONS_AVAILABLE[canvas]:
            raise ImportError(
                f"The {canvas} framework is not installed for using this canvas"
            )
        else:
            canvas = CANVAS_OPTIONS_AVAILABLE[canvas](max_fps=60)

    elif not isinstance(canvas, (WgpuCanvasBase, Texture)):
        raise ValueError(
            f"canvas option must either be a valid WgpuCanvas implementation, a pygfx Texture"
            f" or a str from the following options: {CANVAS_OPTIONS}"
        )

    if renderer is None:
        renderer = WgpuRenderer(canvas, pixel_ratio=2)

    return canvas, renderer


def create_camera(
    camera_type: Union[pygfx.PerspectiveCamera, str],
) -> pygfx.PerspectiveCamera:
    if isinstance(camera_type, pygfx.PerspectiveCamera):
        return camera_type

    elif camera_type == "2d":
        # use perspective for orthographic, makes it easier to then switch to controllers that make sense with fov > 0
        return pygfx.PerspectiveCamera(fov=0)

    elif camera_type == "3d":
        return pygfx.PerspectiveCamera()

    else:
        raise ValueError(
            "camera must be one of: '2d', '3d' or an instance of pygfx.PerspectiveCamera"
        )


controller_types = {
    "fly": pygfx.FlyController,
    "panzoom": pygfx.PanZoomController,
    "trackball": pygfx.TrackballController,
    "orbit": pygfx.OrbitController,
}


def create_controller(
    controller_type: Union[pygfx.Controller, None, str],
    camera: pygfx.PerspectiveCamera,
) -> pygfx.Controller:
    """
    Creates the controllers and adds the camera to it.
    """
    if isinstance(controller_type, pygfx.Controller):
        controller_type.add_camera(camera)
        return controller_type

    if controller_type is None:
        # default controllers
        if camera.fov == 0:
            # default for orthographic
            return pygfx.PanZoomController(camera)
        else:
            return pygfx.FlyController(camera)

    if controller_type not in controller_types.keys():
        raise KeyError(
            f"controller must be a valid pygfx.Controller or one of: "
            f"{list(controller_types.keys())}, you have passed: {controller_type}"
        )

    return controller_types[controller_type](camera)
