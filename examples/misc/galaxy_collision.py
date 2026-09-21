"""
Galaxy Collision Example
========================

Example showing galaxy collision.
"""

# test_example = false
# sphinx_gallery_pygfx_docs = 'animate 8s'

import numpy as np
import fastplotlib as fpl


figure = fpl.Figure(size=(700, 560), cameras=["3d"])


# NOTE: `if __name__ == "__main__"` is NOT how to use fastplotlib interactively
# please see our docs for using fastplotlib interactively in ipython and jupyter
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()