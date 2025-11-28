"""
Simple surface
==============

Example showing a surface mesh
"""

# test_example = true
# sphinx_gallery_pygfx_docs = 'screenshot'

import fastplotlib as fpl
import numpy as np
import pygfx as gfx


figure = fpl.Figure(size=(700, 560), cameras='3d', controller_types='orbit')


t = np.linspace(0, 6, 100).astype(np.float32)
x = np.sin(t)
y = np.cos(t*2)
z = (x.reshape(1, -1) * x.reshape(-1, 1)) * 50  # 100x100


mesh = figure[0, 0].add_surface(z, colors="magenta", cmap='jet')


# figure[0, 0].axes.grids.xy.visible = True
figure[0, 0].camera.show_object(mesh.world_object, (-2, 2, -3), up=(0, 0, 1))
figure.show()


# NOTE: fpl.loop.run() should not be used for interactive sessions
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
