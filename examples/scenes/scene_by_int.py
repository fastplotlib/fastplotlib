"""
Specify Scene IDs with integers
=========================

Share scenes between subplots using integer IDs
"""
# derived from specify_integers.py

# test_example = false
# sphinx_gallery_pygfx_docs = 'screenshot'

import numpy as np
import fastplotlib as fpl


xs = np.linspace(0, 2 * np.pi, 100)
sine = np.sin(xs)
cosine = np.cos(xs)

# scene IDs
# one scene is created for each unique ID
# if the IDs are the same, those subplots will present the same scene
ids = [
    [0, 1],
    [2, 0],
]

figure = fpl.Figure(
    shape=(2, 2),
    scene_ids=ids,
    size=(700, 560),
)

for subplot, scene_id in zip(figure, np.asarray(ids).ravel()):
    subplot.title = f"scene id: {scene_id}"

figure[0, 0].add_line(np.column_stack([xs, sine]))

figure[0, 1].add_line(np.random.rand(100))
figure[1, 0].add_line(np.random.rand(100))

# since we the scene from [0,0], we don't need add anything here
# in fact adding something here would add it to both.
# figure[1, 1].add_line(np.column_stack([xs, cosine]))

figure[1, 1].axes.visible = False  # hide axes as this is a tad silly.


figure.show(maintain_aspect=False)


# NOTE: fpl.loop.run() should not be used for interactive sessions
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
