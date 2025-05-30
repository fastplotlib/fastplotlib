"""
Embed within a Qt Window
========================

When using the Qt canvas, `Figure.show()` just returns a QWidget that behaves like any other Qt widget. So you can
embed it and do other things that you can do with ordinary QWidgets. This example use a simple Plot to display a video
frame that can be updated using a QSlider.
"""

# test_example = false
# sphinx_gallery_pygfx_docs = 'code'

from PyQt6 import QtWidgets, QtCore
from rendercanvas.qt import QRenderCanvas, loop
from rendercanvas.utils.cube import setup_drawing_sync
import imageio.v3 as iio

app = QtWidgets.QApplication([])

main_window = QtWidgets.QMainWindow()

slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
slider.setMaximum(100)
slider.setMinimum(0)

dock = QtWidgets.QDockWidget()
dock.setWidget(slider)

main_window.addDockWidget(
    QtCore.Qt.DockWidgetArea.BottomDockWidgetArea,
    dock
)

canvas = QRenderCanvas(max_fps=60.0, vsync=True, update_mode="continuous")
draw_frame = setup_drawing_sync(canvas)
canvas.request_draw(draw_frame)

main_window.setCentralWidget(canvas)

main_window.resize(500, 400)

main_window.show()

app.exec()
