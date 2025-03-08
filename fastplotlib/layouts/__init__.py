from ._figure import Figure
from ._utils import IMGUI

if IMGUI:
    from ._imgui_figure import ImguiFigure

    __all__ = ["Figure", "ImguiFigure"]
else:
    __all__ = ["Figure"]
