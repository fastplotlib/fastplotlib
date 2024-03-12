from pathlib import Path

from .layouts import Plot, GridPlot
from .graphics import *
from .graphics.selectors import *
from .legends import *
from .widgets import ImageWidget

from wgpu.gui.auto import run
from wgpu.backends.wgpu_native import enumerate_adapters


adapters = [a.request_adapter_info() for a in enumerate_adapters()]

if len(adapters) < 1:
    raise IndexError("No WGPU adapters found, fastplotlib will not work.")

with open(Path(__file__).parent.joinpath("VERSION"), "r") as f:
    __version__ = f.read().split("\n")[0]

__all__ = [
    "Plot",
    "GridPlot",
    "run",
    "ImageWidget",
    "Legend",
]
