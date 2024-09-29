from ._figure import Figure

try:
    import imgui_bundle
except ImportError:
    IMGUI = False
else:
    IMGUI = True

if IMGUI:
    from ._imgui_figure import ImguiFigure

    __all__ = ["Figure", "ImguiFigure"]
else:
    __all__ = ["Figure"]
