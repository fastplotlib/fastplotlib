from ...layouts import IMGUI


if IMGUI:
    from ._base import NDSlicer, NDGraphic
    from ._nd_positions import NDPositions, NDPositionsSlicer, NDTimeseries, ndp_extras
    from ._nd_image import NDImageSlicer, NDImage
    from ._video import VideoSlicer
    from ._nd_vectors import NDVectorsSlicer, NDVectors
    from ._ndwidget import NDWidget

else:

    class NDWidget:
        def __init__(self, *args, **kwargs):
            raise ModuleNotFoundError(
                "NDWidget requires `imgui-bundle` to be installed.\n"
                "pip install imgui-bundle"
            )
