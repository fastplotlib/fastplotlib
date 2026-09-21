"""
NDWidget vector field
=====================

Streamlines of a vector field given as an equation rather than as data. The field is a function of
four variables, two of them are drawn and the other two get sliders, and zooming in resamples the
field so that the streamline density stays the same on screen.
"""

# test_example = false
# sphinx_gallery_pygfx_docs = 'screenshot'

import numpy as np
import fastplotlib as fpl


def field(x, y, t, ripple):
    """
    A large scale flow with a small scale ripple on top of it.

    The display dims arrive as arrays of the grid sample coordinates and the slider dims as scalars,
    so this is called as ``field(x=<[n] array>, y=<[n] array>, t=0.0, ripple=0.4)``. It returns one
    component per display dim.
    """
    u = -1 - x**2 + y + ripple * np.sin(20 * y + t)
    v = 1 + x - y**2 + ripple * np.sin(20 * x - t)

    return u, v


# only the dims that are not drawn need a reference range, x and y are sampled from `extents` below
ndw = fpl.NDWidget(
    ranges={"t": (0.0, 2 * np.pi, 0.05), "ripple": (0.0, 1.5, 0.01)},
    size=(700, 700),
)

nd_field = ndw[0, 0].add_nd_field(
    field,
    ("x", "y", "t", "ripple"),  # every variable of the field
    ("x", "y"),  # the 2 dims that are visualized, everything else becomes a slider
    extents={"x": (-5, 5), "y": (-5, 5)},  # the region the field is sampled over
    resolution=24,  # samples along each of x and y, held constant as you zoom
    # follow the camera, in steps of a factor of 2 in zoom. the number of samples stays the same and
    # the region shrinks, so zooming in resolves the ripple that the coarse grid steps straight over
    extents_mode="auto",
    graphic_kwargs={
        "cmap": "viridis",
        # each zoom level would otherwise take its range from the magnitudes in its own grid, and
        # the colors would mean something different at every level
        "cmap_range": (0, 18),
    },
    name="field",
)

# streamlines are placed again on every update, which is slow enough to notice when playing back a
# slider. an arrow per sample is much cheaper:
# nd_field.graphic_type = fpl.VectorsGraphic

figure = ndw.figure

ndw.show()


# NOTE: fpl.loop.run() should not be used for interactive sessions
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
