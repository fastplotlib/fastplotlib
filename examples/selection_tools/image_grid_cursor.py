"""
Grid of images with a cursor
============================

Example showing a grid of images in a single subplot and an interactive cursor
that marks the same position in each image
"""

# test_example = false
# sphinx_gallery_pygfx_docs = 'screenshot'

import fastplotlib as fpl
import numpy as np


figure = fpl.Figure(size=(700, 560))

# make 12 images
images = np.random.rand(12, 100, 100)

# we will display 3 rows and 4 columns
rows = 3
columns = 4

# spacing between each image
spacing = 25

# interactive cursor
cursor = fpl.Cursor(size=15, color="magenta")

index = 0
for i in range(rows):
    for j in range(columns):
        img = images[index]
        # offset is x, y, z position
        offset = (j * img.shape[1] + spacing * j, i * img.shape[0] + spacing * i, 0)
        img_graphic = figure[0, 0].add_image(img, cmap="viridis", offset=offset)
        cursor.add(img_graphic)

        text_label = figure[0, 0].add_text(
            str(index),
            face_color="r",
            font_size=25,
            outline_color="w",
            outline_thickness=0.05,
            anchor="bottom-right",
            offset=offset
        )

        index += 1

figure.show()


# NOTE: `if __name__ == "__main__"` is NOT how to use fastplotlib interactively
# please see our docs for using fastplotlib interactively in ipython and jupyter
if __name__ == "__main__":
    print(__doc__)
    fpl.run()
