import sys
import importlib


def _is_jupyter():
    """Determine whether the user is executing in a Jupyter Notebook / Lab."""
    try:
        ip = get_ipython()
        if ip.has_trait("kernel"):
            return True
        else:
            return False
    except NameError:
        return False


IS_JUPYTER = _is_jupyter()

# Triage. Ultimately, we let wgpu-py decide, but we can prime things a bit to
# create our own preferred order. If we're in Jupyter, wgpu will prefer and
# select Jupyter, so no no action needed. If one of the GUI backends is already
# imported, this is likely because the user want to use that one, so we should
# honor that. Otherwise, we try importing the GUI backends in the order that
# fastplotlib prefers. When wgpu-py loads the gui.auto, it will see that the
# respective lib has been imported and then prefer the corresponding backend.

# A list of wgpu GUI backend libs, in the order preferred by fpl
gui_backend_libs = ["PySide6", "PyQt6", "PySide2", "PyQt5", "glfw"]

already_imported = [libname for libname in gui_backend_libs if libname in sys.modules]
if not IS_JUPYTER and not already_imported:
    for libname in gui_backend_libs:
        try:
            importlib.import_module(libname)
        except Exception:
            pass
        else:
            break

from wgpu.gui.auto import WgpuCanvas, run

# Get the name of the backend ('qt', 'glfw', 'jupyter')
GUI_BACKEND = WgpuCanvas.__module__.split(".")[-1]

if GUI_BACKEND == "qt":
    from wgpu.gui.qt import get_app, libname

    # create and store ref to qt app
    _qt_app = get_app()

    # Import submodules of PySide6/PyQt6/PySid2/PyQt5
    # For the way that fpl uses Qt, the supported Qt libs seems compatible enough.
    # If necessary we can do some qtpy-like monkey-patching here.
    QtCore = importlib.import_module(".QtCore", libname)
    QtGui = importlib.import_module(".QtGui", libname)
    QtWidgets = importlib.import_module(".QtWidgets", libname)
