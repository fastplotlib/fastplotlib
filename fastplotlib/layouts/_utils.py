from typing import *

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
    "qt": QWgpuCanvas
}


def make_canvas_and_renderer(
        canvas: Union[str, WgpuCanvas, Texture, None],
        renderer: [WgpuRenderer, None]
):
    """
    Parses arguments and returns the appropriate canvas and renderer instances 
    as a tuple (canvas, renderer)
    """

    if canvas is None:
        canvas = WgpuCanvas()

    elif isinstance(canvas, str):
        if canvas not in CANVAS_OPTIONS:
            raise ValueError(
                f"str canvas argument must be one of: {CANVAS_OPTIONS}"
            )
        elif not CANVAS_OPTIONS_AVAILABLE[canvas]:
            raise ImportError(
                f"The {canvas} framework is not installed for using this canvas"
            )
        else:
            canvas = CANVAS_OPTIONS_AVAILABLE[canvas]()

    elif not isinstance(canvas, (WgpuCanvasBase, Texture)):
        raise ValueError(
            f"canvas option must either be a valid WgpuCanvas implementation, a pygfx Texture"
            f" or a str from the following options: {CANVAS_OPTIONS}"
        )

    if renderer is None:
        renderer = WgpuRenderer(canvas)

    return canvas, renderer
