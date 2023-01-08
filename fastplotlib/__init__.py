from .plot import Plot
from .layouts import GridPlot
from .widgets import ImageWidget
from pathlib import Path
from wgpu.gui.auto import run


with open(Path(__file__).parent.joinpath("VERSION"), "r") as f:
    __version__ = f.read().split("\n")[0]
