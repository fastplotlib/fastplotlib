from copy import deepcopy
from typing import *

import numpy as np
import pygfx


def emulate_pointer_movement(
        renderer: pygfx.WgpuRenderer,
        start_position: np.ndarray,  # in screen coordinates
        end_position: np.ndarray,  # in screen coordinates
        n_steps: int = 100,
        button: int = 1,
        modifiers: List[str] = None,
        check_target: pygfx.WorldObject = None
) -> pygfx.WorldObject:
    """
    Emulate a pointer_down -> pointer_move -> pointer_up event series.

    Parameters
    ----------
    renderer: pygfx.WgpuRenderer
        the renderer

    start_position: np.ndarray
        start position of pointer event, [x, y, z] in screen coordinates

    end_position: np.ndarray
        end position of pointer event, [x, y, z] in screen coordinates

    n_steps: int, default 100
        number of pointer_move events between pointer_down and pointer_up

    button: int
        pointer button to emulate
        1: left
        2:
    modifiers: List[str]
        modifiers, "Shift", "Alt", etc.

    check_target: pygfx.WorldObject, optional
        if provided, asserts that the pointer_down event targets the provided `check_target`

    Returns
    -------
    Union[pygfx.WorldObject, None]
        The world object that was interacted with the pointer events.
        ``None`` if no world object was interacted with.

    """
    if modifiers is None:
        modifiers = list()

    # instead of manually defining the target
    # use get_pick_info to make sure the target is pickable!
    pick_info = renderer.get_pick_info(start_position)

    if check_target is not None:
        assert pick_info["world_object"] is check_target

    # start and stop positions
    x1, y1 = start_position[:2]
    xn, yn = end_position[:2]

    # create event info dict
    event_info = {
        "x": x1,
        "y": y1,
        "modifiers": modifiers,
        "button": button,
        "buttons": [button],
    }

    # pointer down event
    pointer_down = pygfx.PointerEvent(
        type="pointer_down",
        target=pick_info["world_object"],
        **event_info
    )

    # pointer move event, xy will be set per step
    pointer_move = pygfx.PointerEvent(
        type="pointer_move",
        **event_info
    )

    # create event info for pointer_up event to end the emulation
    event_info = deepcopy(event_info)
    event_info["x"], event_info["y"] = end_position

    event_info = deepcopy(event_info)

    pointer_up = pygfx.PointerEvent(
        type="pointer_up",
        **event_info
    )

    # start emulating the event series
    renderer.dispatch_event(pointer_down)

    x_steps = np.linspace(x1, xn, n_steps)
    y_steps = np.linspace(y1, yn, n_steps)

    # the pointer move events, move uniformly between start_position and end_position
    for dx, dy in zip(x_steps, y_steps):
        pointer_move.x = dx
        pointer_move.dy = dy

        # move the pointer by dx, dy
        renderer.dispatch_event(pointer_move)

    # end event emulation
    renderer.dispatch_event(pointer_up)

    return pick_info["world_object"]
