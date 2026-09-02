from contextlib import contextmanager
from typing import Callable, Iterable, Sequence

import numpy as np

from ._collection_base import GraphicCollection
from ._base import Graphic


@contextmanager
def pause_events(*graphics: Graphic, event_handlers: Iterable[Callable] = None):
    """
    Context manager for pausing Graphic events.

    Optionally pass in only specific event handlers which are blocked. Other events for the graphic will not be blocked.

    Examples
    --------

    .. code-block::

        # pass in any number of graphics
        with fpl.pause_events(graphic1, graphic2, graphic3):
            # enter context manager
            # all events are blocked from graphic1, graphic2, graphic3

        # context manager exited, event states restored.

    """
    if not all([isinstance(g, Graphic) for g in graphics]):
        raise TypeError(
            f"`pause_events` only takes Graphic instances as arguments, "
            f"you have passed the following types:\n{[type(g) for g in graphics]}"
        )

    original_vals = [g.block_events for g in graphics]

    for g in graphics:
        if event_handlers is not None:
            g.block_handlers.extend([e for e in event_handlers])
        else:
            g.block_events = True
    yield

    for g, value in zip(graphics, original_vals):
        if event_handlers is not None:
            g.block_handlers.clear()
        else:
            g.block_events = value


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

    pos = np.asarray(pos).ravel()

    if pos.shape != (2,) and pos.shape != (3,):
        raise TypeError(
            f"pos.shape must be (2,) or (3,), the shape of pos you have passed is: {pos.shape}"
        )

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
