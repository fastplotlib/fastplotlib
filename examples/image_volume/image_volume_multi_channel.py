"""
Multi channel volumes
=====================

Example with multi-channel volume images. Use alpha_mode "add" for additive blending.
"""

# test_example = false
# run_example = false
# sphinx_gallery_pygfx_docs = 'code'

import fastplotlib as fpl
from ome_zarr.io import parse_url
from ome_zarr.reader import Reader


# load data
url = "https://uk1s3.embassy.ebi.ac.uk/idr/zarr/v0.5/idr0062A/6001240_labels.zarr"

# read the image data
reader = Reader(parse_url(url))
# first node is image data
image_node = next(reader())

dask_data = image_node.data

# use the highest resolution image in the pyramid zarr
voldata = dask_data[0]

figure = fpl.Figure(
    cameras="3d",
    controller_types="orbit",
    size=(700, 700)
)

# add first channel, use cyan colormap
vol_ch0 = figure[0, 0].add_image_volume(voldata[0], cmap="cyan", alpha_mode="add")
# add another channel, use magenta cmap
vol_ch1 = figure[0, 0].add_image_volume(voldata[1], cmap="magenta", alpha_mode="add")

figure.show()


# NOTE: fpl.loop.run() should not be used for interactive sessions
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
