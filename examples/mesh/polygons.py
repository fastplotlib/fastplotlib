"""
Polygons
======================

An example with polygons.

"""

# test_example = True
# sphinx_gallery_pygfx_docs = 'screenshot'

import fastplotlib as fpl
import numpy as np
from cmap import Colormap

figure = fpl.Figure(size=(700, 560))


def make_circle(center, radius: float, n_points: int = 75) -> np.ndarray:
    theta = np.linspace(0, 2 * np.pi, n_points, endpoint=False)
    xs = radius * np.sin(theta)
    ys = radius * np.cos(theta)

    return np.column_stack([xs, ys]) + np.asarray(center)[None]


circle_data = make_circle(center=(0, 0), radius=5)
octogon_data = make_circle(center=(15, 0), radius=7, n_points=8)

rectangle_data = np.array([[10, 10], [15, 10], [15, 15], [10, 15]])

triangle_data = np.array(
    [
        [0, 10],
        [5, 10],
        [2.5, 15],
        [0, 10],
    ]
)


figure[0, 0].add_polygon(circle_data, name="circle")
figure[0, 0].add_polygon(octogon_data, colors=Colormap("jet").lut(8), name="octogon")
figure[0, 0].add_polygon(
    rectangle_data, colors=["r", "r", "cyan", "y"], name="rectangle"
)
figure[0, 0].add_polygon(triangle_data, colors="m")

figure.show()

fpl.loop.run()
