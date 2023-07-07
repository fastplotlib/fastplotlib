from pathlib import Path

from .layouts import Plot, GridPlot
from .graphics import *
from .graphics.selectors import *

from wgpu.gui.auto import run

try:
    import ipywidgets
except (ModuleNotFoundError, ImportError):
    pass
else:
    from .widgets import ImageWidget


def _get_sg_image_scraper():
    from .utils import fastplotlib_scraper

    return fastplotlib_scraper


with open(Path(__file__).parent.joinpath("VERSION"), "r") as f:
    __version__ = f.read().split("\n")[0]

__all__ = [
    "Plot",
    "GridPlot",
    "run",
    "ImageWidget"
]
