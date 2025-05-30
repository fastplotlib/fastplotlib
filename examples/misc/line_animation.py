"""
Simple Line Animation
=====================

Example showing animation with lines.
"""

# test_example = false
# sphinx_gallery_pygfx_docs = 'animate'

import fastplotlib as fpl
import numpy as np

# generate some data
start, stop = 0, 2 * np.pi
increment = (2 * np.pi) / 50

# make a simple sine wave
xs = np.linspace(start, stop, 100)
ys = np.sin(xs)

figure = fpl.Figure(size=(700, 560))

# plot the image data
sine = figure[0, 0].add_line(ys, name="sine", colors="r")


# increment along the x-axis on each render loop :D
def update_line(subplot):
    global increment, start, stop
    xs = np.linspace(start + increment, stop + increment, 100)
    ys = np.sin(xs)

    start += increment
    stop += increment

    # change only the y-axis values of the line
    subplot["sine"].data[:, 1] = ys


figure[0, 0].add_animations(update_line)

figure.show(maintain_aspect=False)


# NOTE: fpl.loop.run() should not be used for interactive sessions
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
