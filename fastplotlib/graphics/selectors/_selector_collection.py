from __future__ import annotations

from numbers import Integral
from typing import Callable
from warnings import warn

import pygfx

from .._base import Graphic
from ._base_selector import BaseSelector
from ._linear import LinearSelector
from ._linear_region import LinearRegionSelector
from ._polygon import PolygonSelector
from ._rectangle import RectangleSelector


_SELECTOR_TYPES = (LinearSelector, LinearRegionSelector, RectangleSelector, PolygonSelector)


class SelectorCollection(Graphic):
    """
    Dynamically-sized collection of same-type selectors on a shared parent graphic.

    Do not instantiate directly; use a concrete subclass such as
    ``RectangleSelectors``.

    ``selection`` is a list of each child selector's ``selection`` value in
    append order.  Assigning to it resizes the collection as needed. shorter
    lists remove tail selectors, longer lists create new ones.

    Parameters
    ----------
    parent : Graphic
        Parent graphic forwarded to every child selector.
    selection : list, optional
        Initial selection values.
    name : str, optional
    **selector_kwargs
        Forwarded verbatim to each child selector on creation.
    """

    _selector_type: type = None

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        t = getattr(cls, "_selector_type", None)
        if t is not None and t not in _SELECTOR_TYPES:
            raise TypeError(
                f"{cls.__name__}._selector_type must be one of "
                f"{[c.__name__ for c in _SELECTOR_TYPES]}, got {t!r}"
            )

    def __init__(
        self,
        parent: Graphic,
        selection: list | None = None,
        name: str = None,
        **selector_kwargs,
    ):
        if type(self)._selector_type is None:
            raise TypeError(
                f"{type(self).__name__} cannot be instantiated directly; "
                "use a concrete subclass."
            )
        super().__init__(name=name)
        self._set_world_object(pygfx.Group())
        self._parent_graphic = parent
        self._selector_kwargs = selector_kwargs
        self._selectors: list[BaseSelector] = []
        self._event_handlers: list[Callable] = []

        if selection is not None:
            self.selection = selection

    # ------------------------------------------------------------------ hooks

    def _fpl_add_plot_area_hook(self, plot_area):
        super()._fpl_add_plot_area_hook(plot_area)
        for sel in self._selectors:
            sel._fpl_add_plot_area_hook(plot_area)

    def _fpl_prepare_del(self):
        for sel in list(self._selectors):
            sel._fpl_prepare_del()
            self.world_object.remove(sel.world_object)
        self._selectors.clear()
        super()._fpl_prepare_del()

    # ------------------------------------------------------------------ selection

    @property
    def selection(self) -> list:
        """Child selector selections in append order."""
        return [s.selection for s in self._selectors]

    @selection.setter
    def selection(self, values: list) -> None:
        n_old = len(self._selectors)
        for sel, val in zip(self._selectors, values):
            sel.selection = val
        while len(self._selectors) > len(values):
            self._remove_selector(-1)
        for val in values[n_old:]:
            self._append_selector(val)
        self._emit({"value": self.selection})

    # ------------------------------------------------------------------ public

    def append(self, selection) -> BaseSelector:
        """Create a new child selector and return it."""
        sel = self._append_selector(selection)
        self._emit({"value": self.selection})
        return sel

    def remove(self, item: int | BaseSelector) -> None:
        """Remove a child selector by index or reference."""
        self._remove_selector(item)
        self._emit({"value": self.selection})

    def clear(self) -> None:
        """Remove all child selectors."""
        while self._selectors:
            self._remove_selector(-1)
        self._emit({"value": []})

    # ------------------------------------------------------------------ internal

    def _append_selector(self, selection) -> BaseSelector:
        sel = self._selector_type(
            selection=selection,
            parent=self._parent_graphic,
            **self._selector_kwargs,
        )
        self.world_object.add(sel.world_object)
        self._selectors.append(sel)
        if self._plot_area is not None:
            sel._fpl_add_plot_area_hook(self._plot_area)
        return sel

    def _remove_selector(self, item: int | BaseSelector) -> None:
        sel = self._selectors[item] if isinstance(item, Integral) else item
        sel._fpl_prepare_del()
        self.world_object.remove(sel.world_object)
        self._selectors.remove(sel)

    # ------------------------------------------------------------------ events

    def add_event_handler(self, handler: Callable) -> None:
        """Register a callback fired on any selection change."""
        if not callable(handler):
            raise TypeError("event handler must be callable")
        if handler in self._event_handlers:
            warn(f"{handler} is already registered.")
            return
        self._event_handlers.append(handler)

    def remove_event_handler(self, handler: Callable) -> None:
        if handler not in self._event_handlers:
            raise KeyError(f"{handler} is not registered.")
        self._event_handlers.remove(handler)

    def _emit(self, info: dict) -> None:
        for h in self._event_handlers:
            h({"selector": self, **info})

    # ------------------------------------------------------------------ dunder

    def __getitem__(self, index: int) -> BaseSelector:
        return self._selectors[index]

    def __len__(self) -> int:
        return len(self._selectors)

    def __contains__(self, item) -> bool:
        return item in self._selectors

    def __iter__(self):
        return iter(self._selectors)

    def __repr__(self) -> str:
        n = len(self._selectors)
        s = f"{self.__class__.__name__}(n={n})"
        if self.name:
            s = f"'{self.name}': {s}"
        return s


