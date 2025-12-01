"""
Gaussian kernel as a surface
============================

Example showing a gaussian kernel as a surface mesh
"""

# test_example = true
# sphinx_gallery_pygfx_docs = 'screenshot'

import fastplotlib as fpl
import numpy as np


figure = fpl.Figure(size=(700, 560), cameras="3d", controller_types="orbit")


def gaus2d(x=0, y=0, mx=0, my=0, sx=1, sy=1):
    return (
        1.0
        / (2.0 * np.pi * sx * sy)
        * np.exp(
            -((x - mx) ** 2.0 / (2.0 * sx**2.0) + (y - my) ** 2.0 / (2.0 * sy**2.0))
        )
    )


r = np.linspace(0, 10, num=200)
x, y = np.meshgrid(r, r)
z = gaus2d(x, y, mx=5, my=5, sx=1, sy=1) * 50

mesh = figure[0, 0].add_surface(
    np.dstack([x, y, z]), mode="phong", colors="magenta", cmap="jet"
)

# figure[0, 0].axes.grids.xy.visible = True
figure[0, 0].camera.show_object(mesh.world_object, (-2, 2, -2), up=(0, 0, 1))
figure.show()


# NOTE: fpl.loop.run() should not be used for interactive sessions
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
