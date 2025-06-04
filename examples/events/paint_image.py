"""
Paint an Image
==============

Click and drag the mouse to paint in the image
"""

# test_example = false
# sphinx_gallery_pygfx_docs = 'screenshot'

import numpy as np
import fastplotlib as fpl
import pygfx

figure = fpl.Figure(size=(700, 560))

# add a blank image
image = figure[0, 0].add_image(np.zeros((100, 100)), vmin=0, vmax=255)

painting = False  # use to toggle painting state


@image.add_event_handler("pointer_down")
def on_pointer_down(ev: pygfx.PointerEvent):
    # start painting when mouse button is down
    global painting

    # get image element index, (x, y) pos corresponds to array (column, row)
    col, row = ev.pick_info["index"]

    # increase value of this image element
    image.data[row, col] = np.clip(image.data[row, col] + 50, 0, 255)

    # toggle on painting state
    painting = True

    # disable controller until painting stops when mouse button is un-clicked
    figure[0, 0].controller.enabled = False


@image.add_event_handler("pointer_move")
def on_pointer_move(ev: pygfx.PointerEvent):
    # continue painting when mouse pointer is moved
    global painting

    if not painting:
        return

    # get image element index, (x, y) pos corresponds to array (column, row)
    col, row = ev.pick_info["index"]

    image.data[row, col] = np.clip(image.data[row, col] + 50, 0, 255)


@figure.renderer.add_event_handler("pointer_up")
def on_pointer_up(ev: pygfx.PointerEvent):
    # toggle off painting state
    global painting
    painting = False

    # re-enable controller
    figure[0, 0].controller.enabled = True


figure.show()

# NOTE: fpl.loop.run() should not be used for interactive sessions
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
