"""
Scale image
===========

This examples illustrates the various spaces that you may need to map between,
plots an image to show these mappings.
"""

# test_example = True
# sphinx_gallery_pygfx_docs = 'screenshot'

import numpy as np
import fastplotlib as fpl

figure = fpl.Figure(size=(700, 560))

# an image to demonstrate some data in model/data space
image_data = np.array(
    [
        [0, 1, 2],
        [3, 4, 5],
        [5, 6, 7],
        [8, 9, 10],
    ]
)
image = figure[0, 0].add_image(image_data, cmap="turbo")


# a scatter that will be in the same space as the image
# used to indicates a few points on the image
scatter_data = np.array([[2, 3], [0, 1]])
scatter = figure[0, 0].add_scatter(
    scatter_data,
    sizes=15,
    colors=["blue", "red"],
)

# text to indicate the scatter point positions in all spaces
text_0 = figure[0, 0].add_text(
    text="",
    anchor="bottom-left",
    face_color="w",
    outline_color="k",
    outline_thickness=0.5,
)
text_1 = figure[0, 0].add_text(
    text="",
    anchor="bottom-left",
    face_color="w",
    outline_color="k",
    outline_thickness=0.5,
)


scaling = (2, 0.5, 1.0)  # scale (x, y, z)
image.scale = scaling
scatter.scale = scaling


def update_text():
    # get the position of the scatter points in world space
    # graphics can map from model <-> world space
    point_0_world = scatter.map_model_to_world(scatter.data[0])
    point_1_world = scatter.map_model_to_world(scatter.data[1])

    # text is always just set in world space
    text_0.offset = point_0_world
    text_1.offset = point_1_world

    # use subplot to map to world <-> screen space
    point_0_screen = figure[0, 0].map_world_to_screen(point_0_world)
    point_1_screen = figure[0, 0].map_world_to_screen(point_1_world)

    # set text to display model, world and screen space position of the 2 points
    text_0.text = (
        f"model pos: {scatter.data[0]}\n"
        f"world pos: {point_0_world}\n"
        f"screen pos: [{', '.join(str(round(p)) for p in point_0_screen)}]"
    )

    text_1.text = (
        f"model pos: {scatter.data[1]}\n"
        f"world pos: {point_1_world}\n"
        f"screen pos: [{', '.join(str(round(p)) for p in point_1_screen)}]"
    )


figure.add_animations(update_text)

figure.show()

fpl.loop.run()
