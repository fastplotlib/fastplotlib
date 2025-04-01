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
image_graphic = figure[0, 0].add_image(data=data, name="random-image")


# a function to update the image_graphic
# a figure-level animation function will optionally take the figure as an argument
def update_data(figure_instance):
    new_data = np.random.rand(512, 512)
    figure_instance[0, 0]["random-image"].data = new_data


figure.add_animations(update_data)

figure.show()


# NOTE: `if __name__ == "__main__"` is NOT how to use fastplotlib interactively
# please see our docs for using fastplotlib interactively in ipython and jupyter
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
