"""
Volume cursor
=============

Orthogonal XY, YZ and XZ views of a volume that follow one 3D cursor. Click any 2D view to move the
cursor; the 3D view shows the three slices through it inside the volume.
"""

# test_example = false
# sphinx_gallery_pygfx_docs = 'screenshot'

import numpy as np
import fastplotlib as fpl
import imageio.v3 as iio

volume = iio.imread("imageio:stent.npz").astype(np.float32)  # (z, y, x)
n_z, n_y, n_x = volume.shape

figure = fpl.Figure(
    shape=(2, 2),
    names=["xy", "yz", "xz", "3d"],
    cameras=["2d", "2d", "2d", "3d"],
    controller_types=["panzoom", "panzoom", "panzoom", "orbit"],
    size=(900, 800),
)

z, y, x = n_z // 2, n_y // 2, n_x // 2
image_xy = figure["xy"].add_image(volume[z], cmap="viridis")
image_yz = figure["yz"].add_image(volume[:, :, x].T, cmap="viridis")  # world x is z, world y is y
image_xz = figure["xz"].add_image(volume[:, y, :], cmap="viridis")  # world x is x, world y is z
volume_graphic = figure["3d"].add_image_volume(volume, cmap="viridis")

cursor = fpl.VolumeCursor(position=(x, y, z))
cursor.add_subplot(figure["xy"], axes=("x", "y"))
cursor.add_subplot(figure["yz"], axes=("z", "y"))
cursor.add_subplot(figure["xz"], axes=("x", "z"))
cursor.add_volume(volume_graphic)


@cursor.add_event_handler
def update_slices(position):
    x, y, z = (int(np.clip(round(v), 0, n - 1)) for v, n in zip(position, (n_x, n_y, n_z)))
    image_xy.data = volume[z]
    image_yz.data = volume[:, :, x].T
    image_xz.data = volume[:, y, :]


figure.show()


# NOTE: fpl.loop.run() should not be used for interactive sessions
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
