from enum import IntEnum


class RenderQueue(IntEnum):
    # Defaults by PyGfx
    background = 1000
    opaque = 2000
    opaque_with_discard = 2400
    auto = 2600
    transparent = 3000
    overlay = 4000
    # For axes and selectors we use a higher render_queue, so they get rendered later than
    # the graphics. Axes (rulers) have depth_compare '<=' and selectors don't compare depth.
    axes = 3400  # still in 'object' group
    selector = 3600  # considered in 'overlay' group
