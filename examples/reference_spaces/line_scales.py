import numpy as np
import fastplotlib as fpl


xs = np.linspace(0, 10 * np.pi, 1000)
ys = np.sin(xs)

ys100 = ys * 1000

l1 = np.column_stack([xs, ys])
l2 = np.column_stack([xs, ys100])

fig = fpl.Figure(size=(500, 400))

fig[0, 0].add_line(l1)
fig.show(maintain_aspect=False)
fig[0, 0].auto_scale(zoom=0.4)

rs = fig[0, 0].add_reference_space(scale=(1, 500, 1))
l2 = fig[0, 0].add_line(l2, reference_space=rs, colors="r")
l2.add_axes(rs)
l2.axes.y.line.material.color = "r"

fpl.loop.run()
