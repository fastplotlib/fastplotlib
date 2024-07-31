from contextlib import contextmanager

from ._base import Graphic


@contextmanager
def pause_events(*graphics: Graphic):
    """
    Context manager for pausing Graphic events.

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
        g.block_events = True
    yield

    for g, value in zip(graphics, original_vals):
        g.block_events = value
