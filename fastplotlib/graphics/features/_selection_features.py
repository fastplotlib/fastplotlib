from typing import Sequence

import numpy as np
import pygfx as gfx

from ...utils import mesh_masks
from ._base import GraphicFeature, GraphicFeatureEvent, block_reentrance
from ...utils.triangulation import triangulate


class LinearSelectionFeature(GraphicFeature):
    event_info_spec = [
        {
            "dict key": "value",
            "type": "float",
            "description": "new x or y value of selection",
        },
    ]

    event_extra_attrs = [
        {
            "attribute": "get_selected_index",
            "type": "callable",
            "description": "returns index under the selector",
        }
    ]

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

        event = GraphicFeatureEvent("selection", {"value": value})
        event.get_selected_index = selector.get_selected_index

        self._call_event_handlers(event)


class LinearRegionSelectionFeature(GraphicFeature):
    event_info_spec = [
        {
            "dict key": "value",
            "type": "np.ndarray",
            "description": "new [min, max] of selection",
        },
    ]

    event_extra_attrs = [
        {
            "attribute": "get_selected_indices",
            "type": "callable",
            "description": "returns indices under the selector",
        },
        {
            "attribute": "get_selected_data",
            "type": "callable",
            "description": "returns data under the selector",
        },
    ]

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
            selector._edges[0].geometry.positions.data[:, 0] = value[0]

            # change x position of the right edge line
            selector._edges[1].geometry.positions.data[:, 0] = value[1]

        elif self.axis == "y":
            # change bottom y position of the fill mesh
            selector.fill.geometry.positions.data[mesh_masks.y_bottom] = value[0]

            # change top position of the fill mesh
            selector.fill.geometry.positions.data[mesh_masks.y_top] = value[1]

            # change y position of the bottom edge line
            selector._edges[0].geometry.positions.data[:, 1] = value[0]

            # change y position of the top edge line
            selector._edges[1].geometry.positions.data[:, 1] = value[1]

        self._value = value

        # send changes to GPU
        selector.fill.geometry.positions.update_range()

        selector._edges[0].geometry.positions.update_range()
        selector._edges[1].geometry.positions.update_range()

        # send event
        if len(self._event_handlers) < 1:
            return

        event = GraphicFeatureEvent("selection", {"value": self.value})

        event.get_selected_indices = selector.get_selected_indices
        event.get_selected_data = selector.get_selected_data

        self._call_event_handlers(event)
        # TODO: user's selector event handlers can call event.graphic.get_selected_indices() to get the data index,
        #  and event.graphic.get_selected_data() to get the data under the selection
        #  this is probably a good idea so that the data isn't sliced until it's actually necessary


class RectangleSelectionFeature(GraphicFeature):
    event_info_spec = [
        {
            "dict key": "value",
            "type": "np.ndarray",
            "description": "new [xmin, xmax, ymin, ymax] of selection",
        },
    ]

    event_extra_attrs = [
        {
            "attribute": "get_selected_indices",
            "type": "callable",
            "description": "returns indices under the selector",
        },
        {
            "attribute": "get_selected_data",
            "type": "callable",
            "description": "returns data under the selector",
        },
    ]

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

        event = GraphicFeatureEvent("selection", {"value": self.value})

        event.get_selected_indices = selector.get_selected_indices
        event.get_selected_data = selector.get_selected_data

        # calls any events
        self._call_event_handlers(event)


class PolygonSelectionFeature(GraphicFeature):
    event_info_spec = [
        {
            "dict key": "value",
            "type": "np.ndarray",
            "description": "new array of points that represents the polygon selection",
        },
    ]

    event_extra_attrs = [
        {
            "attribute": "get_selected_indices",
            "type": "callable",
            "description": "returns indices under the selector",
        },
        {
            "attribute": "get_selected_data",
            "type": "callable",
            "description": "returns data under the selector",
        },
    ]

    def __init__(
        self,
        value: Sequence[tuple[float]],
        limits: tuple[float, float, float, float],
    ):
        super().__init__()

        self._limits = limits
        self._value = np.asarray(value).reshape(-1, 3).astype(float)

    @property
    def value(self) -> np.ndarray[float]:
        """
        The array of the polygon, in data space
        """
        return self._value

    @block_reentrance
    def set_value(self, selector, value: Sequence[tuple[float]]):
        """
        Set the selection of the rectangle selector.

        Parameters
        ----------
        selector: PolygonSelector

        value: array
            new values (3D points) of the selection
        """

        value = np.asarray(value, dtype=np.float32)

        if not value.shape[1] == 3:
            raise TypeError(
                "Selection must be an array, tuple, list, or sequence of the shape Nx3."
            )

        # clip values if they are beyond the limits
        value[:, 0] = value[:, 0].clip(self._limits[0], self._limits[1])
        value[:, 1] = value[:, 1].clip(self._limits[2], self._limits[3])

        self._value = value

        if len(value) >= 3:
            indices = triangulate(value)
        else:
            indices = np.zeros((0, 3), np.int32)

        geometry = selector.geometry

        # Need larger buffer?
        if len(value) > geometry.positions.nitems:
            arr = np.zeros((geometry.positions.nitems * 2, 3), np.float32)
            geometry.positions = gfx.Buffer(arr)
        if len(indices) > geometry.indices.nitems:
            arr = np.zeros((geometry.indices.nitems * 2, 3), np.int32)
            geometry.indices = gfx.Buffer(arr)

        geometry.positions.data[: len(value)] = value
        geometry.positions.data[len(value) :] = value[-1] if len(value) else (0, 0, 0)
        geometry.positions.draw_range = 0, len(value)
        geometry.positions.update_full()

        geometry.indices.data[: len(indices)] = indices
        geometry.indices.data[len(indices) :] = 0
        geometry.indices.draw_range = 0, len(indices)
        geometry.indices.update_full()

        # send event
        if len(self._event_handlers) < 1:
            return

        event = GraphicFeatureEvent("selection", {"value": self.value})

        event.get_selected_indices = selector.get_selected_indices
        event.get_selected_data = selector.get_selected_data

        # calls any events
        self._call_event_handlers(event)
