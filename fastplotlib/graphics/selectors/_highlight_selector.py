from __future__ import annotations

from typing import Callable
from warnings import warn

import numpy as np
import pygfx
from pygfx.resources import Buffer, Texture

from .._collection_base import GraphicCollection
from ..shaders._highlight_materials import (
    HighlightableLineMaterial,
    HighlightableLineThinMaterial,
    HighlightablePointsMaterial,
    HighlightablePointsMarkerMaterial,
    HighlightablePointsSpriteMaterial,
    HighlightablePointsGaussianBlobMaterial,
    HighlightableImageMaterial,
)

_POSITIONS_MATERIAL_TYPES = (
    HighlightableLineMaterial,
    HighlightableLineThinMaterial,
    HighlightablePointsMaterial,
    HighlightablePointsMarkerMaterial,
    HighlightablePointsSpriteMaterial,
    HighlightablePointsGaussianBlobMaterial,
)


def _build_lut(
    color: str | np.ndarray | None,
    lut_source: np.ndarray | None,
    n: int,
) -> np.ndarray:
    """
    Return an (n, 4) float32 RGBA array for n selected items.

    If lut_source is provided, lut_source[i] is the color for the i-th selected
    item. If lut_source is None, all rows are the resolved RGBA of color.
    """
    if n == 0:
        return np.zeros((1, 4), dtype=np.float32)
    if lut_source is not None:
        lut = np.asarray(lut_source, dtype=np.float32)
        if lut.ndim != 2 or lut.shape[1] != 4:
            raise ValueError("`lut` must have shape (k, 4)")
        if lut.shape[0] < n:
            raise ValueError(f"`lut` has {lut.shape[0]} entries but {n} are selected")
        return lut[:n].copy()
    rgba = np.array(pygfx.Color(color if color is not None else "cyan"), dtype=np.float32)
    return np.tile(rgba, (n, 1))


