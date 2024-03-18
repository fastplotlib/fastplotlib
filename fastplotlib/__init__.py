from pathlib import Path

from .layouts import Plot, GridPlot
from .graphics import *
from .graphics.selectors import *
from .legends import *
from .widgets import ImageWidget
from .utils import _notebook_print_banner, config

from wgpu.gui.auto import run
from wgpu.backends.wgpu_native import enumerate_adapters


with open(Path(__file__).parent.joinpath("VERSION"), "r") as f:
    __version__ = f.read().split("\n")[0]

adapters = [a.request_adapter_info() for a in enumerate_adapters()]

if len(adapters) < 1:
    raise IndexError("No WGPU adapters found, fastplotlib will not work.")

_notebook_print_banner()


def _get_sg_image_scraper():
    import sphinx_gallery.scrapers
    from .utils.gallery_scraper import fpl_scraper
    # add webp as supported extension
    sphinx_gallery.scrapers._KNOWN_IMG_EXTS += ("webp",)

    return fpl_scraper


__all__ = [
    "Plot",
    "GridPlot",
    "run",
    "ImageWidget",
    "Legend",
]
