"""
Cursor tool
===========

Example with multiple subplots and an interactive cursor
that marks the same position in each subplot
"""

import numpy as np
import fastplotlib as fpl
import imageio.v3 as iio
from pylinalg import vec_transform

img1 = iio.imread("imageio:camera.png")
img2 = iio.imread("imageio:astronaut.png")

scatter_data = np.random.normal(loc=256, scale=(50), size=(500)).reshape(250, 2)


def map_world_to_screen(subplot, pos):
    ndc = vec_transform(pos, subplot.camera.camera_matrix)

    # ndc = (clip[0] / clip[3], clip[1] / clip[3], clip[2] / clip[3])

    width, height = subplot.canvas.get_physical_size()
    x_screen = (ndc[0] + 1) * 0.5 * width
    y_screen = (1 - ndc[1]) * 0.5 * height

    return x_screen, y_screen


figure = fpl.Figure(shape=(2, 2), size=(500, 500))

figure[0, 0].add_image(img1)
figure[0, 1].add_image(img2)
figure[1, 0].add_scatter(scatter_data, sizes=5)

cursor = fpl.Cursor(mode="crosshair", color="cyan")

for subplot in figure:
    cursor.add_subplot(subplot)

figure.show_tooltips = True

tooltips2 = fpl.Tooltip()
tooltips2.world_object.visible = True
figure.add_tooltip(tooltips2)

@figure.renderer.add_event_handler("pointer_move")
def update(ev):
    pos = figure[0, 0].map_screen_to_world(ev)
    if pos is None:
        return

    x, y = map_world_to_screen(figure[0, 1], pos)
    print(x, y)

    tooltips2.display((x, y), "bah")


figure.show()
fpl.loop.run()
