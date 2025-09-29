from enum import IntEnum


class RenderQueue(IntEnum):
    # Defaults by PyGfx
    background = 1000
    opaque = 2000
    opaque_with_discard = 2400
    auto = 2600
    transparent = 3000
    overlay = 4000
    # For selectors we use a render_queue of 3500, which is at the end of what is considered the group of transparent objects.
    # So it's rendered later than the normal scene (2000 - 3000), but before overlays like legends and tooltips.
    selector = 3500
