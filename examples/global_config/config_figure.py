"""
Figure Config
=============

Configuration values are used for any argument that is not explicitly passed.
"""

# test_example = true
# sphinx_gallery_pygfx_docs = 'screenshot'

import numpy as np
import fastplotlib as fpl

# a tall figure to fit a stack of lines
fpl.Figure.config.init.size = (700, 1000)

# used by Figure.show()
fpl.Figure.config.show.axes_visible = False
fpl.layouts.Subplot.config.auto_scale.maintain_aspect = False

xs = np.linspace(0, 4 * np.pi, 100)
ys = np.sin(xs)
data = np.column_stack([xs, ys])

# 10 sine waves to stack
stack_data = np.stack([data] * 5)

figure = fpl.Figure()

figure[0, 0].add_line_stack(stack_data)

figure.show()

# NOTE: fpl.loop.run() should not be used for interactive sessions
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
