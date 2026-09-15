"""
Axes Config
===========

Configuration values are used for any argument that is not explicitly passed.
"""

# test_example = true
# sphinx_gallery_pygfx_docs = 'screenshot'

import numpy as np
import fastplotlib as fpl

# these can also be set simultaneously:
# fpl.global_config.update(fpl.Axes.config.init, color="red", tick_size=16, line_width=4)
fpl.Axes.config.init.color = "red"
fpl.Axes.config.init.tick_size = 16
fpl.Axes.config.init.line_width = 4

xs = np.linspace(-10, 10, 100)
ys = np.sin(xs)
data = np.column_stack([xs, ys])

figure = fpl.Figure(size=(700, 560))

figure[0, 0].add_line(data)

figure.show()


# NOTE: fpl.loop.run() should not be used for interactive sessions
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