class HighlightSelector:
    """
    Base class managing highlight state on one or more graphics.

    Highlights selected vertices or image regions by blending a color into the
    rendered output. Does not create extra world objects, so ``pick_info``
    is unaffected.

    Use the concrete subclasses directly:

    * :class:`PositionsHighlightSelector` — highlight individual vertices on a
      LineGraphic or ScatterGraphic
    * :class:`CollectionHighlightSelector` — highlight whole lines/scatters in
      a collection
    * :class:`ImageHighlightSelector` — highlight pixel regions of an ImageGraphic
    """

    def __init__(
        self,
        color: str | np.ndarray = "cyan",
        lut: np.ndarray | None = None,
        alpha: float = 1.0,
    ):
        self._color = color
        self._lut_source = lut
        self._alpha = float(alpha)
        self._graphics: list = []
        self._event_handlers: list[Callable] = []

    # ------------------------------------------------------------------ selection API

    @property
    def selection(self):
        raise NotImplementedError

    @selection.setter
    def selection(self, value):
        raise NotImplementedError

    def append(self, item) -> None:
        raise NotImplementedError

    def remove(self, item) -> None:
        raise NotImplementedError

    def clear(self) -> None:
        raise NotImplementedError

    # ------------------------------------------------------------------ properties

    @property
    def color(self) -> str | np.ndarray:
        """
        Color applied to all selected items when no ``lut`` is set.

        Accepts any value that ``pygfx.Color`` understands (color name string,
        RGBA tuple, hex string, etc.).
        """
        return self._color

    @color.setter
    def color(self, value):
        self._color = value
        self._update_all_graphics()

    @property
    def lut(self) -> np.ndarray | None:
        """
        Optional per-item color table, shape ``(k, 4)`` float32 RGBA.

        When set, ``lut[i]`` is the highlight color for the i-th selected item.
        Must have at least as many rows as the number of selected items.
        Set to ``None`` to fall back to ``color``.
        """
        return self._lut_source

    @lut.setter
    def lut(self, value: np.ndarray | None):
        self._lut_source = value
        self._update_all_graphics()

    @property
    def alpha(self) -> float:
        """Highlight blend strength in [0, 1]. 0 = invisible, 1 = full color."""
        return self._alpha

    @alpha.setter
    def alpha(self, value: float):
        self._alpha = float(value)
        self._update_all_graphics()

    @property
    def graphics(self) -> list:
        """Attached graphics."""
        return list(self._graphics)

    # ------------------------------------------------------------------ graphic management

    def add_graphic(self, graphic) -> None:
        """Attach ``graphic`` and immediately apply the current selection to it."""
        if graphic in self._graphics:
            warn(f"{graphic!r} is already attached to this selector.")
            return
        self._validate_graphic(graphic)
        self._graphics.append(graphic)
        self._update_highlight_buffers(graphic)

    def remove_graphic(self, graphic) -> None:
        """Detach ``graphic`` and clear its highlights."""
        if graphic not in self._graphics:
            raise KeyError(f"{graphic!r} is not attached to this selector.")
        self._graphics.remove(graphic)
        self._clear_highlight_buffers(graphic)

    def _validate_graphic(self, graphic) -> None:
        raise NotImplementedError

    def _update_highlight_buffers(self, graphic) -> None:
        raise NotImplementedError

    def _clear_highlight_buffers(self, graphic) -> None:
        raise NotImplementedError

    # ------------------------------------------------------------------ events

    def add_event_handler(self, handler: Callable) -> None:
        """Register a callback fired when the selection changes."""
        if not callable(handler):
            raise TypeError("event handler must be callable")
        if handler in self._event_handlers:
            warn(f"{handler} is already registered.")
            return
        self._event_handlers.append(handler)

    def remove_event_handler(self, handler: Callable) -> None:
        """Remove a registered event handler."""
        if handler not in self._event_handlers:
            raise KeyError(f"{handler} is not registered.")
        self._event_handlers.remove(handler)

    def _emit(self, info: dict) -> None:
        for h in self._event_handlers:
            h({"selector": self, **info})

    # ------------------------------------------------------------------ helpers

    def _update_all_graphics(self) -> None:
        for g in self._graphics:
            self._update_highlight_buffers(g)

    @staticmethod
    def _write_ids(material, ids: np.ndarray) -> None:
        if material._highlight_ids_buffer.data.shape[0] != ids.shape[0]:
            material._highlight_ids_buffer = Buffer(ids.copy())
        else:
            material._highlight_ids_buffer.data[:] = ids
            material._highlight_ids_buffer.update_range()

    @staticmethod
    def _write_lut(material, lut: np.ndarray) -> None:
        if material._highlight_lut_buffer.data.shape[0] != lut.shape[0]:
            material._highlight_lut_buffer = Buffer(lut.copy())
        else:
            material._highlight_lut_buffer.data[:] = lut
            material._highlight_lut_buffer.update_range()

    # ------------------------------------------------------------------ dunder

    def __len__(self) -> int:
        raise NotImplementedError

    def __contains__(self, item) -> bool:
        raise NotImplementedError

    def __iter__(self):
        raise NotImplementedError

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"n_selected={len(self)}, "
            f"n_graphics={len(self._graphics)})"
        )


