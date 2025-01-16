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
from rendercanvas import BaseRenderCanvas
from rendercanvas.auto import RenderCanvas, loop

# Get the name of the backend ('qt', 'glfw', 'jupyter')
GUI_BACKEND = RenderCanvas.__module__.split(".")[-1]
IS_JUPYTER = GUI_BACKEND == "jupyter"


# --- Some backend-specific preparations


def _notebook_print_banner():
    from ipywidgets import Image
    from IPython.display import display, HTML

    logo_path = Path(__file__).parent.parent.joinpath(
        "assets", "fastplotlib_face_logo.png"
    )

    with open(logo_path, "rb") as f:
        logo_data = f.read()

    # get small logo image
    image = Image(value=logo_data, format="png", width=300, height=55)

    # get adapters and info
    adapters = [a for a in wgpu.gpu.enumerate_adapters_sync()]
    adapters_info = [a.info for a in adapters]

    default_adapter_info = wgpu.gpu.request_adapter_sync().info
    default_ix = adapters_info.index(default_adapter_info)

    if len(adapters) < 1:
        return

    # start HTML table
    table_str = (
        "<b>Available devices:</b>"
        "<table>"
        "<tr>"
        "<th>Valid</th>"
        "<th>Device</th>"
        "<th>Type</th>"
        "<th>Backend</th>"
        "<th>Driver</th>"
        "</tr>"
    )

    # parse each adapter that WGPU found
    for ix, adapter in enumerate(adapters_info):
        atype = adapter["adapter_type"]
        backend = adapter["backend_type"]
        driver = adapter["description"]
        device = adapter["device"]

        if atype in ("DiscreteGPU", "IntegratedGPU") and backend != "OpenGL":
            charactor = chr(0x2705)  # green checkmark
            tooltip = "This adapter can be used with fastplotlib"
        elif backend == "OpenGL":
            charactor = chr(0x0000274C)  # red x
            tooltip = "This adapter cannot be used with fastplotlib"
        elif device.startswith("llvmpipe") or atype == "CPU":
            charactor = f"{chr(0x00002757)} limited"  # red !
            tooltip = "CPU rendering support is limited and mainly for testing purposes"
        else:
            charactor = f"{chr(0x00002757)} unknown"  # red !
            tooltip = "Unknown adapter type and backend"

        if ix == default_ix:
            default = " (default) "
        else:
            default = ""

        # add row to HTML table
        table_str += f'<tr title="{tooltip}">'
        # add each element to this row
        for s in [f"{charactor}{default}", device, atype, backend, driver]:
            table_str += f"<td>{s}</td>"
        table_str += "</tr>"

    table_str += "</table>"

    # display logo and adapters table
    display(image)
    display(HTML(table_str))


if GUI_BACKEND == "jupyter":
    _notebook_print_banner()

elif GUI_BACKEND == "qt":
    from rendercanvas.qt import libname

    # Import submodules of PySide6/PyQt6/PySid2/PyQt5
    # For the way that fpl uses Qt, the supported Qt libs seems compatible enough.
    # If necessary we can do some qtpy-like monkey-patching here.
    QtCore = importlib.import_module(".QtCore", libname)
    QtGui = importlib.import_module(".QtGui", libname)
    QtWidgets = importlib.import_module(".QtWidgets", libname)
