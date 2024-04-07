from pathlib import Path

from .utils.gui import run
from .graphics import *
from .graphics.selectors import *
from .legends import *
from .layouts import Figure

# from .widgets import ImageWidget
from .utils import config

import wgpu


with open(Path(__file__).parent.joinpath("VERSION"), "r") as f:
    __version__ = f.read().split("\n")[0]

adapters = [a.summary for a in wgpu.gpu.enumerate_adapters()]

if len(adapters) < 1:
    raise IndexError("No WGPU adapters found, fastplotlib will not work.")


__all__ = [
    "Figure",
    "run",
    # "ImageWidget",
    "Legend",
]
