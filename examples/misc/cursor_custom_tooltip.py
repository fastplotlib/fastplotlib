"""
Cursor tool with tooltips
=========================

Cursor tool example that also displays tooltips
"""

import numpy as np
import fastplotlib as fpl
import imageio.v3 as iio
from pylinalg import vec_transform, mat_combine

img1 = iio.imread("imageio:camera.png")
img2 = iio.imread("imageio:astronaut.png")

scatter_data = np.random.normal(loc=256, scale=(50), size=(500)).reshape(250, 2)
line_data = np.random.rand(100, 2) * 512

figure = fpl.Figure(shape=(2, 2), size=(700, 800))

img = figure[0, 0].add_image(img1, cmap="viridis")
figure[0, 1].add_image(img2, metadata=np.arange(512))
figure[1, 0].add_scatter(scatter_data, sizes=5, metadata="scatter metadata")
figure[1, 1].add_line(line_data, metadata="line metadata")

cursor = fpl.Cursor(mode="crosshair", color="w")

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

    x, y = figure[0, 1].map_world_to_screen(pos)
    pick = subplot.get_pick_info((x, y))

    if pick is None:
        tooltips2.visible = False
        return
    print(pick)
    info = pick["graphic"].metadata[pick["index"][1]]
    tooltips2.display((x, y), str(info))

print((img.world_object.children[0].uniform_buffer.data["global_id"]).item())
figure.show()


# NOTE: fpl.loop.run() should not be used for interactive sessions
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
