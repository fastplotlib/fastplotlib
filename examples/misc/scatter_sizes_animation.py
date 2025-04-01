"""
Scatter sizes animation
=======================

Animate scatter sizes
"""

# test_example = false
# sphinx_gallery_pygfx_docs = 'animate 6s'

import numpy as np
import fastplotlib as fpl

xs = np.linspace(0, 10 * np.pi, 1_000)
# sine wave
ys = np.sin(xs)
data = np.column_stack([xs, ys])

sizes = np.abs(ys) * 5

figure = fpl.Figure(size=(700, 560))

figure[0, 0].add_scatter(data, sizes=sizes, name="sine")


i = 0


def update_sizes(subplot):
    global i

    xs = np.linspace(0.1 * i, (10 * np.pi) + (0.1 * i), 1_000)
    sizes = np.abs(np.sin(xs)) * 5

    subplot["sine"].sizes = sizes

    i += 1


figure[0, 0].add_animations(update_sizes)

figure.show(maintain_aspect=False)


# NOTE: `if __name__ == "__main__"` is NOT how to use fastplotlib interactively
# please see our docs for using fastplotlib interactively in ipython and jupyter
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
