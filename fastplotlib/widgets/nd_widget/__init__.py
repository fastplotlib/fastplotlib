from ...layouts import IMGUI

if IMGUI:
    from ._index import RangeContinuous, AutoRangeContinuous, ReferenceIndices
    from ._base import NDSlicer, NDGraphic
    from ._nd_positions import NDPositions, NDPositionsSlicer, NDTimeseries
    from ._nd_image import NDImageSlicer, NDImage
    from ._video import VideoSlicer
    from ._nd_vectors import NDVectorsSlicer, NDVectors
    from ._nd_field import NDFieldSlicer, NDField
    from ._ndwidget import NDWidget
    from ._ndw_subplot import NDWSubplot

    __all__ = [
        "RangeContinuous",
        "AutoRangeContinuous",
        "ReferenceIndices",
        "NDSlicer",
        "NDGraphic",
        "NDPositions",
        "NDPositionsSlicer",
        "NDTimeseries",
        "NDImageSlicer",
        "NDImage",
        "VideoSlicer",
        "NDVectorsSlicer",
        "NDVectors",
        "NDFieldSlicer",
        "NDField",
        "NDWidget",
        "NDWSubplot",
    ]


else:

    class NDWidget:
        def __init__(self, *args, **kwargs):
            raise ModuleNotFoundError(
                "NDWidget requires `imgui-bundle` to be installed.\n"
                "pip install imgui-bundle"
            )

    __all__ = [
        "NDWidget",
    ]
