"""
Line Stack
==========

Example showing how to plot a stack of lines
"""

# test_example = true
# sphinx_gallery_pygfx_docs = 'screenshot'

import numpy as np
import fastplotlib as fpl


xs = np.linspace(0, np.pi * 10, 100)
# sine wave
ys = np.sin(xs)

data = np.column_stack([xs, ys])
multi_data = np.stack([data] * 10)

figure = fpl.Figure(
    size=(700, 560),
    show_tooltips=True
)

line_stack = figure[0, 0].add_line_stack(
    multi_data,  # shape: (10, 100, 2), i.e. [n_lines, n_points, xy]
    cmap="jet",  # applied along n_lines
    thickness=5,
    separation=1,  # spacing between lines along the separation axis, default separation along "y" axis
)


def tooltip_info(ev):
    """A custom function to display the index of the graphic within the collection."""
    index = ev.pick_info["vertex_index"]  # index of the line datapoint being hovered

    # get index of the hovered line within the line stack
    line_index = np.where(line_stack.graphics == ev.graphic)[0].item()
    info = f"line index: {line_index}\n"

    # append data value info
    info += "\n".join(f"{dim}: {val}" for dim, val in zip("xyz", ev.graphic.data[index]))

    # return str to display in tooltip
    return info

# register the line stack with the custom tooltip function
figure.tooltip_manager.register(
    line_stack, custom_info=tooltip_info
)

figure.show(maintain_aspect=False)


# NOTE: `if __name__ == "__main__"` is NOT how to use fastplotlib interactively
# See the "JupyterLab and IPython" section in the user guide
if __name__ == "__main__":
    print(__doc__)
    fpl.loop.run()
