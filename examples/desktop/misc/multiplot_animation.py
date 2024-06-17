"""
Multi-Subplot Image Update
==========================

Example showing updating a single plot with new random 512x512 data.
"""

# test_example = false
# sphinx_gallery_pygfx_docs = 'animate'

import fastplotlib as fpl
import numpy as np

# Figure of shape 2 x 3 with all controllers synced
figure = fpl.Figure(shape=(2, 3), controller_ids="sync")

# Make a random image graphic for each subplot
for subplot in figure:
    # create image data
    data = np.random.rand(512, 512)
    # add an image to the subplot
    subplot.add_image(data, name="rand-img")

figure[0,1]["rand-img"].cmap = "viridis"
figure[1,0]["rand-img"].cmap = "Wistia"
figure[0,2]["rand-img"].cmap = "gray"
figure[1,1]["rand-img"].cmap = "spring"

# Define a function to update the image graphics with new data
# add_animations will pass the gridplot to the animation function
def update_data(f):
    for subplot in f:
        new_data = np.random.rand(512, 512)
        # index the image graphic by name and set the data
        subplot["rand-img"].data = new_data

# add the animation function
figure.add_animations(update_data)

# show the gridplot
figure.show()

figure.canvas.set_logical_size(700, 560)

# NOTE: `if __name__ == "__main__"` is NOT how to use fastplotlib interactively
# please see our docs for using fastplotlib interactively in ipython and jupyter
if __name__ == "__main__":
    print(__doc__)
    fpl.run()