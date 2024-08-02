try:
    import imgui_bundle
except ImportError:
    IMGUI = False
else:
    IMGUI = True

if IMGUI:
    from ._imgui_figure import ImguiFigure
    Figure = ImguiFigure
    __all__ = ["Figure", "ImguiFigure"]
else:
    from ._figure import Figure

    __all__ = ["Figure"]
