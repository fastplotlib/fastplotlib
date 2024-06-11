"""
Heatmap change data
===================
Change the data of a heatmap
"""

# test_example = true

import fastplotlib as fpl
import numpy as np


fig = fpl.Figure()

xs = np.linspace(0, 1_000, 9_000)

sine = np.sin(np.sqrt(xs))

data = np.vstack([sine * i for i in range(9_000)])

# plot the image data
img = fig[0, 0].add_image(data=data, name="heatmap")

fig.show()

fig.canvas.set_logical_size(1500, 1500)

fig[0, 0].auto_scale()
cosine = np.cos(np.sqrt(xs)[:3000])

# change first 2,000 rows and 3,000 columns
img.data[:2_000, :3_000] = np.vstack([cosine * i * 4 for i in range(2_000)])

if __name__ == "__main__":
    print(__doc__)
    fpl.run()
