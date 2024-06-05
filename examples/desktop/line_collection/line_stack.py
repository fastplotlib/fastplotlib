"""
Line Stack
==========
Example showing how to plot line collections
"""

# test_example = true
# sphinx_gallery_pygfx_docs = 'screenshot'

import numpy as np
import fastplotlib as fpl


xs = np.linspace(0, 100, 1000)
# sine wave
ys = np.sin(xs) * 20

# make 25 lines
data = np.vstack([ys] * 25)

fig = fpl.Figure()

# line stack takes all the same arguments as line collection and behaves similarly
fig[0, 0].add_line_stack(data, cmap="jet")

fig.show(maintain_aspect=False)

# set canvas variable for sphinx_gallery to properly generate examples
# NOT required for users
canvas = fig.canvas

fig.canvas.set_logical_size(700, 560)

# NOTE: `if __name__ == "__main__"` is NOT how to use fastplotlib interactively
# please see our docs for using fastplotlib interactively in ipython and jupyter
if __name__ == "__main__":
    print(__doc__)
    fpl.run()
