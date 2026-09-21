"""
NDWidget YUV Video
==================

Browse videos with an ``NDWidget``. ``add_video`` uploads the YUV planes directly to the GPU with no local copy,
rather than converting every frame to RGB first.

Fetching is asynchronous. An ``NDWidget`` reads each slice on a thread pool and awaits the resulting ``Future``
on the canvas event loop, so a decode never blocks the render loop and several videos can play at once. Each
``asyncvideo`` reader decodes in its own worker process, so the two here decode in parallel.

Both subplots show the same cockatoo video, in the two colorspaces it is shipped in. yuv420p stores the U and V
planes at half resolution in each direction, yuv444p stores them at full resolution. The subplots are linked, so
zoom into an edge where the color changes rapidly over space to see the difference.
"""

# test_example = false
# sphinx_gallery_pygfx_docs = 'code'

import fastplotlib as fpl
from asyncvideo import AsyncVideoReader
from imageio.core import Request


# imageio ships the same video in both colorspaces, `Request` resolves them to local paths
paths = {
    "yuv420p": Request("imageio:cockatoo_yuv420.mp4", "r").get_local_filename(),
    "yuv444p": Request("imageio:cockatoo.mp4", "r").get_local_filename(),
}

# one worker process per reader, `time` is the timestamp of every frame in seconds
videos = {name: AsyncVideoReader(path, buffer_size=64) for name, path in paths.items()}

# reference space is seconds, one step per frame. both encodes share the same clock
time = videos["yuv420p"].time
ranges = {"time": (time[0], time[-1], time[1] - time[0])}

ndw = fpl.NDWidget(
    ranges=ranges,
    shape=(1, 2),
    names=list(videos.keys()),
    controller_ids="sync",
    size=(700, 400),
)

for name, video in videos.items():
    ndw[name].add_video(
        video,
        dims=("time", "m", "n"),
        display_dims=("m", "n"),
        colorspace=video.colorspace,
        slider_maps={"time": video.time},
        name="video",
    )
    # neither the pixel values nor a row/col axis are interesting for a video
    ndw[name].subplot.tooltip.enabled = False
    ndw[name].subplot.axes.visible = False

ndw.show()

figure = ndw.figure


# NOTE: fpl.loop.run() should not be used for interactive sessions
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