class LinearSelectors(SelectorCollection):
    """
    Collection of :class:`.LinearSelector` instances on a shared parent graphic.

    Parameters
    ----------
    parent : Graphic
    limits : tuple[float, float]
        ``(min, max)`` bounds on the selector axis.
    selection : list[float], optional
        Initial selector positions.
    axis : "x" or "y"
    edge_color : color
    thickness : float
    arrow_keys_modifier : str
    extra_width : float
    name : str, optional
    """

    _selector_type = LinearSelector

    def __init__(
        self,
        parent: Graphic,
        limits: tuple[float, float],
        selection: list[float] | None = None,
        *,
        axis: str = "x",
        edge_color="yellow",
        thickness: float = 1.0,
        arrow_keys_modifier: str = "Shift",
        extra_width: float = 14.0,
        name: str = None,
    ):
        super().__init__(
            parent, selection, name=name,
            limits=limits,
            axis=axis,
            edge_color=edge_color,
            thickness=thickness,
            arrow_keys_modifier=arrow_keys_modifier,
            extra_width=extra_width,
        )


class LinearRegionSelectors(SelectorCollection):
    """
    Collection of :class:`.LinearRegionSelector` instances on a shared parent graphic.

    Parameters
    ----------
    parent : Graphic
    limits : tuple[float, float]
        ``(min, max)`` range the selector can occupy.
    size : float
        Extent of each region box along the axis orthogonal to ``axis``.
    center : float
        Centre of each box along the orthogonal axis.
    selection : list[tuple[float, float]], optional
        Initial ``(min, max)`` pairs.
    axis : "x" or "y"
    resizable : bool
    fill_color : color
    edge_color : color
    edge_thickness : float
    arrow_keys_modifier : str
    extra_width : float
    name : str, optional
    """

    _selector_type = LinearRegionSelector

    def __init__(
        self,
        parent: Graphic,
        limits: tuple[float, float],
        size: float,
        center: float,
        selection: list | None = None,
        *,
        axis: str = "x",
        resizable: bool = True,
        fill_color=(0, 0, 0.35),
        edge_color="yellow",
        edge_thickness: float = 1.0,
        arrow_keys_modifier: str = "Shift",
        extra_width: float = 14.0,
        name: str = None,
    ):
        super().__init__(
            parent, selection, name=name,
            limits=limits,
            size=size,
            center=center,
            axis=axis,
            resizable=resizable,
            fill_color=fill_color,
            edge_color=edge_color,
            edge_thickness=edge_thickness,
            arrow_keys_modifier=arrow_keys_modifier,
            extra_width=extra_width,
        )


class RectangleSelectors(SelectorCollection):
    """
    Collection of :class:`.RectangleSelector` instances on a shared parent graphic.

    Parameters
    ----------
    parent : Graphic
    limits : tuple[float, float, float, float]
        ``(xmin, xmax, ymin, ymax)`` bounds.
    selection : list[tuple[float, float, float, float]], optional
        Initial ``(xmin, xmax, ymin, ymax)`` rectangles.
    resizable : bool
    fill_color : color
    edge_color : color
    edge_thickness : float
    vertex_color : color
    vertex_size : float
    arrow_keys_modifier : str
    name : str, optional
    """

    _selector_type = RectangleSelector

    def __init__(
        self,
        parent: Graphic,
        limits: tuple[float, float, float, float],
        selection: list | None = None,
        *,
        resizable: bool = True,
        fill_color=(0, 0, 0.35),
        edge_color=(0.8, 0.6, 0),
        edge_thickness: float = 8,
        vertex_color=(0.7, 0.4, 0),
        vertex_size: float = 8,
        arrow_keys_modifier: str = "Shift",
        name: str = None,
    ):
        super().__init__(
            parent, selection, name=name,
            limits=limits,
            resizable=resizable,
            fill_color=fill_color,
            edge_color=edge_color,
            edge_thickness=edge_thickness,
            vertex_color=vertex_color,
            vertex_size=vertex_size,
            arrow_keys_modifier=arrow_keys_modifier,
        )


class PolygonSelectors(SelectorCollection):
    """
    Collection of :class:`.PolygonSelector` instances on a shared parent graphic.

    Parameters
    ----------
    parent : Graphic
    limits : tuple[float, float, float, float]
        ``(xmin, xmax, ymin, ymax)`` bounds.
    selection : list, optional
        Initial polygon vertex lists; each element is a sequence of
        ``(x, y)`` or ``(x, y, 0)`` points, or ``None`` for an empty polygon.
    resizable : bool
    fill_color : color
    edge_color : color
    edge_thickness : float
    vertex_color : color
    vertex_size : float
    name : str, optional
    """

    _selector_type = PolygonSelector

    def __init__(
        self,
        parent: Graphic,
        limits: tuple[float, float, float, float],
        selection: list | None = None,
        *,
        resizable: bool = True,
        fill_color=(0, 0, 0.35),
        edge_color=(0.8, 0.6, 0),
        edge_thickness: float = 4,
        vertex_color=(0.7, 0.4, 0),
        vertex_size: float = 12,
        name: str = None,
    ):
        super().__init__(
            parent, selection, name=name,
            limits=limits,
            resizable=resizable,
            fill_color=fill_color,
            edge_color=edge_color,
            edge_thickness=edge_thickness,
            vertex_color=vertex_color,
            vertex_size=vertex_size,
        )
