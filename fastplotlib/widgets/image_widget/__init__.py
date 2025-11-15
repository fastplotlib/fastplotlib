from ...layouts import IMGUI

if IMGUI:
    from ._widget import ImageWidget
    from ._processor import NDImageProcessor

else:

    class ImageWidget:
        def __init__(self, *args, **kwargs):
            raise ModuleNotFoundError(
                "ImageWidget requires `imgui-bundle` to be installed.\n"
                "pip install imgui-bundle"
            )
