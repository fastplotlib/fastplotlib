from pathlib import Path

# this must be the first import for auto-canvas detection
from .utils import loop  # noqa
from .graphics import *
from .graphics.selectors import *
from .graphics.utils import pause_events
from .legends import *
from .tools import *

from .layouts import IMGUI

if IMGUI:
    # default to imgui figure if imgui_bundle is installed
    from .layouts import ImguiFigure as Figure
else:
    from .layouts import Figure

from .widgets import ImageWidget
from .utils import config, enumerate_adapters, select_adapter, print_wgpu_report


with open(Path(__file__).parent.joinpath("VERSION"), "r") as f:
    __version__ = f.read().split("\n")[0]

if len(enumerate_adapters()) < 1:
    from warnings import warn

    warn(
        f"WGPU could not enumerate any adapters, fastplotlib will not work.\n"
        f"This is caused by one of the following:\n"
        f"1. You do not have a hardware GPU installed and you do not have "
        f"software rendering (ex. lavapipe) installed either\n"
        f"2. Your GPU drivers are not installed or something is wrong with your GPU driver installation, "
        f"re-installing the latest drivers from your hardware vendor (probably Nvidia or AMD) may help.\n"
        f"3. You are missing system libraries that are required for WGPU to access GPU(s), this is "
        f"common in cloud computing environments.\n"
        f"These two links can help you troubleshoot:\n"
        f"https://wgpu-py.readthedocs.io/en/stable/start.html#platform-requirements\n"
        f"https://fastplotlib.readthedocs.io/en/latest/user_guide/gpu.html\n",
        RuntimeWarning,
    )
