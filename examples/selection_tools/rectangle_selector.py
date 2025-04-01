"""
Rectangle Selectors
===================

Example showing how to use a `RectangleSelector` with line collections
"""

# test_example = false
# sphinx_gallery_pygfx_docs = 'screenshot'

import numpy as np
import fastplotlib as fpl
from itertools import product

# create a figure
figure = fpl.Figure(size=(700, 560))


# generate some data
def make_circle(center, radius: float, n_points: int = 75) -> np.ndarray:
    theta = np.linspace(0, 2 * np.pi, n_points)
    xs = radius * np.sin(theta)
    ys = radius * np.cos(theta)

    return np.column_stack([xs, ys]) + center


spatial_dims = (50, 50)

circles = list()
for center in product(range(0, spatial_dims[0], 9), range(0, spatial_dims[1], 9)):
    circles.append(make_circle(center, 3, n_points=75))

pos_xy = np.vstack(circles)

# add image
line_collection = figure[0, 0].add_line_collection(circles, cmap="jet", thickness=5)

# add rectangle selector to image graphic
rectangle_selector = line_collection.add_rectangle_selector()


# add event handler to highlight selected indices
@rectangle_selector.add_event_handler("selection")
def color_indices(ev):
    line_collection.cmap = "jet"
    ixs = ev.get_selected_indices()

    # iterate through each of the selected indices, if the array size > 0 that mean it's under the selection
    selected_line_ixs = [i for i in range(len(ixs)) if ixs[i].size > 0]
    line_collection[selected_line_ixs].colors = "w"


# manually move selector to make a nice gallery image :D
rectangle_selector.selection = (15, 30, 15, 30)


figure.show()

# NOTE: `if __name__ == "__main__"` is NOT how to use fastplotlib interactively
# please see our docs for using fastplotlib interactively in ipython and jupyter
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
