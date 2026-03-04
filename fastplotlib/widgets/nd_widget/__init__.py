from ...layouts import IMGUI

if IMGUI:
    from ._base import NDProcessor
    from ._nd_positions import NDPositions, NDPositionsProcessor, ndp_extras
    from ._nd_image import NDImageProcessor, NDImage
    from ._ndwidget import NDWidget
else:
    class NDWidget:
        def __init__(self, *args, **kwargs):
            raise ModuleNotFoundError(
                "NDWidget requires `imgui-bundle` to be installed.\n"
                "pip install imgui-bundle"
            )
