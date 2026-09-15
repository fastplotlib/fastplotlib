"""
Subplot Config
==============

Configuration values are used for any argument that is not explicitly passed.
"""

# test_example = true
# sphinx_gallery_pygfx_docs = 'screenshot'

import fastplotlib as fpl
from fastplotlib.layouts import Subplot
import imageio.v3 as iio

# used to create every subplot
Subplot.config.init.toolbar = False
# a sequence of 1, 2, or 4 colors, 2 colors makes a gradient from bottom to top
Subplot.config.init.background_color = ["black", "gray"]

# used by Subplot.auto_scale(), which Figure.show() calls for every subplot
Subplot.config.auto_scale.zoom = 4

data = iio.imread("imageio:camera.png")

figure = fpl.Figure(size=(700, 560))

figure[0, 0].add_image(data)

figure.show()

# NOTE: fpl.loop.run() should not be used for interactive sessions
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
