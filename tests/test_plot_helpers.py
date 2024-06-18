import numpy as np
import fastplotlib as fpl


def make_circle(center, radius: float, n_points: int = 75) -> np.ndarray:
    theta = np.linspace(0, 2 * np.pi, n_points)
    xs = radius * np.sin(theta)
    ys = radius * np.cos(theta)

    return np.column_stack([xs, ys]) + center


def test_get_nearest_graphics():
    circles = list()

    centers = [[0, 0], [0, 20], [20, 0], [20, 20]]

    for center in centers:
        circles.append(make_circle(center, 5, n_points=75))

    fig = fpl.Figure()

    lines = fig[0, 0].add_line_collection(circles, cmap="jet", thickness=5)

    fig[0, 0].add_scatter(np.array([[0, 12, 0]]))

    # check distances
    nearest = fpl.utils.get_nearest_graphics((0, 12), lines)
    assert nearest[0] is lines[1]  # closest
    assert nearest[1] is lines[0]
    assert nearest[2] is lines[3]
    assert nearest[3] is lines[2]  # furthest
    assert nearest[-1] is lines[2]
