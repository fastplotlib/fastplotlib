"""
Heatmap change data
===================
Change the data of a heatmap
"""

# test_example = true

import fastplotlib as fpl
import numpy as np


fig = fpl.Figure()

xs = np.linspace(0, 1_000, 10_000)

sine = np.sin(np.sqrt(xs))

data = np.vstack([sine * i for i in range(20_000)])

# plot the image data
img = fig[0, 0].add_image(data=data, name="heatmap")

fig.show()

fig.canvas.set_logical_size(1500, 1500)

fig[0, 0].auto_scale()
cosine = np.cos(np.sqrt(xs))

# change first 10,000 rows and 9,000 columns
img.data[:10_000, :9000] = np.vstack([cosine[:9000] * i * 2 for i in range(10_000)])

if __name__ == "__main__":
    print(__doc__)
    fpl.run()
