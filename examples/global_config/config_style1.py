"""
Light and Compact Style
=======================

A style is a preset of configuration values.
Once called, it effects all subsequent Figures/graphic objects that the style sets.
"""

# test_example = true
# sphinx_gallery_pygfx_docs = 'screenshot'

import numpy as np
import fastplotlib as fpl

# white background, black axes, dark graphic colors
fpl.style.light()

# no subplot toolbar, thin subplot frame
# this configuration is merged with the existing light preset from above
fpl.style.compact()

xs = np.linspace(-10, 10, 100)
ys = np.sin(xs)
data = np.column_stack([xs, ys])

figure = fpl.Figure(shape=(2, 1), size=(700, 560))

# the colors of the line and the scatter come from the style
figure[0, 0].add_line(data)
figure[1, 0].add_scatter(data)

figure.show()


# NOTE: fpl.loop.run() should not be used for interactive sessions
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
