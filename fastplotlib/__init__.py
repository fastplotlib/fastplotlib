from pathlib import Path

from wgpu.gui.auto import run

from .plot import Plot
from .layouts import GridPlot

try:
    import ipywidgets
except (ModuleNotFoundError, ImportError):
    pass
else:
    from .widgets import ImageWidget


with open(Path(__file__).parent.joinpath("VERSION"), "r") as f:
    __version__ = f.read().split("\n")[0]
