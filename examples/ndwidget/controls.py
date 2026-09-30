"""
NDWidget controls
=================

The controls window of an ``NDWidget`` with only its sliders: the row of playback controls is dropped when
the widget is created, and the title bar afterwards.
"""

# test_example = true
# sphinx_gallery_pygfx_docs = 'screenshot'

import numpy as np
import fastplotlib as fpl

data = np.random.rand(100, 10, 128, 128).astype(np.float32)

# a reference range for each slider dim
ranges = {
    "time": (0, 100, 1),
    "depth": (0, 10, 1),
}

# no playback controls above the sliders
ndw = fpl.NDWidget(ranges=ranges, size=(700, 560), ui_kwargs={"playback": False})

ndw[0, 0].add_nd_image(
    data,
    ("time", "depth", "m", "n"),  # all dim names
    ("m", "n"),  # the spatial dims, the rest get sliders
    name="4d-image",
)

figure = ndw.figure

ndw.show()

# every option can also be set on the controls window at any time, here the title bar goes too
ndw.ui_sliders.title = None

# `ndw.ui_sliders.visible = False` hides the whole window and the subplots take its space, and
# `fpl.NDWidget.config.init.ui_kwargs = {"playback": False}` configures every widget created after it


# NOTE: fpl.loop.run() should not be used for interactive sessions
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
