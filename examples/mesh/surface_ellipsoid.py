"""
Ellipsoid surface
=================

Simple example of a sphere surface mesh with a colormap indicating z values.

"""

# test_example = false
# sphinx_gallery_pygfx_docs = 'screenshot'

import fastplotlib as fpl
import numpy as np

figure = fpl.Figure(size=(700, 560), cameras='3d', controller_types='orbit')

# create an ellipsoid from spherical coordinates
# see this for reference: https://mathworld.wolfram.com/SphericalCoordinates.html
# phi and theta are swapped in this example w.r.t. the wolfram alpha description
radius = 10

nx = 101
phi = np.linspace(0, np.pi * 2, num=nx, dtype=np.float32)
ny = 51
theta = np.linspace(0, np.pi, num=ny, dtype=np.float32)

phi_grid, theta_grid = np.meshgrid(phi, theta)

# convert to cartesian coordinates
theta_grid_sin = np.sin(theta_grid)
x = radius * np.cos(phi_grid) * theta_grid_sin * -1
y = radius * np.cos(theta_grid)

# elongate along z axis
z = radius * 2 * np.sin(phi_grid) * theta_grid_sin

sphere = figure[0, 0].add_surface(
    np.dstack([x, y, z]),
    mode="phong",
    cmap="bwr", # by default, providing a colormap name will map the colors to z values
)

# display xz plane as a grid
figure[0, 0].axes.grids.xy.visible = True
figure.show()

# view from top right angle
figure[0, 0].camera.show_object(sphere.world_object, (1, 1, -1), up=(0, 0, 1))


# NOTE: fpl.loop.run() should not be used for interactive sessions
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
