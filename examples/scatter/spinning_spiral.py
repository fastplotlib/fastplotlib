"""
Spinning spiral scatter
=======================

Example of a spinning spiral scatter. Runs at 125 fps on an AMD RX 570.
"""

# test_example = false
# sphinx_gallery_pygfx_docs = 'animate 10s'

import numpy as np
import fastplotlib as fpl

# number of points
n = 1_000_000

# create data in the shape of a spiral
phi = np.linspace(0, 30, n)

xs = phi * np.cos(phi) + np.random.normal(scale=1.5, size=n)
ys = np.random.normal(scale=1, size=n)
zs = phi * np.sin(phi) + np.random.normal(scale=1.5, size=n)

data = np.column_stack([xs, ys, zs])

figure = fpl.Figure(
    cameras="3d",
    size=(700, 560),
    canvas_kwargs={"max_fps": 500, "vsync": False}
)

spiral = figure[0, 0].add_scatter(data, cmap="viridis_r", alpha=0.8)

jitter = np.random.normal(scale=0.01, size=n * 3).reshape((n, 3))


def update():
    # rotate around y axis
    spiral.rotate(0.005, axis="y")

    # add small jitter
    spiral.data[:] += jitter
    # shift array to provide a random-sampling effect
    # without re-running a random generator on each iteration
    jitter[1000:] = jitter[:-1000]
    jitter[:1000] = jitter[-1000:]


figure.add_animations(update)
figure.show()

# pre-saved camera state
camera_state = {
    'position': np.array([-0.13046005, 20.09142224, 29.03347696]),
    'rotation': np.array([-0.44485092,  0.05335406,  0.11586037,  0.88647469]),
    'scale': np.array([1., 1., 1.]),
    'reference_up': np.array([0., 1., 0.]),
    'fov': 50.0,
    'width': 62.725074768066406,
    'height': 8.856056690216064,
    'zoom': 0.75,
    'maintain_aspect': True,
    'depth_range': None
}

figure[0, 0].camera.set_state(camera_state)
figure[0, 0].axes.visible = False


if fpl.IMGUI:
    # show fps with imgui overlay
    figure.imgui_show_fps = True


# NOTE: `if __name__ == "__main__"` is NOT how to use fastplotlib interactively
# please see our docs for using fastplotlib interactively in ipython and jupyter
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
