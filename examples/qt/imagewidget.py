"""
Use ImageWidget to display one or multiple image sequences
"""
import numpy as np
from PyQt6 import QtWidgets
import fastplotlib as fpl

# Qt app MUST be instantiated before creating any fpl objects, or any other Qt objects
app = QtWidgets.QApplication([])

images = np.random.rand(100, 512, 512)

# create image widget, force Qt canvas so it doesn't pick glfw
iw = fpl.ImageWidget(images, grid_plot_kwargs={"canvas": "qt"})
iw.show()
iw.widget.resize(800, 800)

# another image widget with multiple images
images_list = [np.random.rand(100, 512, 512) for i in range(9)]

iw_mult = fpl.ImageWidget(
    images_list,
    grid_plot_kwargs={"canvas": "qt"},
    cmap="viridis"
)
iw_mult.show()
iw_mult.widget.resize(800, 800)

app.exec()
