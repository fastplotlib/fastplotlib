from ...layouts import IMGUI

if IMGUI:
    from ._index import RangeContinuous, AutoRangeContinuous, ReferenceIndices
    from ._base import NDSlicer, NDGraphic
    from ._nd_positions import NDPositions, NDPositionsSlicer, NDTimeseries, nds_extras
    from ._nd_image import NDImageSlicer, NDImage
    from ._video import VideoSlicer
    from ._nd_vectors import NDVectorsSlicer, NDVectors
    from ._ndwidget import NDWidget

    __all__ = [
        "RangeContinuous",
        "AutoRangeContinuous",
        "ReferenceIndices",
        "NDSlicer",
        "NDGraphic",
        "NDPositions",
        "NDPositionsSlicer",
        "NDTimeseries",
        "nds_extras",
        "NDImageSlicer",
        "NDImage",
        "VideoSlicer",
        "NDVectorsSlicer",
        "NDVectors",
        "NDWidget",
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
