from ...layouts import IMGUI

try:
    import imgui_bundle
except ImportError:
    HAS_XARRAY = False
else:
    HAS_XARRAY = True


if IMGUI and HAS_XARRAY:
    from ._base import NDProcessor, NDGraphic
    from ._nd_positions import NDPositions, NDPositionsProcessor, ndp_extras
    from ._nd_image import NDImageProcessor, NDImage
    from ._ndwidget import NDWidget

else:

    class NDWidget:
        def __init__(self, *args, **kwargs):
            raise ModuleNotFoundError(
                "NDWidget requires `imgui-bundle` and `xarray` to be installed.\n"
                "pip install imgui-bundle"
            )
