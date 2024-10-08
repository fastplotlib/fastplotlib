"""
Rectangle Selectors Images
==========================

Example showing how to use a `RectangleSelector` with images
"""

# test_example = false
# sphinx_gallery_pygfx_docs = 'screenshot'

import imageio.v3 as iio
import fastplotlib as fpl

# create a figure
figure = fpl.Figure(
    shape=(2, 1),
    size=(700, 560)
)

# add image
image_graphic = figure[0, 0].add_image(data=iio.imread("imageio:camera.png"))

# add rectangle selector to image graphic
rectangle_selector = image_graphic.add_rectangle_selector()

# add a zoomed plot of the selected data
zoom_ig = figure[1, 0].add_image(rectangle_selector.get_selected_data())


# add event handler to update the data of the zoomed image as the selection changes
@rectangle_selector.add_event_handler("selection")
def update_data(ev):
    # get the new data
    new_data = ev.get_selected_data()

    # remove the old zoomed image graphic
    global zoom_ig

    figure[1, 0].remove_graphic(zoom_ig)

    # add new zoomed image of new data
    zoom_ig = figure[1, 0].add_image(data=new_data)

    # autoscale the plot
    figure[1, 0].auto_scale()

figure.show()

# NOTE: `if __name__ == "__main__"` is NOT how to use fastplotlib interactively
# please see our docs for using fastplotlib interactively in ipython and jupyter
if __name__ == "__main__":
    print(__doc__)
    fpl.run()
