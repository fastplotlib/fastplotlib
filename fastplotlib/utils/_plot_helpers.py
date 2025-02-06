from typing import Sequence

import numpy as np

from ..graphics._base import Graphic
from ..graphics._collection_base import GraphicCollection


def get_nearest_graphics_indices(
    pos: tuple[float, float] | tuple[float, float, float],
    graphics: Sequence[Graphic] | GraphicCollection,
) -> np.ndarray[int]:
    """
    Returns indices of the nearest ``graphics`` to the passed position ``pos`` in world space
    in order of closest to furtherst. Uses the distance between ``pos`` and the center of the
    bounding sphere for each graphic.

    Parameters
    ----------
    pos: (x, y) | (x, y, z)
        position in world space, z-axis is ignored when calculating L2 norms if ``pos`` is 2D

    graphics: Sequence, i.e. array, list, tuple, etc. of Graphic | GraphicCollection
        the graphics from which to return a sorted array of graphics in order of closest
        to furthest graphic

    Returns
    -------
    ndarray[int]
        indices of the nearest nearest graphics to ``pos`` in order

    """
    if isinstance(graphics, GraphicCollection):
        graphics = graphics.graphics

    if not all(isinstance(g, Graphic) for g in graphics):
        raise TypeError("all elements of `graphics` must be Graphic objects")

    pos = np.asarray(pos)

    if pos.shape != (2,) or not pos.shape != (3,):
        raise TypeError

    # get centers
    centers = np.empty(shape=(len(graphics), len(pos)))
    for i in range(centers.shape[0]):
        centers[i] = graphics[i].world_object.get_world_bounding_sphere()[: len(pos)]

    # l2
    distances = np.linalg.norm(centers[:, : len(pos)] - pos, ord=2, axis=1)

    sort_indices = np.argsort(distances)
    return sort_indices


def get_nearest_graphics(
    pos: tuple[float, float] | tuple[float, float, float],
    graphics: Sequence[Graphic] | GraphicCollection,
) -> np.ndarray[Graphic]:
    """
    Returns the nearest ``graphics`` to the passed position ``pos`` in world space.
    Uses the distance between ``pos`` and the center of the bounding sphere for each graphic.

    Parameters
    ----------
    pos: (x, y) | (x, y, z)
        position in world space, z-axis is ignored when calculating L2 norms if ``pos`` is 2D

    graphics: Sequence, i.e. array, list, tuple, etc. of Graphic | GraphicCollection
        the graphics from which to return a sorted array of graphics in order of closest
        to furthest graphic

    Returns
    -------
    ndarray[Graphic]
        nearest graphics to ``pos`` in order

    """
    sort_indices = get_nearest_graphics_indices(pos, graphics)
    return np.asarray(graphics)[sort_indices]
