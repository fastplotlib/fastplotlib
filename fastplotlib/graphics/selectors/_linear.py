import math
from numbers import Real
from typing import Sequence

import numpy as np
import pygfx

from .._base import Graphic
from .._collection_base import GraphicCollection
from .._features._selection_features import LinearSelectionFeature
from ._base_selector import BaseSelector


class LinearSelector(BaseSelector):
    @property
    def parent(self) -> Graphic:
        return self._parent

    @property
    def selection(self) -> float:
        """
        x or y value of selector's current position
        """
        return self._selection.value

    @selection.setter
    def selection(self, value: int):
        graphic = self._parent

        if isinstance(graphic, GraphicCollection):
            pass

        self._selection.set_value(self, value)

    @property
    def limits(self) -> tuple[float, float]:
        return self._limits

    @limits.setter
    def limits(self, values: tuple[float, float]):
        # check that `values` is an iterable of two real numbers
        # using `Real` here allows it to work with builtin `int` and `float` types, and numpy scaler types
        if len(values) != 2 or not all(map(lambda v: isinstance(v, Real), values)):
            raise TypeError("limits must be an iterable of two numeric values")
        self._limits = tuple(
            map(round, values)
        )  # if values are close to zero things get weird so round them
        self.selection._limits = self._limits

    @property
    def edge_color(self) -> pygfx.Color:
        """Returns the color of the linear selector."""
        return self._edge_color

    @edge_color.setter
    def edge_color(self, color: str | Sequence[float]):
        """
        Set the color of the linear selector.

        Parameters
        ----------
        color : str | Sequence[float]
            String or sequence of floats that gets converted into a ``pygfx.Color`` object.
        """
        color = pygfx.Color(color)
        # only want to change inner line color
        self._edges[0].material.color = color
        self._original_colors[self._edges[0]] = color
        self._edge_color = color

    # TODO: make `selection` arg in graphics data space not world space
    def __init__(
        self,
        selection: float,
        limits: Sequence[float],
        size: float,
        center: float,
        axis: str = "x",
        parent: Graphic = None,
        edge_color: str | Sequence[float] | np.ndarray = "w",
        thickness: float = 2.5,
        arrow_keys_modifier: str = "Shift",
        name: str = None,
    ):
        """
        Create a horizontal or vertical line that can be used to select a value along an axis.

        Parameters
        ----------
        selection: int
            initial x or y selected position for the selector, in data space

        limits: (int, int)
            (min, max) limits along the x or y-axis for the selector, in data space

        size: float
            size of the selector, usually the range of the data

        center: float
            center offset of the selector on the orthogonal axis, usually the data mean

        axis: str, default "x"
            "x" | "y", the axis along which the selector can move

        parent: Graphic
            parent graphic for this LinearSelector

        arrow_keys_modifier: str
            modifier key that must be pressed to initiate movement using arrow keys, must be one of:
            "Control", "Shift", "Alt" or ``None``. Double-click the selector first to enable the
            arrow key movements, or set the attribute ``arrow_key_events_enabled = True``

        thickness: float, default 2.5
            thickness of the selector

        edge_color: str | tuple | np.ndarray, default "w"
            color of the selector

        name: str, optional
            name of linear selector

        """
        self._fill_color = None
        self._edge_color = pygfx.Color(edge_color)
        self._vertex_color = None

        if len(limits) != 2:
            raise ValueError("limits must be a tuple of 2 integers, i.e. (int, int)")

        self._limits = np.asarray(limits)

        end_points = [-size / 2, size / 2]

        if axis == "x":
            xs = np.array([selection, selection])
            ys = np.array(end_points)
            zs = np.zeros(2)

            line_data = np.column_stack([xs, ys, zs])
        elif axis == "y":
            xs = np.array(end_points)
            ys = np.array([selection, selection])
            zs = np.zeros(2)

            line_data = np.column_stack([xs, ys, zs])
        else:
            raise ValueError("`axis` must be one of 'x' or 'y'")

        line_data = line_data.astype(np.float32)

        if thickness < 1.1:
            material = pygfx.LineThinMaterial
        else:
            material = pygfx.LineMaterial

        self.colors_outer = pygfx.Color([0.3, 0.3, 0.3, 1.0])

        line_inner = pygfx.Line(
            # self.data.feature_data because data is a Buffer
            geometry=pygfx.Geometry(positions=line_data),
            material=material(thickness=thickness, color=edge_color, pick_write=True),
        )

        self.line_outer = pygfx.Line(
            geometry=pygfx.Geometry(positions=line_data),
            material=material(
                thickness=thickness + 6, color=self.colors_outer, pick_write=True
            ),
        )

        line_inner.world.z = self.line_outer.world.z + 1

        world_object = pygfx.Group()

        world_object.add(self.line_outer)
        world_object.add(line_inner)

        self._move_info: dict = None

        if axis == "x":
            offset = (parent.offset[0], center + parent.offset[1], 0)
        elif axis == "y":
            offset = (center + parent.offset[0], parent.offset[1], 0)

        # init base selector
        BaseSelector.__init__(
            self,
            edges=(line_inner, self.line_outer),
            hover_responsive=(line_inner, self.line_outer),
            arrow_keys_modifier=arrow_keys_modifier,
            axis=axis,
            parent=parent,
            name=name,
            offset=offset,
        )

        self._set_world_object(world_object)

        self._selection = LinearSelectionFeature(
            axis=axis, value=selection, limits=self._limits
        )

        if self._parent is not None:
            self.selection = selection
        else:
            self._selection.set_value(self, selection)

    def get_selected_index(self, graphic: Graphic = None) -> int | list[int]:
        """
        Data index the selector is currently at w.r.t. the Graphic data.

        With LineGraphic data, the geometry x or y position is not always the data position, for example if plotting
        data using np.linspace. Use this to get the data index of the selector.

        Parameters
        ----------
        graphic: Graphic, optional
            Graphic to get the selected data index from. Default is the parent graphic associated to the selector.

        Returns
        -------
        int or List[int]
            data index the selector is currently at, list of ``int`` if a Collection
        """

        source = self._get_source(graphic)

        if isinstance(source, GraphicCollection):
            ixs = list()
            for g in source.graphics:
                ixs.append(self._get_selected_index(g))

            return ixs

        return self._get_selected_index(source)

    def _get_selected_index(self, graphic):
        # the array to search for the closest value along that axis
        if self.axis == "x":
            data = graphic.data[:, 0]
        elif self.axis == "y":
            data = graphic.data[:, 1]

        if (
            "Line" in graphic.__class__.__name__
            or "Scatter" in graphic.__class__.__name__
        ):
            # we want to find the index of the data closest to the selector position
            find_value = self.selection

            # get closest data index to the world space position of the selector
            idx = np.searchsorted(data, find_value, side="left")

            if idx > 0 and (
                idx == len(data)
                or math.fabs(find_value - data[idx - 1])
                < math.fabs(find_value - data[idx])
            ):
                return round(idx - 1)
            else:
                return round(idx)

        if "Image" in graphic.__class__.__name__:
            # indices map directly to grid geometry for image data buffer
            index = self.selection
            shape = graphic.data[:].shape

            if self.axis == "x":
                # assume selecting columns
                upper_bound = shape[1] - 1
            elif self.axis == "y":
                # assume selecting rows
                upper_bound = shape[0] - 1

            return min(round(index), upper_bound)

    def _move_graphic(self, delta: np.ndarray):
        """
        Moves the graphic

        Parameters
        ----------
        delta: np.ndarray
            delta in world space

        """

        if self.axis == "x":
            self.selection = self.selection + delta[0]
        else:
            self.selection = self.selection + delta[1]
