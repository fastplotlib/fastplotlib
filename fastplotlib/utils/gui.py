import sys
import importlib
from pathlib import Path

import wgpu


# --- Prepare


# Ultimately, we let wgpu-py decide, but we can prime things a bit to create our
# own preferred order, by importing a Qt lib. But we only do this if no GUI has
# been imported yet.

# Qt libs that we will try to import
qt_libs = ["PySide6", "PyQt6", "PySide2", "PyQt5"]

# Other known libs that, if imported, we should probably not try to force qt
other_libs = ["glfw", "wx", "ipykernel"]

already_imported = [name for name in (qt_libs + other_libs) if name in sys.modules]
if not already_imported:
    for name in qt_libs:
        try:
            importlib.import_module(name)
        except Exception:
            pass
        else:
            break


# --- Triage


# Let wgpu do the auto gui selection
from wgpu.gui.auto import WgpuCanvas, run

# Get the name of the backend ('qt', 'glfw', 'jupyter')
GUI_BACKEND = WgpuCanvas.__module__.split(".")[-1]
IS_JUPYTER = GUI_BACKEND == "jupyter"


# --- Some backend-specific preparations


def _notebook_print_banner():

    from ipywidgets import Image
    from IPython.display import display

    logo_path = Path(__file__).parent.parent.joinpath(
        "assets", "fastplotlib_face_logo.png"
    )

    with open(logo_path, "rb") as f:
        logo_data = f.read()

    image = Image(value=logo_data, format="png", width=300, height=55)

    display(image)

    # print logo and adapter info
    adapters = [a for a in wgpu.gpu.enumerate_adapters()]
    adapters_info = [a.request_adapter_info() for a in adapters]

    default_adapter_info = wgpu.gpu.request_adapter().request_adapter_info()
    default_ix = adapters_info.index(default_adapter_info)

    if len(adapters) > 0:
        print("Available devices:")

    for ix, adapter in enumerate(adapters_info):
        atype = adapter["adapter_type"]
        backend = adapter["backend_type"]
        driver = adapter["description"]
        device = adapter["device"]

        if atype == "DiscreteGPU" and backend != "OpenGL":
            charactor = chr(0x2705)
        elif atype == "IntegratedGPU" and backend != "OpenGL":
            charactor = chr(0x0001FBC4)
        else:
            charactor = chr(0x2757)

        if ix == default_ix:
            default = " (default) "
        else:
            default = " "

        output_str = f"{charactor}{default}| {device} | {atype} | {backend} | {driver}"
        print(output_str)


if GUI_BACKEND == "jupyter":
    _notebook_print_banner()

elif GUI_BACKEND == "qt":
    from wgpu.gui.qt import get_app, libname

    # create and store ref to qt app
    _qt_app = get_app()

    # Import submodules of PySide6/PyQt6/PySid2/PyQt5
    # For the way that fpl uses Qt, the supported Qt libs seems compatible enough.
    # If necessary we can do some qtpy-like monkey-patching here.
    QtCore = importlib.import_module(".QtCore", libname)
    QtGui = importlib.import_module(".QtGui", libname)
    QtWidgets = importlib.import_module(".QtWidgets", libname)