class PositionsHighlightSelector(HighlightSelector):
    """
    Highlights individual data points on a LineGraphic or ScatterGraphic.

    Parameters
    ----------
    color : str or array-like, default "cyan"
        Color applied to all selected vertices when no ``lut`` is set.
    lut : np.ndarray of shape (k, 4), optional
        Per-vertex RGBA colors; ``lut[i]`` applies to the i-th selected vertex.
        Must have at least as many rows as the number of selected vertices.
    alpha : float, default 1.0
        Highlight blend strength in [0, 1].
    """

    def __init__(
        self,
        color: str | np.ndarray = "cyan",
        lut: np.ndarray | None = None,
        alpha: float = 1.0,
    ):
        super().__init__(color=color, lut=lut, alpha=alpha)
        self._selection: list[int] = []

    @property
    def selection(self) -> list[int]:
        """
        Selected vertex indices.

        Assign a list or array of integer indices to set the selection.
        Empty selection is represented as ``[]``.
        """
        return list(self._selection)

    @selection.setter
    def selection(self, value) -> None:
        if value is None or len(value) == 0:
            self._selection = []
        else:
            self._selection = [int(i) for i in np.asarray(value).ravel()]
        self._update_all_graphics()
        self._emit({"value": list(self._selection)})

    def append(self, item) -> None:
        """
        Append one or more vertex indices to the selection.

        Indices already in the selection are silently skipped.
        """
        new = [int(i) for i in np.asarray(item).ravel()]
        novel = [i for i in new if i not in self._selection]
        if novel:
            self._selection.extend(novel)
            self._update_all_graphics()
            self._emit({"value": list(self._selection)})

    def remove(self, item) -> None:
        """Remove one or more vertex indices from the selection."""
        to_remove = set(int(i) for i in np.asarray(item).ravel())
        self._selection = [i for i in self._selection if i not in to_remove]
        self._update_all_graphics()
        self._emit({"value": list(self._selection)})

    def clear(self) -> None:
        """Remove all highlights."""
        self._selection = []
        self._update_all_graphics()
        self._emit({"value": []})

    def _validate_graphic(self, graphic) -> None:
        mat = graphic.world_object.material
        if not isinstance(mat, _POSITIONS_MATERIAL_TYPES):
            raise TypeError(
                f"PositionsHighlightSelector requires a graphic using one of "
                f"{[t.__name__ for t in _POSITIONS_MATERIAL_TYPES]}, "
                f"got {type(mat).__name__}."
            )

    def _update_highlight_buffers(self, graphic) -> None:
        mat = graphic.world_object.material
        mat.uniform_buffer.data["highlight_alpha"] = self._alpha
        mat.uniform_buffer.update_range()

        n_vertices = graphic.data.value.shape[0]
        ids = np.zeros(n_vertices, dtype=np.uint32)
        for rank, idx in enumerate(self._selection):
            if 0 <= idx < n_vertices:
                ids[idx] = rank + 1

        self._write_ids(mat, ids)
        self._write_lut(mat, _build_lut(self._color, self._lut_source, len(self._selection)))

    def _clear_highlight_buffers(self, graphic) -> None:
        mat = graphic.world_object.material
        n_vertices = graphic.data.value.shape[0]
        self._write_ids(mat, np.zeros(n_vertices, dtype=np.uint32))
        self._write_lut(mat, np.zeros((1, 4), dtype=np.float32))

    def __len__(self) -> int:
        return len(self._selection)

    def __contains__(self, item) -> bool:
        return int(item) in self._selection

    def __iter__(self):
        return iter(self._selection)

    def __repr__(self) -> str:
        return (
            f"PositionsHighlightSelector("
            f"selection={self._selection}, "
            f"n_graphics={len(self._graphics)})"
        )


class CollectionHighlightSelector(HighlightSelector):
    """
    Highlights entire graphics within a LineCollection or ScatterCollection.

    Each selected collection item is highlighted with a single color across
    all of its vertices.

    Parameters
    ----------
    color : str or array-like, default "cyan"
        Color applied to all selected items when no ``lut`` is set.
    lut : np.ndarray of shape (k, 4), optional
        Per-item RGBA colors; ``lut[i]`` applies to the i-th selected item.
        Must have at least as many rows as the number of selected items.
    alpha : float, default 1.0
        Highlight blend strength in [0, 1].
    """

    def __init__(
        self,
        color: str | np.ndarray = "cyan",
        lut: np.ndarray | None = None,
        alpha: float = 1.0,
    ):
        super().__init__(color=color, lut=lut, alpha=alpha)
        self._selection: list[int] = []

    @property
    def selection(self) -> list[int]:
        """
        Selected collection indices.

        Assign a list or array of integer indices to set the selection.
        Empty selection is represented as ``[]``.
        """
        return list(self._selection)

    @selection.setter
    def selection(self, value) -> None:
        if value is None or len(value) == 0:
            self._selection = []
        else:
            self._selection = [int(i) for i in np.asarray(value).ravel()]
        self._update_all_graphics()
        self._emit({"value": list(self._selection)})

    def append(self, item) -> None:
        """
        Append one or more collection indices to the selection.

        Indices already in the selection are silently skipped.
        """
        new = [int(i) for i in np.asarray(item).ravel()]
        novel = [i for i in new if i not in self._selection]
        if novel:
            self._selection.extend(novel)
            self._update_all_graphics()
            self._emit({"value": list(self._selection)})

    def remove(self, item) -> None:
        """Remove one or more collection indices from the selection."""
        to_remove = set(int(i) for i in np.asarray(item).ravel())
        self._selection = [i for i in self._selection if i not in to_remove]
        self._update_all_graphics()
        self._emit({"value": list(self._selection)})

    def clear(self) -> None:
        """Remove all highlights."""
        self._selection = []
        self._update_all_graphics()
        self._emit({"value": []})

    def _validate_graphic(self, graphic) -> None:
        if not isinstance(graphic, GraphicCollection):
            raise TypeError(
                f"CollectionHighlightSelector requires a GraphicCollection, "
                f"got {type(graphic).__name__}."
            )

    def _update_highlight_buffers(self, graphic) -> None:
        n_items = len(graphic)
        sel = self._selection
        lut = _build_lut(self._color, self._lut_source, len(sel))
        rank_map = {
            idx: rank + 1
            for rank, idx in enumerate(sel)
            if 0 <= idx < n_items
        }
        for i, sub_graphic in enumerate(graphic):
            sub_mat = sub_graphic.world_object.material
            if not isinstance(sub_mat, _POSITIONS_MATERIAL_TYPES):
                continue
            sub_mat.uniform_buffer.data["highlight_alpha"] = self._alpha
            sub_mat.uniform_buffer.update_range()
            n_vertices = sub_graphic.data.value.shape[0]
            id_val = np.uint32(rank_map.get(i, 0))
            self._write_ids(sub_mat, np.full(n_vertices, id_val, dtype=np.uint32))
            self._write_lut(sub_mat, lut)

    def _clear_highlight_buffers(self, graphic) -> None:
        for sub_graphic in graphic:
            sub_mat = sub_graphic.world_object.material
            if not isinstance(sub_mat, _POSITIONS_MATERIAL_TYPES):
                continue
            n_vertices = sub_graphic.data.value.shape[0]
            self._write_ids(sub_mat, np.zeros(n_vertices, dtype=np.uint32))
            self._write_lut(sub_mat, np.zeros((1, 4), dtype=np.float32))

    def __len__(self) -> int:
        return len(self._selection)

    def __contains__(self, item) -> bool:
        return int(item) in self._selection

    def __iter__(self):
        return iter(self._selection)

    def __repr__(self) -> str:
        return (
            f"CollectionHighlightSelector("
            f"selection={self._selection}, "
            f"n_graphics={len(self._graphics)})"
        )


