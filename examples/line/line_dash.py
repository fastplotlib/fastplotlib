"""
Line Dash Patterns
==================

Draw lines with different dash patterns using matplotlib-style strings.
"""

# test_example = true
# sphinx_gallery_pygfx_docs = 'screenshot'

import fastplotlib as fpl
import numpy as np

figure = fpl.Figure(size=(700, 560))

xs = np.linspace(0, 4 * np.pi, 100)

# a matplotlib-style string, or a sequence of floats, sets the dash pattern
patterns = ["-", "--", "-.", ":"]

for i, pattern in enumerate(patterns):
    ys = np.sin(xs) + i * 3
    data = np.column_stack([xs, ys])
    figure[0, 0].add_line(
        data, thickness=5, dash_pattern=pattern, name=pattern
    )

figure.show()


# NOTE: fpl.loop.run() should not be used for interactive sessions
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
