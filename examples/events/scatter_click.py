"""
Scatter click
=============

Add an event handler to click on scatter points and highlight them, i.e. change the color and size of the clicked point.
Fly around the 3D scatter using WASD keys and click on points to highlight them
"""

# test_example = false
# sphinx_gallery_pygfx_docs = 'screenshot'

import numpy as np
import fastplotlib as fpl

# make a gaussian cloud
data = np.random.normal(loc=0, scale=3, size=1500).reshape(500, 3)

figure = fpl.Figure(cameras="3d", size=(700, 560))

scatter = figure[0, 0].add_scatter(
    data,  # the gaussian cloud
    sizes=10,  # some big points that are easy to click
    cmap="viridis",
    cmap_transform=np.linalg.norm(data, axis=1)  # color points using distance from origin
)

# simple dict to restore the original scatter color and size
# of the previously clicked point upon clicking a new point
old_props = {"index": None, "size": None, "color": None}


@scatter.add_event_handler("click")
def highlight_point(ev):
    global old_props

    # the index of the point that was just clicked
    new_index = ev.pick_info["vertex_index"]

    # restore old point's properties
    if old_props["index"] is not None:
        old_index = old_props["index"]
        if new_index == old_index:
            # same point was clicked, ignore
            return
        scatter.colors[old_index] = old_props["color"]
        scatter.sizes[old_index] = old_props["size"]

    # store the current property values of this new point
    old_props["index"] = new_index
    old_props["color"] = scatter.colors[new_index].copy()  # if you do not copy you will just get a view of the array!
    old_props["size"] = scatter.sizes[new_index]

    # highlight this new point
    scatter.colors[new_index] = "magenta"
    scatter.sizes[new_index] = 20


figure.show()


# NOTE: `if __name__ == "__main__"` is NOT how to use fastplotlib interactively
# please see our docs for using fastplotlib interactively in ipython and jupyter
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()

