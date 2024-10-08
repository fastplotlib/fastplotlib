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
import fastplotlib as fpl
import imageio.v3 as iio


video = iio.imread("imageio:cockatoo.mp4")

# fastplotlib and wgpu will auto-detect if Qt is imported and then use the Qt canvas and output context
fig = fpl.Figure()

fig[0, 0].add_image(video[0], name="video")


def update_frame(ix):
    fig[0, 0]["video"].data = video[ix]
    # you can also do fig[0, 0].graphics[0].data = video[ix]


# create a QMainWindow
main_window = QtWidgets.QMainWindow()

# Create a QSlider for updating frames
slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
slider.setMaximum(video.shape[0] - 1)
slider.setMinimum(0)
slider.valueChanged.connect(update_frame)

# put slider in a dock
dock = QtWidgets.QDockWidget()
dock.setWidget(slider)

# put the dock in the main window
main_window.addDockWidget(
    QtCore.Qt.DockWidgetArea.BottomDockWidgetArea,
    dock
)

# calling fig.show() is required to start the rendering loop
qwidget = fig.show()

# set the qwidget as the central widget
main_window.setCentralWidget(qwidget)

# set window size from width and height of video
main_window.resize(video.shape[2], video.shape[1])

# show the main window
main_window.show()

# execute Qt app
fpl.run()

# You can also use Qt interactively/in a non-blocking manner in notebooks and ipython
# by using %gui qt and NOT calling `fpl.run()`, see the user guide for more details
