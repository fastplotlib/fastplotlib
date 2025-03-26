"""
Key Events
==========

Move an image around using and change some of its properties using keyboard events.

Use the arrows keys to move the image by changing its offset

Press "v", "g", "p" to change the colormaps (viridis, grey, plasma).

Press "r" to rotate the image +18 degrees (pi / 10 radians)
Press "Shift + R" to rotate the image -18 degrees
Axis of rotation is the origin

Press "-", "=" to decrease/increase the vmin
Press "_", "+" to decrease/increase the vmax

We use the ImageWidget here because the histogram LUT tool makes it easy to see the changes in vmin and vmax.
"""

# test_example = false
# sphinx_gallery_pygfx_docs = 'screenshot'

import numpy as np
import fastplotlib as fpl
import imageio.v3 as iio

data = iio.imread("imageio:camera.png")

iw = fpl.ImageWidget(data)

image = iw.managed_graphics[0]


@iw.figure.renderer.add_event_handler("key_down")
def handle_event(ev):
    match ev.key:
        # change the cmap
        case "v":
            image.cmap = "viridis"
        case "g":
            image.cmap = "grey"
        case "p":
            image.cmap = "plasma"

        # keys to change vmin/vmax
        case "-":
            image.vmin -= 1
        case "=":
            image.vmin += 1
        case "_":
            image.vmax -= 1
        case "+":
            image.vmax += 1

        # rotate
        case "r":
            image.rotate(np.pi / 10, axis="z")
        case "R":
            image.rotate(-np.pi / 10, axis="z")

        # arrow key events to move the image
        case "ArrowUp":
            image.offset = image.offset + [0, -10, 0]  # remember y-axis is flipped for images
        case "ArrowDown":
            image.offset = image.offset + [0, 10, 0]
        case "ArrowLeft":
            image.offset = image.offset + [-10, 0, 0]
        case "ArrowRight":
            image.offset = image.offset + [10, 0, 0]

iw.show()


# NOTE: `if __name__ == "__main__"` is NOT how to use fastplotlib interactively
# please see our docs for using fastplotlib interactively in ipython and jupyter
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()

