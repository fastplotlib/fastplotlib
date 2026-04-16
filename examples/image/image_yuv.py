"""
YUV Image
=========

Example that shows how to use YUV images. Most videos are stored in this colorspace.
Y stores luma at full resolution, UV stores chroma values.
In yuv420p UV channels are stored at half the resolution of Y. In yuv444p, UV channels are stored
at full resolution.

YUV is also called YCbCr for digital images.

For more info: https://en.wikipedia.org/wiki/Y%E2%80%B2UV
"""

# test_example = true
# sphinx_gallery_pygfx_docs = 'screenshot'

import fastplotlib as fpl
import numpy as np
from skimage.color import rgb2ycbcr
import imageio.v3 as iio

# convert an rgb image to ycbcr for example purposes
img = iio.imread("imageio:astronaut.png")
img_yuv = rgb2ycbcr(img).astype(np.uint8)

y = img_yuv[..., 0]
u = img_yuv[::2, ::2, 1]
v = img_yuv[::2, ::2, 2]

figure = fpl.Figure(size=(700, 560))

# plot the image data
image = figure[0, 0].add_image_yuv(
    data=(y, u, v), colorspace="yuv420p", name="yuv image"
)

figure.show()


# NOTE: fpl.loop.run() should not be used for interactive sessions
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
