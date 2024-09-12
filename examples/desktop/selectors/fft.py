"""
Explore fourier transform of images
===================================
Example showing how to use a `RectangleSelector` to interactively reconstruct
an image using portions of it fourier transform
"""

# test_example = false
# sphinx_gallery_pygfx_docs = 'screenshot'

import numpy as np
import fastplotlib as fpl
import scipy
import imageio.v3 as iio

image = iio.imread("imageio:camera.png")

# compute discrete fourier transform of image
dft = scipy.fftpack.fft2(image)

# image to just visualize absolute magnitudes
log_abs_dft = np.log(np.abs(dft))

# placeholders for displaying fft and inverse fft of selections
zeros = np.zeros(image.shape)

# create an ImageWidget to display all the images
iw = fpl.ImageWidget(
    data=[image, log_abs_dft, zeros, zeros, zeros, zeros],
    names=["image", "DFT", "selected", "IDFT of selected", "not-selected", "IDFT of not-selected"],
    figure_shape=(3, 2),  # so we can see image and fft side by side
    figure_kwargs={"size": (600, 900)},
    histogram_widget=False,
)

# set contrast limits based on the full DFT for the DFT-selection images
iw.figure["selected"].graphics[0].vmin, iw.figure["selected"].graphics[0].vmax = log_abs_dft.min(), log_abs_dft.max()
iw.figure["not-selected"].graphics[0].vmin, iw.figure["not-selected"].graphics[0].vmax = log_abs_dft.min(), log_abs_dft.max()

iw.show()

# create a rectangle selector
rs = iw.managed_graphics[1].add_rectangle_selector()


@rs.add_event_handler("selection")
def update_images(ev):
    """
    Updates the images when the selection changes
    """

    # get the bbox of the selection
    ixs = ev.get_selected_indices()
    r0, r1 = ixs[1][0], ixs[1][-1]
    c0, c1 = ixs[0][0], ixs[0][-1]

    # fft of the selection
    selected_fft = np.zeros(image.shape, dtype=np.complex64)
    selected_fft[r0:r1, c0:c1] = dft[r0:r1, c0:c1]

    # update image graphic with the current fft selection
    iw.managed_graphics[2].data = np.log(np.abs(selected_fft))

    # inverse fft to reconstruct image using only the selection
    iw.managed_graphics[3].data = scipy.fftpack.ifft2(selected_fft)
    iw.managed_graphics[3].reset_vmin_vmax()

    # fft of the region outside the selection
    unselected_fft = dft.copy()
    unselected_fft[r0:r1, c0:c1] = 0

    # update image graphic with unselected fft area
    iw.managed_graphics[4].data = np.log(np.abs(unselected_fft))

    # inverse fft to reconstruct image using only the unselected part of the fft
    iw.managed_graphics[5].data = scipy.fftpack.ifft2(unselected_fft)
    iw.managed_graphics[5].reset_vmin_vmax()


# set initial selection to top right corner
rs.selection = (400, 512, 0, 100)


figure = iw.figure

# NOTE: `if __name__ == "__main__"` is NOT how to use fastplotlib interactively
# please see our docs for using fastplotlib interactively in ipython and jupyter
if __name__ == "__main__":
    print(__doc__)
    fpl.run()
