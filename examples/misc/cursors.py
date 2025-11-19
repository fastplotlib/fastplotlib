"""
Cursor tool
===========

Example with multiple subplots and an interactive cursor
that marks the same position in each subplot
"""

import numpy as np
import fastplotlib as fpl
import imageio.v3 as iio

img1 = iio.imread("imageio:camera.png")
img2 = iio.imread("imageio:astronaut.png")

scatter_data = np.random.normal(loc=256, scale=(50), size=(500)).reshape(250, 2)


figure = fpl.Figure(shape=(2, 2))

figure[0, 0].add_image(img1)
figure[0, 1].add_image(img2)
figure[1, 0].add_scatter(scatter_data, sizes=5)

cursor = fpl.Cursor(mode="crosshair", color="cyan")

for subplot in figure:
    cursor.add_subplot(subplot)

figure.show_tooltips = True

figure.show()
fpl.loop.run()
