from pathlib import Path

from .layouts import Plot, GridPlot

from wgpu.gui.auto import run

try:
    import ipywidgets
except (ModuleNotFoundError, ImportError):
    pass
else:
    from .widgets import ImageWidget


with open(Path(__file__).parent.joinpath("VERSION"), "r") as f:
    __version__ = f.read().split("\n")[0]
