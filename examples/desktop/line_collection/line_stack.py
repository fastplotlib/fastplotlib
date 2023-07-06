"""
Line Stack
==========
Example showing how to plot line collections
"""

# test_example = true

import numpy as np
import fastplotlib as fpl


xs = np.linspace(0, 100, 1000)
# sine wave
ys = np.sin(xs) * 20

# make 25 lines
data = np.vstack([ys] * 25)

plot = fpl.Plot()
# to force a specific framework such as glfw:
# plot = fpl.Plot(canvas="glfw")

# line stack takes all the same arguments as line collection and behaves similarly
plot.add_line_stack(data, cmap="jet")

plot.show(maintain_aspect=False)

plot.canvas.set_logical_size(900, 600)

if __name__ == "__main__":
    print(__doc__)
    fpl.run()
