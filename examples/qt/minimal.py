"""
Minimal PyQt example that displays an image. Press "r" key to autoscale
"""
from PyQt6 import QtWidgets
import fastplotlib as fpl
import imageio.v3 as iio

# Qt app MUST be instantiated before creating any fpl objects, or any other Qt objects
app = QtWidgets.QApplication([])

img = iio.imread("imageio:astronaut.png")

# force qt canvas, wgpu will sometimes pick glfw by default even if Qt is present
plot = fpl.Plot(canvas="qt")

plot.add_image(img)
plot.camera.local.scale *= -1

# must call plot.show() to start rendering loop
plot.show()

# set QWidget initial size from image width and height
plot.canvas.resize(*img.shape[:2])


def autoscale(ev):
    if ev.key == "r":
        plot.auto_scale()


# useful if you pan/zoom away from the image
plot.renderer.add_event_handler(autoscale, "key_down")

# execute Qt app
app.exec()
