from typing import Sequence

import numpy as np

from ...utils import mesh_masks
from ._base import GraphicFeature, FeatureEvent, block_reentrance


class LinearSelectionFeature(GraphicFeature):
    """
    **additional event attributes:**

    +--------------------+----------+------------------------------------+
    | attribute          | type     | description                        |
    +====================+==========+====================================+
    | get_selected_index | callable | returns indices under the selector |
    +--------------------+----------+------------------------------------+

    **info dict:**

    +----------+------------+-------------------------------+
    | dict key | value type | value description             |
    +==========+============+===============================+
    | value    | np.ndarray | new x or y value of selection |
    +----------+------------+-------------------------------+

    """

    def __init__(self, axis: str, value: float, limits: tuple[float, float]):
        """

        Parameters
        ----------
        axis: "x" | "y"
            axis the selector is restricted to

        value: float
            position of the slider in world space, NOT data space
        limits: (float, float)
            min, max limits of the selector

        """

        super().__init__()

        self._axis = axis
        self._limits = limits
        self._value = value

    @property
    def value(self) -> np.float32:
        """
        selection, data x or y value
        """
        return self._value

    @block_reentrance
    def set_value(self, selector, value: float):
        # clip value between limits
        value = np.clip(value, self._limits[0], self._limits[1], dtype=np.float32)

        # set position
        if self._axis == "x":
            dim = 0
        elif self._axis == "y":
            dim = 1

        for edge in selector._edges:
            edge.geometry.positions.data[:, dim] = value
            edge.geometry.positions.update_range()

        self._value = value

        event = FeatureEvent("selection", {"value": value})
        event.get_selected_index = selector.get_selected_index

        self._call_event_handlers(event)


class LinearRegionSelectionFeature(GraphicFeature):
    """
    **additional event attributes:**

    +----------------------+----------+------------------------------------+
    | attribute            | type     | description                        |
    +======================+==========+====================================+
    | get_selected_indices | callable | returns indices under the selector |
    +----------------------+----------+------------------------------------+
    | get_selected_data    | callable | returns data under the selector    |
    +----------------------+----------+------------------------------------+

    **info dict:**

    +----------+------------+-----------------------------+
    | dict key | value type | value description           |
    +==========+============+=============================+
    | value    | np.ndarray | new [min, max] of selection |
    +----------+------------+-----------------------------+

    """

    def __init__(self, value: tuple[int, int], axis: str, limits: tuple[float, float]):
        super().__init__()

        self._axis = axis
        self._limits = limits
        self._value = tuple(int(v) for v in value)

    @property
    def value(self) -> np.ndarray[float]:
        """
        (min, max) of the selection, in data space
        """
        return self._value

    @property
    def axis(self) -> str:
        """one of "x" | "y" """
        return self._axis

    @block_reentrance
    def set_value(self, selector, value: Sequence[float]):
        """
        Set start, stop range of selector

        Parameters
        ----------
        selector: LinearRegionSelector

        value: (float, float)
             (min, max) values in data space

        """
        if not len(value) == 2:
            raise TypeError(
                "selection must be a array, tuple, list, or sequence in the form of `(min, max)`, "
                "where `min` and `max` are numeric values."
            )

        # convert to array, clip values if they are beyond the limits
        value = np.asarray(value, dtype=np.float32).clip(*self._limits)

        # make sure `selector width >= 2`, left edge must not move past right edge!
        # or bottom edge must not move past top edge!
        if not (value[1] - value[0]) >= 0:
            return

        if self.axis == "x":
            # change left x position of the fill mesh
            selector.fill.geometry.positions.data[mesh_masks.x_left] = value[0]

            # change right x position of the fill mesh
            selector.fill.geometry.positions.data[mesh_masks.x_right] = value[1]

            # change x position of the left edge line
            selector.edges[0].geometry.positions.data[:, 0] = value[0]

            # change x position of the right edge line
            selector.edges[1].geometry.positions.data[:, 0] = value[1]

        elif self.axis == "y":
            # change bottom y position of the fill mesh
            selector.fill.geometry.positions.data[mesh_masks.y_bottom] = value[0]

            # change top position of the fill mesh
            selector.fill.geometry.positions.data[mesh_masks.y_top] = value[1]

            # change y position of the bottom edge line
            selector.edges[0].geometry.positions.data[:, 1] = value[0]

            # change y position of the top edge line
            selector.edges[1].geometry.positions.data[:, 1] = value[1]

        self._value = value

        # send changes to GPU
        selector.fill.geometry.positions.update_range()

        selector.edges[0].geometry.positions.update_range()
        selector.edges[1].geometry.positions.update_range()

        # send event
        if len(self._event_handlers) < 1:
            return

        event = FeatureEvent("selection", {"value": self.value})

        event.get_selected_indices = selector.get_selected_indices
        event.get_selected_data = selector.get_selected_data

        self._call_event_handlers(event)
        # TODO: user's selector event handlers can call event.graphic.get_selected_indices() to get the data index,
        #  and event.graphic.get_selected_data() to get the data under the selection
        #  this is probably a good idea so that the data isn't sliced until it's actually necessary


