"""
Surface animation
=================

Example of a surface ripple animation by setting the z-height data on every render.

"""

# test_example = false
# sphinx_gallery_pygfx_docs = 'animate 6s'

import fastplotlib as fpl
import numpy as np


figure = fpl.Figure(size=(700, 560), cameras="3d", controller_types="orbit")


def create_ripple(shape=(100, 100), phase=0.0, freq=np.pi / 4, ampl=1.0):
    m, n = shape
    y, x = np.ogrid[-m / 2 : m / 2, -n / 2 : n / 2]
    r = np.sqrt(x**2 + y**2)
    z = (ampl * np.sin(freq * r + phase)) / np.sqrt(r + 1)

    return z * 8


z = create_ripple()

# set the clim vmax
max_z = create_ripple(phase=(np.pi / 4) - (np.pi / 2)).max()

surface = figure[0, 0].add_surface(
    z, mode="basic", cmap="viridis", clim=(-max_z, max_z)
)

# enable continuous updates for the tooltip
figure[0, 0].tooltip.continuous_update = True

figure[0, 0].camera.show_object(surface.world_object, (-1, 3, -1), up=(0, 0, 1))
figure.show()

figure[0, 0].camera.zoom = 1.15

phase = 0.0


def animate():
    global phase

    z = create_ripple(phase=phase)

    surface.data = z

    phase -= 0.1


figure[0, 0].add_animations(animate)


# NOTE: fpl.loop.run() should not be used for interactive sessions
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
