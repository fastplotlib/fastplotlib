from typing import Sequence

import numpy as np
import pygfx

from .._base import Graphic
from .._collection_base import GraphicCollection
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
        selection : np.ndarray
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

    def get_selected_index(self, graphic: Graphic = None) -> int | list[int]:
        return 0

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
