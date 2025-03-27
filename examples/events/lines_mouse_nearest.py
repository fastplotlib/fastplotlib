"""
Highlight nearest circle
========================

Shows how to use the "pointer_move" event to get the nearest circle and highlight it.

"""

from itertools import product
import numpy as np
import fastplotlib as fpl
import pygfx


def make_circle(center, radius: float, n_points: int) -> np.ndarray:
    theta = np.linspace(0, 2 * np.pi, n_points)
    xs = radius * np.cos(theta)
    ys = radius * np.sin(theta)

    return np.column_stack([xs, ys]) + center

spatial_dims = (100, 100)

circles = list()
for center in product(range(0, spatial_dims[0], 15), range(0, spatial_dims[1], 15)):
    circles.append(make_circle(center, 5, n_points=75))

pos_xy = np.vstack(circles)

figure = fpl.Figure(size=(700, 560))

line_collection = figure[0, 0].add_line_collection(circles, colors="w", thickness=5)


@figure.renderer.add_event_handler("pointer_move")
def highlight_nearest(ev: pygfx.PointerEvent):
    line_collection.colors = "w"

    pos = figure[0, 0].map_screen_to_world(ev)
    if pos is None:
        return

    # get_nearest_graphics() is a helper function
    # sorted the passed array or collection of graphics from nearest to furthest from the passed `pos`
    nearest = fpl.utils.get_nearest_graphics(pos, line_collection)[0]

    nearest.colors = "r"


# remove clutter
figure[0, 0].axes.visible = False

figure.show()

# NOTE: `if __name__ == "__main__"` is NOT how to use fastplotlib interactively
# please see our docs for using fastplotlib interactively in ipython and jupyter
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
