"""
Earth sphere animation
======================

Example showing how to create a sphere with an image of the Earth and rotate it around its 23.44° axis of rotation
with respect to the ecliptic (the xz plane in the visualization).

"""

# test_example = false
# sphinx_gallery_pygfx_docs = 'animate 8s'

import fastplotlib as fpl
import numpy as np
import imageio.v3 as iio
import pylinalg as la


figure = fpl.Figure(size=(700, 560), cameras="3d", controller_types="orbit")

# create a sphere from spherical coordinates
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
z = radius * np.sin(phi_grid) * theta_grid_sin

# get texture coords to map the image onto the mesh positions
u = phi_grid / (np.pi * 2)
v = 1 - (theta_grid / np.pi)
texcoords = np.dstack([u, v]).reshape(-1, 2)

# get an image of the earth from nasa
image = iio.imread(
    "https://svs.gsfc.nasa.gov/vis/a000000/a003600/a003615/flat_earth_Largest_still.0330.jpg"
)
# images coordinate systems are typically inverted in y, so flip the image
image = np.ascontiguousarray(np.flipud(image))

# create a sphere
sphere = figure[0, 0].add_surface(
    np.dstack([x, y, z]),
    mode="phong",
    colors="magenta",
    cmap=image,
    mapcoords=texcoords,
)

# display xz plane as a grid
figure[0, 0].axes.grids.xz.visible = True
figure.show()

# view from top right angle
figure[0, 0].camera.show_object(sphere.world_object, (-0.5, -0.25, -1), up=(0, 1, 0))
figure[0, 0].camera.zoom = 1.25

# create quaternion for 23.44 degrees axial tilt
axial_tilt = la.quat_from_euler((np.radians(23.44), 0), order="XY")

# a line to indicate the axial tilt
figure[0, 0].add_line(
    np.array([[0, -20, 0], [0, 20, 0]]), rotation=axial_tilt, colors="magenta"
)

rot = 1


def rotate():
    # rotate by 1 degree
    global rot
    rot += 1
    rot_quat = la.quat_from_euler((0, np.radians(rot)), order="XY")

    # apply rotation w.r.t. axial tilt
    sphere.rotation = la.quat_mul(axial_tilt, rot_quat)


figure[0, 0].add_animations(rotate)


# NOTE: fpl.loop.run() should not be used for interactive sessions
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
