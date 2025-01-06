"""
Minimal Qt
==========

Minimal PyQt example that displays an image.

`Figure.show()` returns a QWidget that you can use in a Qt app just like any other QWidget!
"""

# test_example = false
# sphinx_gallery_pygfx_docs = 'code'

# import Qt or PySide
from PyQt6 import QtWidgets
import fastplotlib as fpl
import imageio.v3 as iio

img = iio.imread("imageio:astronaut.png")

# fastplotlib and wgpu will auto-detect if Qt is imported and then use the Qt canvas and Qt output context
figure = fpl.Figure()

figure[0, 0].add_image(img)

# must call fig.show() to start rendering loop and show the QWidget containing the fastplotlib figure
qwidget = figure.show()

# set QWidget initial size from image width and height
qwidget.resize(*img.shape[:2])

# execute Qt app
# if this is part of a larger Qt QApplication, you can also call app.exec() where app is the QApplication instance
fpl.loop.run()

# You can also use Qt interactively/in a non-blocking manner in notebooks and ipython
# by using %gui qt and NOT calling `fpl.run()`, see the user guide for more details
