"""
Very Compact Style
==================

A style is a preset of configuration values.
The very compact style hides the subplot toolbar and frame, useful for figures with many subplots.
"""

# test_example = true
# sphinx_gallery_pygfx_docs = 'screenshot'

import numpy as np
import fastplotlib as fpl

fpl.style.very_compact()

xs = np.linspace(-10, 10, 100)
ys = np.sin(xs)
data = np.column_stack([xs, ys])

figure = fpl.Figure(shape=(2, 2), size=(700, 560))

for subplot in figure:
    subplot.add_line(data)

figure.show()


# NOTE: fpl.loop.run() should not be used for interactive sessions
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
