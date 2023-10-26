"""
Use a simple Plot to display a video frame that can be updated using a QSlider
"""
from PyQt6 import QtWidgets, QtCore
import fastplotlib as fpl
import imageio.v3 as iio

# Qt app MUST be instantiated before creating any fpl objects, or any other Qt objects
app = QtWidgets.QApplication([])

video = iio.imread("imageio:cockatoo.mp4")

# force qt canvas, wgpu will sometimes pick glfw by default even if Qt is present
plot = fpl.Plot(canvas="qt")

plot.add_image(video[0], name="video")
plot.camera.local.scale *= -1


def update_frame(ix):
    plot["video"].data = video[ix]
    # you can also do plot.graphics[0].data = video[ix]


# create a QMainWindow, set the plot canvas as the main widget
# The canvas does not have to be in a QMainWindow and it does
# not have to be the central widget, it will work like any QWidget
main_window = QtWidgets.QMainWindow()
main_window.setCentralWidget(plot.canvas)

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

# calling plot.show() is required to start the rendering loop
plot.show()

# set window size from width and height of video
main_window.resize(video.shape[2], video.shape[1])

# show the main window
main_window.show()

# execute Qt app
app.exec()
