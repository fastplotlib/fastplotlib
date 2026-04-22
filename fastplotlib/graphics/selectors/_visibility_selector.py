from __future__ import annotations

from collections.abc import Iterable
from numbers import Integral
from typing import Callable
from warnings import warn

import cmap as cmap_lib
import numpy as np

from .._collection_base import GraphicCollection
from ..shaders._highlight_materials import HighlightableImageMaterial
from ._highlight_selector import _build_lut

_AXES = {"x": 0, "y": 1, "z": 2}


def _validate_int_collection(value, name: str) -> set | int:
    if isinstance(value, Integral):
        return int(value)

    s = set(value)

    if not all(isinstance(i, Integral) for i in s):
        raise TypeError(f"{name} must contain only integers, got: {s!r}")

    return value


class VisibilitySelector:
    """
    Shows a subset of graphics in a GraphicCollection by toggling their visibility.

    ``selection = list()`` or ``None``: all invisible.
    ``selection = [s1, s2, ..., s_n]``: only these indices visible

    For ``LineStack`` and ``ScatterStack``, visible graphics are re-stacked
    along the stack axis when the selection changes.

    If a ``lut`` is provided, each visible graphic is colored by its position in
    the selection

    Parameters
    ----------
    collection : GraphicCollection
    selection : list[int] or None
        Initial selection.

    lut : str or array-like of shape (n, 4), optional
        color or stack of RGBA arrays

    lut_wrap : "fixed" or "repeat"
        How to handle selection indices beyond the end of the lut.
    """

    def __init__(
        self,
        collection: GraphicCollection,
        selection: list[int] | None = None,
        lut: str | np.ndarray | None = None,
        lut_wrap: str = "fixed",
    ):
        if not isinstance(collection, GraphicCollection):
            raise TypeError(
                f"VisibilitySelector requires a GraphicCollection, "
                f"got {type(collection).__name__}."
            )
        if lut_wrap not in ("fixed", "repeat"):
            raise ValueError(f"lut_wrap must be 'fixed' or 'repeat', got {lut_wrap!r}")

        self._collection = collection
        self._selection: list[int] = []
        self._event_handlers: list[Callable] = []
        self._lut_wrap = lut_wrap

        self._lut = lut

        # save original colors so they can be restored when this selector is deleted
        self._original_colors: dict[int, np.ndarray] = {}
        for i, g in enumerate(collection.graphics):
            c = g.colors
            if hasattr(c, "value"):
                self._original_colors[i] = np.asarray(c.value, dtype=np.float32).copy()
            else:
                self._original_colors[i] = np.asarray(c, dtype=np.float32).copy()

        self._is_stack = hasattr(collection, "separation")
        if self._is_stack:
            self._sep_axis = collection.separation_axis
            ax_i = _AXES[self._sep_axis]
            self._data_ranges = np.array(
                [float(g.data.value[:, ax_i].max()) for g in collection.graphics]
            )

        for g in collection.graphics:
            g.visible = False

        if selection is not None and len(selection) > 0:
            self.selection = selection

    def __del__(self):
        for g in self._collection.graphics:
            g.visible = True

        if self._lut is None:
            return

        for i, g in enumerate(self._collection.graphics):
            g.colors = self._original_colors[i]

    @property
    def selection(self) -> tuple[int, ...]:
        """Get or set the selection"""
        return tuple(self._selection)

    @selection.setter
    def selection(self, new_selection: Iterable[int] | int):
        if new_selection:
            _validate_int_collection(new_selection, "selection")

        for index in self._selection:
            # set any selected things to be invisible
            self._collection.graphics[index].visible = False

        if isinstance(new_selection, Integral):
            new_selection = [new_selection]

        self._selection = list(new_selection) if new_selection else list()

        for index in self._selection:
            # set the new selection to be visible
            self._collection.graphics[index].visible = True

        if self._is_stack:
            self._restack()

        self._apply_lut()
        self._emit({"value": tuple(self._selection)})

    def append(self, item: int):
        """Add an index to the selection. Already-selected indices are skipped."""
        if not isinstance(item, Integral):
            raise TypeError(f"item must be an integer, got {type(item)}")

        if item in self._selection:
            return

        self._collection.graphics[item].visible = True
        self._selection.append(item)

        if self._is_stack:
            self._restack()

        self._apply_lut()
        self._emit({"value": tuple(self._selection)})

    def remove(self, item: int):
        """Remove an index from the selection."""
        if not isinstance(item, Integral):
            raise TypeError(f"item must be an integer, got {type(item).__name__}")

        if item not in self._selection:
            return

        self._collection.graphics[item].visible = False
        self._selection.remove(item)

        if self._is_stack:
            self._restack()

        self._apply_lut()
        self._emit({"value": list(self._selection)})

    def clear(self) -> None:
        """Hide all graphics. Stack offsets are left as-is."""
        for idx in self._selection:
            self._collection.graphics[idx].visible = False

        self._selection = list()
        self._emit({"value": []})
    @property
    def lut(self) -> np.ndarray | None:
        """Optional per-item colors, shape ``(n, 4)`` float32 RGBA"""
        return self._lut

    @lut.setter
    def lut(self, value: str | np.ndarray | None) -> None:
        self._lut = value
        self._apply_lut()

    @property
    def lut_wrap(self) -> str:
        """LUT wrap mode: ``'fixed'`` or ``'repeat'``."""
        return self._lut_wrap

    def _apply_lut(self) -> None:
        if self._lut is None or not self._selection:
            return

        colors = _build_lut(
            color=None, lut=self._lut, n=len(self._selection), lut_wrap=self._lut_wrap
        )
        for sel_index, graphic_index in enumerate(self._selection):
            self._collection.graphics[graphic_index].colors = colors[sel_index]

    def _restack(self) -> None:
        sep = self._collection.separation
        ax_i = _AXES[self._sep_axis]

        distance = 0.0
        for index in self._selection:
            g = self._collection.graphics[index]
            offset = list(g.offset)
            offset[ax_i] = distance
            g.offset = tuple(offset)
            distance += self._data_ranges[index] + sep

    def add_event_handler(self, handler: Callable) -> None:
        """Register a callback fired when the selection changes."""
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

    def __len__(self) -> int:
        return len(self._selection)

    def __contains__(self, item) -> bool:
        return item in self._selection

    def __iter__(self):
        return iter(self._selection)

    def __repr__(self) -> str:
        return (
            f"VisibilitySelector\n"
            f"selection: {self._selection}"
        )


