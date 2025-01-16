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
import imageio.v3 as iio

image = iio.imread("imageio:camera.png")

# compute discrete fourier transform of image
img_fft = np.fft.fftshift(np.fft.fft2(image))

# image to just visualize absolute magnitudes
log_abs_img_fft = np.log(np.abs(img_fft + 1))

# placeholders for displaying fft and inverse fft of selections
zeros = np.zeros(image.shape)

# create an ImageWidget to display all the images
iw = fpl.ImageWidget(
    data=[image, log_abs_img_fft, zeros, zeros, zeros, zeros],
    names=["image", "DFT", "selected", "FFT of selected", "not-selected", "IFFT of not-selected"],
    figure_shape=(3, 2),  # so we can see image and fft side by side
    figure_kwargs={"size": (700, 1024)},
    histogram_widget=False,
)

# we don't need the toolbars here, unclutter the figure
for subplot in iw.figure:
    subplot.toolbar = False

# viridis cmap for the fft images
iw.cmap = "viridis"

# gray for the non-fft images
iw.managed_graphics[0].cmap = "gray"
iw.managed_graphics[3].cmap = "gray"
iw.managed_graphics[-1].cmap = "gray"

# set contrast limits based on the full DFT for the DFT-selection images
iw.figure["selected"].graphics[0].vmin, iw.figure["selected"].graphics[0].vmax = log_abs_img_fft.min(), log_abs_img_fft.max()
iw.figure["not-selected"].graphics[0].vmin, iw.figure["not-selected"].graphics[0].vmax = log_abs_img_fft.min(), log_abs_img_fft.max()

iw.show()

# create a rectangle selector
rs = iw.managed_graphics[1].add_rectangle_selector(edge_color="w", edge_thickness=2.0)


@rs.add_event_handler("selection")
def update_images(ev):
    """
    Updates the images when the selection changes
    """

    # get the bbox of the selection
    row_ixs, col_ixs = ev.get_selected_indices()
    row_slice = slice(row_ixs[0], row_ixs[-1] + 1)
    col_slice = slice(col_ixs[0], col_ixs[-1] + 1)

    # fft of the selection
    selected_fft = np.zeros(image.shape, dtype=np.complex64)
    selected_fft[row_slice, col_slice] = img_fft[row_slice, col_slice]

    # update image graphic with the current fft selection
    iw.managed_graphics[2].data = np.log(np.abs(selected_fft + 1))

    # inverse fft to reconstruct image using only the selection
    iw.managed_graphics[3].data = np.fft.ifft2(np.fft.fftshift(selected_fft))
    iw.managed_graphics[3].reset_vmin_vmax()

    # fft of the region outside the selection
    unselected_fft = img_fft.copy()
    unselected_fft[row_slice, col_slice] = 0

    # update image graphic with unselected fft area
    iw.managed_graphics[4].data = np.log(np.abs(unselected_fft + 1))

    # inverse fft to reconstruct image using only the unselected part of the fft
    iw.managed_graphics[5].data = np.fft.ifft2(np.fft.fftshift(unselected_fft))
    iw.managed_graphics[5].reset_vmin_vmax()


# set initial selection to the center
rs.selection = (225, 285, 225, 285)


figure = iw.figure

# NOTE: `if __name__ == "__main__"` is NOT how to use fastplotlib interactively
# please see our docs for using fastplotlib interactively in ipython and jupyter
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
