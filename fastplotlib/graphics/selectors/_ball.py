from typing import Sequence
import math

import numpy as np
import pygfx

from .._base import Graphic
from ..features._selection_features import PointSelectionFeature
from ._base_selector import BaseSelector, MoveInfo
from ..features import UniformSize


class BallSelector(BaseSelector):
    _features = {"selection": PointSelectionFeature}

    @property
    def parent(self) -> Graphic:
        return self._parent

    @property
    def selection(self) -> np.ndarray:
        """Value of selector's current position (x, y, z)"""
        return self._selection.value

    @selection.setter
    def selection(self, value: np.ndarray):
        """
        Set the (x, y, z) position of the selector. If bound to a parent graphic, will set
        selection to the nearest point of the parent.

        Parameters
        ----------
        value : np.ndarray
            New (x, y, z) position of the selector
        """
        if value.shape != (1, 3):
            raise ValueError("Selection must be a single (x, y, z) point")
        # if selector is bound to a parent graphic, find the nearest data point
        if self.parent is not None:
            closest_ix = self._get_nearest_index(self.parent, value)
            value = self.parent.data[closest_ix].reshape(1, 3)
        self._selection.set_value(self, value)

    @property
    def color(self) -> pygfx.Color:
        """Returns the color of the ball selector."""
        return self._color

    @color.setter
    def color(self, color: str | Sequence[float]):
        """
        Set the color of the ball selector.

        Parameters
        ----------
        color : str | Sequence[float]
            String or sequence of floats that gets converted into a ``pygfx.Color`` object.
        """
        color = pygfx.Color(color)
        self.world_object.material.color = color
        self._original_colors[self._vertices[0]] = color
        self._color = color

    @property
    def size(self) -> float:
        """Returns the size of the ball selector."""
        if isinstance(self._size, UniformSize):
            return self._size.value

    @size.setter
    def size(self, value: float):
        """
        Set the size of the ball selector.

        Parameters
        ----------
        value : float
            Size of the ball selector
        """
        if isinstance(self._size, UniformSize):
            self._size.set_value(self, value)

    def __init__(
        self,
        selection: np.ndarray,
        parent: Graphic = None,
        color: str | Sequence[float] | np.ndarray = "w",
        size: float = 10,
        arrow_keys_modifier: str = "Shift",
        name: str = None,
    ):
        """
        Create a ball marker that can be used to select a value along a line

        Parameters
        ----------
        selection: np.ndarray
            (x, y, z) position of the selector, in data space
        parent: Graphic
            parent graphic for the BallSelector
        color: str | tuple | np.ndarray, default "w"
            color of the selector
        size: float
            size of the selector
        arrow_keys_modifier: str
            modifier key that must be pressed to initiate movement using arrow keys, must be one of:
            "Control", "Shift", "Alt" or ``None``. Double-click the selector first to enable the
            arrow key movements, or set the attribute ``arrow_key_events_enabled = True``
        name: str, optional
            name of linear selector

        """
        self._color = pygfx.Color(color)

        geo_kwargs = {"positions": selection}

        material_kwargs = {"pick_write": True}
        material_kwargs["color_mode"] = "uniform"
        material_kwargs["color"] = self._color

        material_kwargs["size_mode"] = "uniform"
        self._size = UniformSize(size)
        material_kwargs["size"] = self.size

        world_object = pygfx.Points(
            pygfx.Geometry(**geo_kwargs),
            material=pygfx.PointsMaterial(**material_kwargs),
        )

        # init base selector
        BaseSelector.__init__(
            self,
            vertices=(world_object,),
            hover_responsive=(world_object,),
            arrow_keys_modifier=arrow_keys_modifier,
            parent=parent,
            name=name,
        )

        self._set_world_object(world_object)

        self._selection = PointSelectionFeature(value=selection)

        if self._parent is not None:
            self.selection = selection
        else:
            self._selection.set_value(self, selection)

    def _get_nearest_index(self, graphic, find_value):
        data = graphic.data.value[:]

        # get closest data index to the world space position of the selector
        distances = np.sum((data - find_value) ** 2, axis=1)

        # Index of closest point
        idx = np.argmin(distances)

        return idx

    def _move_graphic(self, move_info: MoveInfo):
        """
        Moves the graphic

        Parameters
        ----------
        delta: np.ndarray
            delta in world space

        """
        # If this the first move in this drag, store initial selection
        if move_info.start_selection is None:
            move_info.start_selection = self.selection

        delta = move_info.delta

        self.selection = move_info.start_selection + delta
