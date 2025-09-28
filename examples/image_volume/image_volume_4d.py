"""
Volume movie
============

View 4D data of a volume over time by updating the volume data.
"""

# test_example = false
# sphinx_gallery_pygfx_docs = 'animate 5s'

import numpy as np
from scipy.ndimage import gaussian_filter
import fastplotlib as fpl


def generate_data(
    p=1,
    noise=0.5,
    T=128,
    framerate=10,
    firerate=2.0,
):
    gamma = np.array([0.9])
    dims = (128, 128, 30)  # size of image
    sig = (4, 4, 2)  # neurons size
    bkgrd = 10
    N = 150  # number of neurons
    np.random.seed(0)
    centers = np.asarray(
        [[np.random.randint(s, x - s) for x, s in zip(dims, sig)] for i in range(N)]
    )
    Y = np.zeros((T,) + dims, dtype=np.float32)
    trueSpikes = np.random.rand(N, T) < firerate / float(framerate)
    trueSpikes[:, 0] = 0
    truth = trueSpikes.astype(np.float32)
    for i in range(2, T):
        if p == 2:
            truth[:, i] += gamma[0] * truth[:, i - 1] + gamma[1] * truth[:, i - 2]
        else:
            truth[:, i] += gamma[0] * truth[:, i - 1]
    for i in range(N):
        Y[:, centers[i, 0], centers[i, 1], centers[i, 2]] = truth[i]
    tmp = np.zeros(dims)
    tmp[tuple(np.array(dims) // 2)] = 1.0
    print("gaussing filtering")
    z = np.linalg.norm(gaussian_filter(tmp, sig).ravel())

    print("finishing")
    Y = (
        bkgrd
        + noise * np.random.randn(*Y.shape)
        + 10 * gaussian_filter(Y, (0,) + sig) / z
    )

    return Y


voldata = generate_data()

fig = fpl.Figure(cameras="3d", controller_types="orbit", size=(700, 560))

volume = fig[0, 0].add_image_volume(
    voldata[0],
    vmin=10,
    vmax=15,
    cmap="gnuplot2",
    alpha_mode="add",
)

hlut = fpl.HistogramLUTTool(voldata, volume)

fig[0, 0].docks["right"].size = 100
fig[0, 0].docks["right"].controller.enabled = False
fig[0, 0].docks["right"].add_graphic(hlut)
fig[0, 0].docks["right"].auto_scale(maintain_aspect=False)

fig.show()

# load a pre-saved camera state
state = {
    "position": np.array([-70, 90, 150]),
    "rotation": np.array([-0.09210227, -0.47460177, -0.05001713, 0.87393857]),
    "scale": np.array([1.0, 1.0, 1.0]),
    "reference_up": np.array([0.0, 1.0, 0.0]),
    "fov": 50.0,
    "width": 27.605629518746266,
    "height": 117.78401927998402,
    "depth": 183.4884192530962,
    "zoom": 0.75,
    "maintain_aspect": True,
    "depth_range": None,
}

fig[0, 0].camera.set_state(state)


i = 0
def update():
    global i

    volume.data = voldata[i]

    i += 1
    if i == voldata.shape[0]:
        i = 0


fig.add_animations(update)


# NOTE: fpl.loop.run() should not be used for interactive sessions
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
