"""
Volume rendering of toy data
============================

Volume rendering of toy trig data
"""

import fastplotlib as fpl
import numpy as np

n_cols = 100
n_rows = 100
z = 50

xs = np.linspace(0, 1_000, n_cols)

sine = np.sin(np.sqrt(xs))

data = np.dstack([np.vstack([sine * i for i in range(n_rows)]).astype(np.float32) * j for j in range(z)])

figure = fpl.Figure(cameras="3d", controller_types="orbit")

volume = figure[0, 0].add_image_volume(data)

figure.show()

# NOTE: fpl.loop.run() should not be used for interactive sessions
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
