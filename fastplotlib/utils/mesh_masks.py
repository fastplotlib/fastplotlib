import numpy as np


"""
positions for indexing the BoxGeometry to set the "width" and "size" of the box
hacky, but I don't think we can morph meshes in pygfx yet: https://github.com/pygfx/pygfx/issues/346
"""

x_right = np.array(
    [
        True,
        True,
        True,
        True,
        False,
        False,
        False,
        False,
        False,
        True,
        False,
        True,
        True,
        False,
        True,
        False,
        False,
        True,
        False,
        True,
        True,
        False,
        True,
        False,
    ]
)

x_left = np.array(
    [
        False,
        False,
        False,
        False,
        True,
        True,
        True,
        True,
        True,
        False,
        True,
        False,
        False,
        True,
        False,
        True,
        True,
        False,
        True,
        False,
        False,
        True,
        False,
        True,
    ]
)

y_top = np.array(
    [
        False,
        True,
        False,
        True,
        False,
        True,
        False,
        True,
        True,
        True,
        True,
        True,
        False,
        False,
        False,
        False,
        False,
        False,
        True,
        True,
        False,
        False,
        True,
        True,
    ]
)

y_bottom = np.array(
    [
        True,
        False,
        True,
        False,
        True,
        False,
        True,
        False,
        False,
        False,
        False,
        False,
        True,
        True,
        True,
        True,
        True,
        True,
        False,
        False,
        True,
        True,
        False,
        False,
    ]
)

x_right = (x_right, 0)
x_left = (x_left, 0)
y_top = (y_top, 1)
y_bottom = (y_bottom, 1)
