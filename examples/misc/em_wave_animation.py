"""
Electromagnetic Wave Animation
==============================

Example showing animation of an electromagnetic wave.
"""

# test_example = false
# sphinx_gallery_pygfx_docs = 'animate 8s'

import fastplotlib as fpl
import numpy as np

figure = fpl.Figure(
    cameras="3d",
    controller_types="orbit",
    size=(700, 560)
)

start, stop = 0, 4 * np.pi

# let's define the x, y and z axes for each with direction of wave propogation along the z-axis
# electric field in the xz plane travelling along
zs = np.linspace(start, stop, 200)
e_ys = np.zeros(200)
e_xs = np.sin(zs)
electric = np.column_stack([e_xs, e_ys, zs])

# magnetic field in the yz plane
zs = np.linspace(start, stop, 200)
m_ys = np.sin(zs)
m_xs = np.zeros(200)
magnetic = np.column_stack([m_xs, m_ys, zs])

# add the lines
figure[0, 0].add_line(electric, colors="blue", thickness=2, name="e")
figure[0, 0].add_line(magnetic, colors="red", thickness=2, name="m")

# draw vector line at every 10th position
electric_vectors = [np.array([[0, 0, z], [x, 0, z]]) for (x, z) in zip(e_xs[::10], zs[::10])]
magnetic_vectors = [np.array([[0, 0, z], [0, y, z]]) for (y, z) in zip(m_ys[::10], zs[::10])]

# add as a line collection
figure[0, 0].add_line_collection(electric_vectors, colors="blue", thickness=1.5, name="e-vec")
figure[0, 0].add_line_collection(magnetic_vectors, colors="red", thickness=1.5, name="m-vec")
# note that the z_offset in `add_line_collection` is not data-related
# it is the z-offset for where to place the *graphic*, by default with Orthographic cameras (i.e. 2D views)
# it will increment by 1 for each line in the collection, we want to disable this so set z_position=0

# just a pre-saved camera state
state = {
    'position': np.array([-8.0 ,  6.0, -2.0]),
    'rotation': np.array([0.09,  0.9 ,  0.2, -0.5]),
    'scale': np.array([1., 1., 1.]),
    'reference_up': np.array([0., 1., 0.]),
    'fov': 50.0,
    'width': 12,
    'height': 12,
    'zoom': 1.35,
    'maintain_aspect': True,
    'depth_range': None
}


figure[0, 0].camera.set_state(state)

# make all grids except xz plane invisible to remove clutter
figure[0, 0].axes.grids.xz.visible = True

figure.show()

figure[0, 0].camera.zoom = 1.5

increment = np.pi * 4 / 100


# moves the wave one step along the z-axis
def tick(subplot):
    global increment, start, stop, zs
    new_zs = np.linspace(start, stop, 200)
    new_data = np.sin(new_zs)

    # just change the x-axis vals for the electric field
    subplot["e"].data[:, 0] = new_data
    subplot["e"].data[:, 2] = new_zs
    # and y-axis vals for magnetic field
    subplot["m"].data[:, 1] = new_data
    subplot["m"].data[:, 2] = new_zs

    # update the vector lines
    for i, (value, z) in enumerate(zip(new_data[::10], new_zs[::10])):
        subplot["e-vec"].graphics[i].data = np.array([[0, 0, z], [value, 0, z]])
        subplot["m-vec"].graphics[i].data = np.array([[0, 0, z], [0, value, z]])

    # update axes and center scene
    subplot.axes.z.start_value = start
    subplot.axes.z.update(subplot.camera, subplot.viewport.logical_size)
    subplot.center_scene()

    start += increment
    stop += increment


figure[0, 0].axes.x.visible = False
figure[0, 0].axes.y.visible = False
figure[0, 0].axes.auto_grid = False

figure[0, 0].add_animations(tick)
print(figure[0, 0]._fpl_graphics_scene.children)

# NOTE: `if __name__ == "__main__"` is NOT how to use fastplotlib interactively
# please see our docs for using fastplotlib interactively in ipython and jupyter
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
