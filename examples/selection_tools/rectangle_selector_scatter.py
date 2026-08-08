"""
Rectangle Selectors with ScatterGraphic
=======================================

Example showing how to use a `RectangleSelector` with a scatter plot.
"""

# test_example = true
# sphinx_gallery_pygfx_docs = 'screenshot'

import numpy as np
import fastplotlib as fpl

# create a figure
figure = fpl.Figure(
    size=(700, 560)
)

xys = (100 * np.random.random_sample(size=(200, 2))).astype(np.float32)

# add image
scatter = figure[0, 0].add_scatter(xys, cmap="jet", sizes=4)

# add rectangle selector to image graphic
rectangle_selector = scatter.add_rectangle_selector()

# add event handler to highlight selected indices
@rectangle_selector.add_event_handler("selection")
def color_indices(ev):
    scatter.cmap = "jet"
    scatter.sizes = 4
    ixs = ev.get_selected_indices()
    if ixs.size == 0:
        return
    scatter.colors[ixs] = 'w'
    scatter.sizes[ixs] = 8


# manually move selector to make a nice gallery image :D
rectangle_selector.selection = (20, 40, 40, 60)


figure.show()

# NOTE: fpl.loop.run() should not be used for interactive sessions
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