class ImageHighlightSelector(HighlightSelector):
    """
    Highlights pixel regions of an ImageGraphic.

    ``selection`` is a dict with up to three keys:

    * ``"rows"`` — list of row specs; each spec is an int, list of ints, or slice.
      Selects those rows across all columns.
    * ``"cols"`` — list of col specs; each spec is an int, list of ints, or slice.
      Selects those cols across all rows.
    * ``"pixels"`` — list of ``(n, 2)`` arrays of ``[[row, col], ...]`` coordinates.

    When both ``"rows"`` and ``"cols"`` are given they must have the same length
    and are zipped: ``rows[i]`` × ``cols[i]`` defines a rectangle for LUT index i.

    LUT index corresponds to position in the list (or among zipped pairs when
    both ``"rows"`` and ``"cols"`` are present), followed by ``"pixels"`` items.

    Parameters
    ----------
    color : str or array-like, default "cyan"
        Color applied to all selected pixels when no ``lut`` is set.
    lut : np.ndarray of shape (k, 4), optional
        Per-item RGBA colors; ``lut[i]`` applies to the i-th item.
    alpha : float, default 1.0
        Highlight blend strength in [0, 1].
    """

    _VALID_KEYS = frozenset(("rows", "cols", "pixels"))

    def __init__(
        self,
        color: str | np.ndarray = "cyan",
        lut: np.ndarray | None = None,
        alpha: float = 1.0,
    ):
        super().__init__(color=color, lut=lut, alpha=alpha)
        self._selection: dict[str, list] = {}

    @staticmethod
    def _resolve_spec(spec, size: int) -> np.ndarray:
        if isinstance(spec, slice):
            return np.arange(size)[spec]
        return np.atleast_1d(spec)

    def _iter_items(self, n_rows: int, n_cols: int):
        """Yield (row_indices, col_indices) arrays for each logical item."""
        rows = self._selection.get("rows", [])
        cols = self._selection.get("cols", [])
        if rows and cols:
            if len(rows) != len(cols):
                raise ValueError(
                    f"'rows' and 'cols' must have the same length when both given "
                    f"({len(rows)} vs {len(cols)})"
                )
            for rs, cs in zip(rows, cols):
                ri = self._resolve_spec(rs, n_rows)
                ci = self._resolve_spec(cs, n_cols)
                rr, cc = np.meshgrid(ri, ci, indexing="ij")
                yield rr.ravel(), cc.ravel()
        else:
            for rs in rows:
                ri = self._resolve_spec(rs, n_rows)
                rr, cc = np.meshgrid(ri, np.arange(n_cols), indexing="ij")
                yield rr.ravel(), cc.ravel()
            for cs in cols:
                ci = self._resolve_spec(cs, n_cols)
                rr, cc = np.meshgrid(np.arange(n_rows), ci, indexing="ij")
                yield rr.ravel(), cc.ravel()
        for px in self._selection.get("pixels", []):
            arr = np.asarray(px)
            yield arr[:, 0], arr[:, 1]

    def _n_items(self) -> int:
        rows = self._selection.get("rows", [])
        cols = self._selection.get("cols", [])
        n = len(rows) if (rows and cols) else len(rows) + len(cols)
        return n + len(self._selection.get("pixels", []))

    @property
    def selection(self) -> dict[str, list]:
        """Dict of selection specifiers. Empty selection is ``{}``."""
        return {k: list(v) for k, v in self._selection.items()}

    @selection.setter
    def selection(self, value: dict | None) -> None:
        if not value:
            self._selection = {}
        else:
            for k in value:
                if k not in self._VALID_KEYS:
                    raise ValueError(f"Unknown key {k!r}. Must be one of {self._VALID_KEYS}")
            self._selection = {k: list(v) for k, v in value.items()}
        self._update_all_graphics()
        self._emit({"value": self.selection})

    def append(self, key: str, item) -> None:
        """
        Append one item to the selection.

        Parameters
        ----------
        key : str
            One of ``"rows"``, ``"cols"``, ``"pixels"``.
        item : int | list[int] | slice | np.ndarray
            The item to append (see class docstring for format per key).
        """
        if key not in self._VALID_KEYS:
            raise ValueError(f"Unknown key {key!r}. Must be one of {self._VALID_KEYS}")
        self._selection.setdefault(key, []).append(item)
        self._update_all_graphics()
        self._emit({"value": self.selection})

    def remove(self, key: str, index: int = -1) -> None:
        """
        Remove one item from the selection.

        Parameters
        ----------
        key : str
            Selection key.
        index : int, default -1
            Index of the item within that key's list to remove.
        """
        if key not in self._selection:
            raise KeyError(f"{key!r} is not in the selection.")
        self._selection[key].pop(index)
        if not self._selection[key]:
            del self._selection[key]
        self._update_all_graphics()
        self._emit({"value": self.selection})

    def clear(self) -> None:
        """Remove all highlighted regions."""
        self._selection = {}
        self._update_all_graphics()
        self._emit({"value": {}})

    def _validate_graphic(self, graphic) -> None:
        mat = getattr(graphic, "_material", None)
        if not isinstance(mat, HighlightableImageMaterial):
            raise TypeError(
                f"ImageHighlightSelector requires HighlightableImageMaterial, "
                f"got {type(mat).__name__}."
            )

    def _update_highlight_buffers(self, graphic) -> None:
        mat = graphic._material
        mat.uniform_buffer.data["highlight_alpha"] = self._alpha
        mat.uniform_buffer.update_range()

        n_rows, n_cols = graphic.data.value.shape[:2]
        mask = np.zeros((n_rows, n_cols), dtype=np.uint8)
        for mask_id, (ri, ci) in enumerate(self._iter_items(n_rows, n_cols), start=1):
            mask[ri, ci] = np.uint8(mask_id)

        cur = mat._highlight_mask_texture
        if cur.data.shape[0] != n_rows or cur.data.shape[1] != n_cols:
            mat._highlight_mask_texture = Texture(mask.copy(), dim=2)
        else:
            cur.data[:] = mask
            cur.update_range((0, 0, 0), cur.size)

        n = self._n_items()
        lut = mat._highlight_lut_buffer.data
        lut[:] = 0.0
        if n > 0:
            lut[:n] = _build_lut(self._color, self._lut_source, n)
        mat._highlight_lut_buffer.update_range()

    def _clear_highlight_buffers(self, graphic) -> None:
        mat = graphic._material
        n_rows, n_cols = graphic.data.value.shape[:2]
        mat._highlight_mask_texture = Texture(
            np.zeros((n_rows, n_cols), dtype=np.uint8), dim=2
        )
        self._write_lut(mat, np.zeros((1, 4), dtype=np.float32))

    def __len__(self) -> int:
        return self._n_items()

    def __contains__(self, item) -> bool:
        return item in self._selection

    def __iter__(self):
        return iter(self._selection.values())

    def __repr__(self) -> str:
        summary = {k: len(v) for k, v in self._selection.items()}
        return (
            f"ImageHighlightSelector("
            f"selection={summary}, "
            f"n_graphics={len(self._graphics)})"
        )