class RectangleSelectionFeature(GraphicFeature):
    """
    **additional event attributes:**

    +----------------------+----------+------------------------------------+
    | attribute            | type     | description                        |
    +======================+==========+====================================+
    | get_selected_indices | callable | returns indices under the selector |
    +----------------------+----------+------------------------------------+
    | get_selected_data    | callable | returns data under the selector    |
    +----------------------+----------+------------------------------------+

    **info dict:**

    +----------+------------+-------------------------------------------+
    | dict key | value type | value description                         |
    +==========+============+===========================================+
    | value    | np.ndarray | new [xmin, xmax, ymin, ymax] of selection |
    +----------+------------+-------------------------------------------+

    """

    def __init__(
        self,
        value: tuple[float, float, float, float],
        limits: tuple[float, float, float, float],
    ):
        super().__init__()

        self._limits = limits
        self._value = tuple(int(v) for v in value)

    @property
    def value(self) -> np.ndarray[float]:
        """
        (xmin, xmax, ymin, ymax) of the selection, in data space
        """
        return self._value

    @block_reentrance
    def set_value(self, selector, value: Sequence[float]):
        """
        Set the selection of the rectangle selector.

        Parameters
        ----------
        selector: RectangleSelector

        value: (float, float, float, float)
            new values (xmin, xmax, ymin, ymax) of the selection
        """
        if not len(value) == 4:
            raise TypeError(
                "Selection must be an array, tuple, list, or sequence in the form of `(xmin, xmax, ymin, ymax)`, "
                "where `xmin`, `xmax`, `ymin`, `ymax` are numeric values."
            )

        # convert to array
        value = np.asarray(value, dtype=np.float32)

        # clip values if they are beyond the limits
        value[:2] = value[:2].clip(self._limits[0], self._limits[1])
        # clip y
        value[2:] = value[2:].clip(self._limits[2], self._limits[3])

        xmin, xmax, ymin, ymax = value

        # make sure `selector width >= 2` and selector height >=2 , left edge must not move past right edge!
        # or bottom edge must not move past top edge!
        if not (xmax - xmin) >= 0 or not (ymax - ymin) >= 0:
            return

        # change fill mesh
        # change left x position of the fill mesh
        selector.fill.geometry.positions.data[mesh_masks.x_left] = xmin

        # change right x position of the fill mesh
        selector.fill.geometry.positions.data[mesh_masks.x_right] = xmax

        # change bottom y position of the fill mesh
        selector.fill.geometry.positions.data[mesh_masks.y_bottom] = ymin

        # change top position of the fill mesh
        selector.fill.geometry.positions.data[mesh_masks.y_top] = ymax

        # change the edge lines

        # each edge line is defined by two end points which are stored in the
        # geometry.positions
        # [x0, y0, z0]
        # [x1, y1, z0]

        # left line
        z = selector.edges[0].geometry.positions.data[:, -1][0]
        selector.edges[0].geometry.positions.data[:] = np.array(
            [[xmin, ymin, z], [xmin, ymax, z]]
        )

        # right line
        selector.edges[1].geometry.positions.data[:] = np.array(
            [[xmax, ymin, z], [xmax, ymax, z]]
        )

        # bottom line
        selector.edges[2].geometry.positions.data[:] = np.array(
            [[xmin, ymin, z], [xmax, ymin, z]]
        )

        # top line
        selector.edges[3].geometry.positions.data[:] = np.array(
            [[xmin, ymax, z], [xmax, ymax, z]]
        )

        # change the vertex positions

        # bottom left
        selector.vertices[0].geometry.positions.data[:] = np.array([[xmin, ymin, 1]])

        # bottom right
        selector.vertices[1].geometry.positions.data[:] = np.array([[xmax, ymin, 1]])

        # top left
        selector.vertices[2].geometry.positions.data[:] = np.array([[xmin, ymax, 1]])

        # top right
        selector.vertices[3].geometry.positions.data[:] = np.array([[xmax, ymax, 1]])

        self._value = value

        # send changes to GPU
        selector.fill.geometry.positions.update_range()

        for edge in selector.edges:
            edge.geometry.positions.update_range()

        for vertex in selector.vertices:
            vertex.geometry.positions.update_range()

        # send event
        if len(self._event_handlers) < 1:
            return

        event = FeatureEvent("selection", {"value": self.value})

        event.get_selected_indices = selector.get_selected_indices
        event.get_selected_data = selector.get_selected_data

        # calls any events
        self._call_event_handlers(event)
