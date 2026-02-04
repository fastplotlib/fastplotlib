import numpy as np
import fastplotlib as fpl

xs = np.linspace(0, 10 * np.pi, 100)
ys = np.sin(xs)

data = np.column_stack([xs, ys])

fig = fpl.Figure(shape=(2, 2), size=(700, 700))

line = fig[0, 0].add_line(data)
text = fig[0, 0].add_text(f"n_points: {100}", offset=(0, 3, 0), anchor="middle-left")

scatter = fig[0, 1].add_scatter(
    np.random.rand(100, 3),
    colors=np.random.rand(100, 4),
    sizes=(np.random.rand(100) + 1) * 3,
    edge_colors=np.random.rand(100, 4),
    point_rotations=np.random.rand(100) * 180,
    uniform_size=False,
    uniform_edge_color=False,
    point_rotation_mode="vertex",
)

fig.show()

i = 0


def update():
    global i

    # update line
    freq = (np.sin(i) + 1) * 5
    n_points = int((freq * 50_000) + 10)

    xs = np.linspace(0, 10 * np.pi, n_points)
    ys = np.sin(xs * freq)
    new_data = np.column_stack([xs, ys])

    line.data = new_data

    # update scatter
    scatter.data = np.random.rand(n_points, 3)
    scatter.colors = np.random.rand(n_points, 4)

    i += 0.01
    text.text = f"n_points: {n_points}"


fig.add_animations(update)

fpl.loop.run()
