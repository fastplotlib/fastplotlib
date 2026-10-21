from . import gui
from .enums import *
from . import types
from .functions import *
from ._config import global_config
from .gpu import enumerate_adapters, select_adapter, print_wgpu_report
from .protocols import (
    ARRAY_LIKE_ATTRS,
    ArrayProtocol,
    FutureProtocol,
    CudaArrayProtocol,
)
from ._video_writer import VideoWriter


def __getattr__(name):
    # the rendercanvas loop is resolved lazily, see gui.py
    if name == "loop":
        return gui.loop
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
