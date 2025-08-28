"""
Simple Image Update
===================

Example showing updating a single plot with new random 512x512 data.
"""

# test_example = false
# sphinx_gallery_pygfx_docs = 'animate'

import fastplotlib as fpl
import numpy as np

data = np.random.rand(512, 512)

figure = fpl.Figure(size=(700, 560))

# plot the image data
image = figure[0, 0].add_image(data=data, name="random-image")


# a function to update the image
# a figure-level animation function will optionally take the figure as an argument
def update_data(figure_instance):
    new_data = np.random.rand(512, 512)
    figure_instance[0, 0]["random-image"].data = new_data

figure.add_animations(update_data)

figure.show()


# NOTE: fpl.loop.run() should not be used for interactive sessions
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
