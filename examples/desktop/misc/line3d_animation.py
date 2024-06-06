"""
Simple 3D Line Animation
========================

Example showing animation with 3D lines.
"""

# test_example = false
# sphinx_gallery_pygfx_docs = 'animate 5s'

import numpy as np
import fastplotlib as fpl

# create data in the shape of a spiral
phi = np.linspace(0, 30, 200)

xs = phi * np.cos(phi)
ys = phi * np.sin(phi)
zs = phi

# make data 3d, with shape [<n_vertices>, 3]
spiral = np.dstack([xs, ys, zs])[0]

fig = fpl.Figure(cameras="3d")

line_graphic = fig[0,0].add_line(data=spiral, thickness=3, cmap='jet')

marker = fig[0,0].add_scatter(data=spiral[0], sizes=10, name="marker")

marker_index = 0


# a function to move the ball along the spiral
def move_marker():
    global marker_index

    marker_index += 1

    if marker_index == spiral.shape[0]:
        marker_index = 0

    for subplot in fig:
        subplot["marker"].data = spiral[marker_index]


# add `move_marker` to the animations
fig.add_animations(move_marker)

fig.show()

# set canvas variable for sphinx_gallery to properly generate examples
# NOT required for users
canvas = fig.canvas

fig.canvas.set_logical_size(700, 560)

fig[0,0].auto_scale(maintain_aspect=False)

# NOTE: `if __name__ == "__main__"` is NOT how to use fastplotlib interactively
# please see our docs for using fastplotlib interactively in ipython and jupyter
if __name__ == "__main__":
    print(__doc__)
    fpl.run()
