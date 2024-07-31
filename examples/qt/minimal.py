"""
Minimal PyQt example that displays an image. Press "r" key to autoscale
"""
# import Qt or PySide
from PyQt6 import QtWidgets
import fastplotlib as fpl
import imageio.v3 as iio

img = iio.imread("imageio:astronaut.png")

# fastplotlib and wgpu will auto-detect if Qt is imported and then use the Qt canvas and Qt output context
fig = fpl.Figure()

fig[0, 0].add_image(img)

# must call fig.show() to start rendering loop and show the QWidget containing the fastplotlib figure
qwidget = fig.show()

# set QWidget initial size from image width and height
qwidget.resize(*img.shape[:2])

# execute Qt app
# if this is part of a larger Qt QApplication, you can also call app.exec() where app is the QApplication instance
fpl.run()
