"""
Simple 3D Line Animation
========================

Example showing animation with 3D lines.
"""

# test_example = false
# sphinx_gallery_pygfx_docs = 'animate 6s'

import numpy as np
import fastplotlib as fpl

# create data in the shape of a spiral
phi = np.linspace(0, 30, 200)

xs = phi * np.cos(phi)
ys = phi * np.sin(phi)
zs = phi

# make data 3d, with shape [<n_vertices>, 3]
spiral = np.dstack([xs, ys, zs])[0]

figure = fpl.Figure(cameras="3d", size=(700, 560))

line_graphic = figure[0,0].add_line(data=spiral, thickness=3, cmap='jet')

marker = figure[0,0].add_scatter(data=spiral[0], sizes=10, name="marker")

marker_index = 0


# a function to move the ball along the spiral
def move_marker():
    global marker_index

    marker_index += 1

    if marker_index == spiral.shape[0]:
        marker_index = 0

    for subplot in figure:
        subplot["marker"].data = spiral[marker_index]


# add `move_marker` to the animations
figure.add_animations(move_marker)

# remove clutter
figure[0, 0].axes.grids.xy.visible = True
figure[0, 0].axes.grids.xz.visible = True


figure.show()


# NOTE: `if __name__ == "__main__"` is NOT how to use fastplotlib interactively
# please see our docs for using fastplotlib interactively in ipython and jupyter
if __name__ == "__main__":
    print(__doc__)
    fpl.run()