class ImageVisibilitySelector:
    """
    Shows a subset of rows or columns of an ``ImageGraphic`` via GPU shader remapping.

    Selected rows/columns are rendered as a compact stack with no gaps. Non-selected
    rows/columns are discarded in the fragment shader.

    Requires ``HighlightableImageMaterial`` and ``interpolation='nearest'``.

    Can be combined with ``ImageHighlightSelector`` on the same graphic; highlight
    indices always refer to original source coordinates regardless of visibility state.

    Parameters
    ----------
    graphic : ImageGraphic
    axis : "rows" or "cols"
        Axis to subset.
    selection : list[int] or None
        Initial selection.
    """

    def __init__(self, graphic, axis: str = "rows", selection: list[int] | None = None):
        if axis not in ("rows", "cols"):
            raise ValueError(f"axis must be 'rows' or 'cols', got {axis!r}")

        mat = getattr(graphic, "_material", None)
        if not isinstance(mat, HighlightableImageMaterial):
            raise TypeError(
                "ImageVisibilitySelector requires HighlightableImageMaterial, "
                f"got {type(mat).__name__}."
            )

        if graphic.interpolation != "nearest":
            raise ValueError(
                "ImageVisibilitySelector requires interpolation='nearest'; "
                f"got {graphic.interpolation!r}. Set graphic.interpolation = 'nearest' first."
            )

        tiles = list(graphic.world_object.children)
        if len(tiles) != 1:
            raise ValueError(
                f"ImageVisibilitySelector only supports single-tile images, "
                f"got {len(tiles)} tiles."
            )

        self._graphic = graphic
        self._tile = tiles[0]
        self._axis = axis
        self._selection: list[int] = list()
        self._event_handlers: list[Callable] = list()

        mat.uniform_buffer.data["fpl_vis_axis_y"] = np.uint32(
            1 if axis == "rows" else 0
        )
        mat.uniform_buffer.data["fpl_n_visible"] = np.uint32(0)
        mat.uniform_buffer.update_range()

        if selection is not None and len(selection) > 0:
            self.selection = selection

    @property
    def axis(self) -> str:
        """
        'rows' or 'cols'
        """
        return self._axis

    @property
    def selection(self) -> tuple[int, ...]:
        """Get or set row/col selection indices"""
        return tuple(self._selection)

    @selection.setter
    def selection(self, value: Iterable[int]):
        if value:
            _validate_int_collection(value, "selection")

        if isinstance(value, Integral):
            value = [value]

        self._selection = list(value) if value else list()

        self._update_material()
        self._emit({"value": tuple(self._selection)})

    def append(self, item) -> None:
        """add a row/col index to the selection"""
        if not isinstance(item, Integral):
            raise TypeError(f"item must be an integer, got {type(item)}")

        if item in self._selection:
            return

        self._selection.append(item)

        self._update_material()
        self._emit({"value": list(self._selection)})

    def remove(self, item) -> None:
        """Remove a row/col index from the selection."""
        if not isinstance(item, Integral):
            raise TypeError(f"item must be an integer, got {type(item)}")

        if item not in self._selection:
            return

        self._selection.remove(item)
        self._update_material()
        self._emit({"value": list(self._selection)})

    def clear(self) -> None:
        """Clear the selection (all invisible, fpl_n_visible=0)."""
        self._selection = list()
        self._update_material()
        self._emit({"value": list()})

    def _update_material(self) -> None:
        mat = self._graphic._material
        n = len(self._selection)
        if n > 0:
            mat._vis_lut_buffer.data[:n] = np.array(self._selection, dtype=np.uint32)

        mat._vis_lut_buffer.update_range()
        mat.uniform_buffer.data["fpl_n_visible"] = np.uint32(n)
        mat.uniform_buffer.update_range()

        self._update_bbox()

    def _update_bbox(self) -> None:
        data = self._graphic.data.value
        n_total = data.shape[0] if self._axis == "rows" else data.shape[1]

        n_visible = len(self._selection)
        ax_i = 1 if self._axis == "rows" else 0
        self._graphic.world_object.children[0]._vis_scale = (
            ax_i,
            n_visible / n_total if n_total > 0 else 0.0,
        )

    def add_event_handler(self, handler: Callable) -> None:
        """register an event handler that is called when the selection changes"""
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

    def __len__(self) -> int:
        return len(self._selection)

    def __contains__(self, item) -> bool:
        return item in self._selection

    def __iter__(self):
        return iter(self._selection)

    def __repr__(self) -> str:
        data = self._graphic.data.value
        return (
            f"ImageVisibilitySelector\n"
            f"axis: {self._axis}\n"
            f"selection: {self._selection}\n"
        )
