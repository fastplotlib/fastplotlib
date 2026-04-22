from __future__ import annotations

from numbers import Integral
from typing import Callable, Literal
from warnings import warn

import cmap as cmap_lib
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

cmap_lib.Colormap("tab10").lut()


def _build_lut(
    color: str | np.ndarray = "red",
    lut: np.ndarray | None = None,
    n: int = 1,
    lut_wrap: Literal["fixed", "repeat"] = "fixed",
) -> np.ndarray:
    """
    Return an (n, 4) float32 RGBA array for n selected items.
    """

    if n == 0:
        return np.zeros((1, 4), dtype=np.float32)

    if lut is not None:
        if isinstance(lut, str):
            lut = cmap_lib.Colormap(lut).lut(n)

        lut = np.asarray(lut, dtype=np.float32)

        if lut.ndim != 2 or lut.shape[1] != 4:
            raise ValueError("`lut` must have shape (n, 4) for n selected items")

        if lut_wrap == "repeat":
            return lut[np.arange(n) % len(lut)]

        if lut.shape[0] < n:
            raise ValueError(
                f"`lut` has only {lut.shape[0]} entries but {n} are selected"
            )

        return lut[:n]

    return np.repeat([pygfx.Color(color)], n, axis=0)


class HighlightSelector:
    """
    Base class managing highlight state on one or more graphics.

    Highlights selected vertices or image regions by blending a color into the
    rendered output. Does not create extra world objects, so ``pick_info``
    is unaffected.

    Use the subclasses:

    * :class:`PositionsHighlightSelector`: highlight individual vertices on a
      LineGraphic or ScatterGraphic
    * :class:`CollectionHighlightSelector`: highlight whole lines/scatters in
      a collection
    * :class:`ImageHighlightSelector`: highlight pixel regions of an ImageGraphic
    """

    def __init__(
        self,
        color: str | np.ndarray = "red",
        lut: str | np.ndarray | None = None,
        lut_wrap: Literal["fixed", "repeat"] = "fixed",
        alpha: float = 0.7,
    ):
        if lut_wrap not in ("fixed", "repeat"):
            raise ValueError(f"lut_wrap must be 'fixed' or 'repeat', got {lut_wrap!r}")

        self._color = color
        self._lut = lut
        self._alpha = float(alpha)
        self._lut_wrap = lut_wrap
        self._graphics = list()
        self._event_handlers: list[Callable] = list()

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

    @property
    def color(self) -> str | np.ndarray:
        """
        Get or set color applied to all selected items, used if ``lut`` is ``None``.

        Accepts any value that ``pygfx.Color`` understands (color name string,
        RGBA tuple, hex string, etc.).
        """
        return self._color

    @color.setter
    def color(self, value):
        self._color = value
        self._update_all_graphics()

    @property
    def lut(self) -> str | np.ndarray | None:
        """
        Get or set per-item color lookup table, shape ``(n, 4)`` float32 RGBA, or a str
        that defines a colormap.

        When set, ``lut[i]`` is the highlight color for the i-th selected item.
        Must have at least as many rows as the number of selected items.
        Set to ``None`` to fall back to ``color``.
        """
        return self._lut

    @lut.setter
    def lut(self, value: np.ndarray | None):
        self._lut = value
        self._update_all_graphics()

    @property
    def lut_wrap(self) -> str:
        """
        Get or set LUT wrap mode.
        - "fixed":  no wrapping, fixed to size of the given LUT
        - "repeat": cycles through the colormap when n_selections > lut_size"""
        return self._lut_wrap

    @property
    def alpha(self) -> float:
        """Get or set alpha value, 0 - 1.0"""
        return self._alpha

    @alpha.setter
    def alpha(self, value: float):
        self._alpha = float(value)
        self._update_all_graphics()

    @property
    def graphics(self) -> list:
        """Get graphics the highlight selector is operating on."""
        return list(self._graphics)

    def add_graphic(self, graphic) -> None:
        """Add ``graphic`` and apply the current highlight selection to it."""
        if graphic in self._graphics:
            warn(f"{graphic!r} is already attached to this selector.")
            return

        self._check_graphic(graphic)
        self._graphics.append(graphic)
        self._update_highlight_buffers(graphic)

    def remove_graphic(self, graphic) -> None:
        """remove ``graphic`` and clear its highlight buffer."""
        if graphic not in self._graphics:
            raise KeyError(f"{graphic!r} is not attached to this selector.")
        self._graphics.remove(graphic)
        self._clear_highlight_buffers(graphic)

    def _check_graphic(self, graphic) -> None:
        raise NotImplementedError

    def _update_highlight_buffers(self, graphic) -> None:
        raise NotImplementedError

    def _clear_highlight_buffers(self, graphic) -> None:
        raise NotImplementedError

    def add_event_handler(self, handler: Callable) -> None:
        """Add a callback that is called when the selection changes."""
        if not callable(handler):
            raise TypeError("event handler must be callable")

        if handler in self._event_handlers:
            warn(f"{handler} is already registered.")
            return

        self._event_handlers.append(handler)

    def remove_event_handler(self, handler: Callable) -> None:
        """Remove an event handler."""
        if handler not in self._event_handlers:
            raise KeyError(f"{handler} is not registered.")

        self._event_handlers.remove(handler)

    def _emit(self, info: dict) -> None:
        for h in self._event_handlers:
            h({"selector": self, **info})

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

    def __len__(self) -> int:
        raise NotImplementedError

    def __contains__(self, item) -> bool:
        raise NotImplementedError

    def __iter__(self):
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}\n" f"selection: {self.selection}"


class PositionsHighlightSelector(HighlightSelector):
    """
    Highlights individual data points on a LineGraphic or ScatterGraphic.

    Parameters
    ----------
    color : str or array-like, default "cyan"
        Color applied to all selected vertices when no ``lut`` is set.

    lut : np.ndarray of shape (n, 4), optional
        Per-vertex RGBA colors; ``lut[i]`` applies to the i-th selected vertex.

    lut_wrap: "fixed" or "repeat"
        - "fixed":  no wrapping, fixed to size of the given LUT
        - "repeat": cycles through the colormap when n_selections > lut_size

    alpha : float, default 1.0
        Highlight blend strength in [0, 1].

    """

    def __init__(
        self,
        color: str | np.ndarray = "red",
        lut: str | np.ndarray | None = None,
        lut_wrap: Literal["fixed", "repeat"] = "fixed",
        alpha: float = 1.0,
    ):
        super().__init__(color=color, lut=lut, lut_wrap=lut_wrap, alpha=alpha)
        self._selection: list[int] = list()

    @property
    def selection(self) -> tuple[int, ...]:
        """
        Get or set selected vertex indices.
        """
        return tuple(self._selection)

    @selection.setter
    def selection(self, value) -> None:
        if value is None or len(value) == 0:
            self._selection = list()
        else:
            if isinstance(value, Integral):
                value = [value]

            if not all([isinstance(i, Integral) for i in value]):
                raise TypeError(f"selection must be an iterable of <int>\ngot: {value}")

            # convert to list
            self._selection = list(map(int, value))

        self._update_all_graphics()
        self._emit({"value": tuple(self._selection)})

    # TODO: need to review the rest of these method
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

    def _check_graphic(self, graphic) -> None:
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
        self._write_lut(
            mat,
            _build_lut(self._color, self._lut, len(self._selection), self._lut_wrap),
        )

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


# TODO: review
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

    def _check_graphic(self, graphic) -> None:
        if not isinstance(graphic, GraphicCollection):
            raise TypeError(
                f"CollectionHighlightSelector requires a GraphicCollection, "
                f"got {type(graphic).__name__}."
            )

    def _update_highlight_buffers(self, graphic) -> None:
        n_items = len(graphic)
        sel = self._selection
        lut = _build_lut(self._color, self._lut, len(sel), self._lut_wrap)
        rank_map = {idx: rank + 1 for rank, idx in enumerate(sel) if 0 <= idx < n_items}
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

    Can be used in two modes:

    **Free-selection mode**, if ``selection_options`` is ``None``:

    ``selection`` is a dict with keys:

        - "rows": list of row specs (int, list[int], or slice); selects those rows across all cols.
        - "cols": list of col specs (int, list[int], or slice); selects those cols across all rows.
        - "pixels": list of ``(n, 2)`` arrays of ``[[row, col], ...]`` coordinates.

    When both "rows" and "cols" are given they must have the same length each pair defines a rectangle.

    **Options mode**, if ``selection_options`` is set:

    All options are shown with ``options_color`` & ``options_alpha``.
    ``selection`` is an ``int`` or ``list[int]`` indexing into the options, selected items are shown
    with the highlight ``color`` or ``lut`` & ``alpha``.
    Only the LUT is rewritten on selection change, not the mask.

    Parameters
    ----------
    color : str or array-like, default "red"
        Highlight color for selected items.

    lut : np.ndarray of shape (n, 4), optional
        RGBA colors for each selected item

    alpha : float, default 1.0
        alpha blending value

    options_color : str or array-like, default "w"
        Color shown for unselected option items.

    options_alpha : float, default 0.1
        alpha blend value for unselected items

    selection_options : dict or None, optional
        Pool of selectable options (same dict format as ``selection`` in free-selection mode).

    """

    _VALID_KEYS = frozenset(("rows", "cols", "pixels"))

    def __init__(
        self,
        color: str | np.ndarray = "red",
        lut: np.ndarray | None = None,
        alpha: float = 0.7,
        lut_wrap: str = "fixed",
        options_color: str | np.ndarray = "w",
        options_alpha: float = 0.1,
        selection_options: dict | None = None,
    ):
        super().__init__(color=color, lut=lut, alpha=alpha, lut_wrap=lut_wrap)

        self._selection: dict[str, list] = dict()
        self._selected_indices: list[int] = list()
        self._options_color = options_color
        self._options_alpha = float(options_alpha)

        # validate and store selection_options without triggering _update_all_graphics
        # no graphics are targeted yet
        if selection_options is not None:
            for k in selection_options:
                if k not in self._VALID_KEYS:
                    raise ValueError(
                        f"Unknown key {k!r}. Must be one of {self._VALID_KEYS}"
                    )
            self._selection_options: dict[str, list] | None = {
                k: list(v) for k, v in selection_options.items()
            }
        else:
            self._selection_options = None

    @staticmethod
    def _resolve_spec(spec, size: int) -> np.ndarray:
        if isinstance(spec, slice):
            return np.arange(size)[spec]
        return np.atleast_1d(spec)

    def _iter_items(self, sel: dict, n_rows: int, n_cols: int):
        """Yield (row_indices, col_indices) for each logical item in *sel*."""
        rows = sel.get("rows", [])
        cols = sel.get("cols", [])
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
        for px in sel.get("pixels", []):
            arr = np.asarray(px)
            yield arr[:, 0], arr[:, 1]

    def _count_items(self, sel: dict) -> int:
        rows = sel.get("rows", [])
        cols = sel.get("cols", [])
        n = len(rows) if (rows and cols) else len(rows) + len(cols)
        return n + len(sel.get("pixels", []))

    @staticmethod
    def _rgba(color, alpha: float) -> np.ndarray:
        c = np.array(pygfx.Color(color), dtype=np.float32)
        c[3] = float(alpha)
        return c

    def _write_mask(self, mat, mask: np.ndarray, n_rows: int, n_cols: int) -> None:
        cur = mat._highlight_mask_texture
        if cur.data.shape[0] != n_rows or cur.data.shape[1] != n_cols:
            mat._highlight_mask_texture = Texture(mask.copy(), dim=2)
        else:
            cur.data[:] = mask
            cur.update_range((0, 0, 0), cur.size)

    @property
    def selection_options(self) -> dict[str, tuple] | None:
        """
        Get or set a pool of selectable items (same dict format as ``selection`` in free mode).
        When set, all options highlighted using ``options_color`` and ``options_alpha``.
        ``selection`` indexes into this pool.
        Setting to ``None`` reverts to free-selection mode and clears the selection.
        """
        if self._selection_options is None:
            return None

        # return a new dict with a tuple of the selections so the user can't modify the objects
        return {k: tuple(v) for k, v in self._selection_options.items()}

    @selection_options.setter
    def selection_options(self, value: dict | None) -> None:
        if value is None:
            self._selection_options = None
        else:
            for k in value:
                if k not in self._VALID_KEYS:
                    raise ValueError(
                        f"Unknown key {k!r}. Must be one of {self._VALID_KEYS}"
                    )
            self._selection_options = {k: list(v) for k, v in value.items()}

        self._selected_indices = list()
        self._selection = dict()
        self._update_all_graphics()
        self._emit({"value": self.selection})

    @property
    def options_color(self) -> str | np.ndarray:
        """Get or set color for unselected option items (options mode only)."""
        return self._options_color

    @options_color.setter
    def options_color(self, value: str | np.ndarray) -> None:
        self._options_color = value

        if self._selection_options is not None:
            self._update_all_graphics()

    @property
    def options_alpha(self) -> float:
        """Get or set alpha blend value of unselected option items (options mode only)."""
        return self._options_alpha

    @options_alpha.setter
    def options_alpha(self, value: float) -> None:
        self._options_alpha = float(value)

        if self._selection_options is not None:
            self._update_all_graphics()

    @property
    def selection(self) -> tuple[int, ...] | dict[str, tuple]:
        """
        In options mode: tuple of selection option indices.
        In free mode: dict of selection items.
        """
        if self._selection_options is not None:
            return tuple(self._selected_indices)

        # return a new dict with a tuple of the selections so the user can't modify the objects
        return {k: tuple(v) for k, v in self._selection.items()}

    @selection.setter
    def selection(self, value: dict[Literal["rows", "cols", "pixels"], list]) -> None:
        if self._selection_options is not None:
            if value is None:
                self._selected_indices = list()

            elif isinstance(value, int):
                self._selected_indices = [value]

            else:
                self._selected_indices = [int(i) for i in value]

        else:
            if not value:
                self._selection = {}

            else:
                for k in value:
                    if k not in self._VALID_KEYS:
                        raise ValueError(
                            f"Unknown key {k!r}. Must be one of {self._VALID_KEYS}"
                        )

                self._selection = {k: list(v) for k, v in value.items()}

        self._update_all_graphics()
        self._emit({"value": self.selection})

    def append(self, dict_or_index: dict | int) -> None:
        """
        append to the current selection
        """
        if self._selection_options is not None:
            # options mode
            index = dict_or_index
            if not isinstance(index, Integral):
                raise TypeError(
                    f"must provide integer index to append to selection "
                    f"in 'options' mode, you passed: {dict_or_index!r}"
                )
            if index not in self._selected_indices:
                self._selected_indices.append(index)
                self._update_all_graphics()
                self._emit({"value": self.selection})
        else:
            d = dict_or_index
            # check that dict is valid
            keys = list(d.keys())
            err = f"must provide a dict of only rows, cols, rows & cols, or pixels, you passed a dict with keys: {keys}"

            if any([k not in self._VALID_KEYS for k in keys]):
                raise KeyError(err)

            if "pixels" in keys and len(keys) > 1:
                raise KeyError(err)

            if "rows" in keys and "cols" in keys:
                if len(d["rows"]) != len(d["cols"]):
                    raise ValueError(
                        f"if appending pairs of rows & cols, they must be of the same length"
                    )
                rows, cols = d["rows"], d["cols"]
                if not all(
                    [
                        isinstance(r, slice) and isinstance(c, slice)
                        for r, c in zip(rows, cols)
                    ]
                ):
                    raise ValueError(
                        f"if appending pairs of rows & cols, each row and column pair must be a slice, you passed: {d}"
                    )
            for k in keys:
                self._selection.setdefault(k, list()).append(d[k])

            self._update_all_graphics()
            self._emit({"value": self.selection})

    def remove(self, dict_or_index: dict | int) -> None:
        """
        In options mode: ``remove(index)``: remove an option index from the selection.
        In free mode: ``remove(key, list_index=-1)``: remove one item from the selection dict.
        """
        if self._selection_options is not None:
            # options mode
            index = dict_or_index
            if not isinstance(index, Integral):
                raise TypeError(
                    f"must provide integer index to append to selection "
                    f"in 'options' mode, you passed: {dict_or_index!r}"
                )
            if index in self._selected_indices:
                self._selected_indices.remove(index)
                self._update_all_graphics()
                self._emit({"value": self.selection})
        else:
            d = dict_or_index
            keys = list(d.keys())
            if any([k not in self._selection for k in keys]):
                raise KeyError(
                    f"You provided keys that are  not in the selection.\nkeys: {keys}\nselection: {self._selection}"
                )

            for k in keys:
                for item in d[k]:
                    self._selection[k].remove(item)
                if len(self._selection[k]) < 1:
                    del self._selection[k]

            self._update_all_graphics()
            self._emit({"value": self.selection})

    def clear(self) -> None:
        """Clear the selection (options mode: deselects all, free mode: clears all regions)."""
        if self._selection_options is not None:
            # options mode
            self._selected_indices = list()
        else:
            self._selection = dict()
        self._update_all_graphics()
        self._emit({"value": self.selection})

    def _check_graphic(self, graphic) -> None:
        mat = getattr(graphic, "_material", None)
        if not isinstance(mat, HighlightableImageMaterial):
            raise TypeError(
                f"ImageHighlightSelector requires HighlightableImageMaterial, "
                f"got {type(mat).__name__}."
            )

    def _update_highlight_buffers(self, graphic) -> None:
        mat = graphic._material
        # highlight_alpha uniform is 1.0, per-item alpha is in the LUT.
        mat.uniform_buffer.data["highlight_alpha"] = 1.0
        mat.uniform_buffer.update_range()

        n_rows, n_cols = graphic.data.value.shape[:2]
        if self._selection_options is not None:
            self._update_options_mode(mat, n_rows, n_cols)
        else:
            self._update_free_mode(mat, n_rows, n_cols)

    def _update_options_mode(self, mat, n_rows: int, n_cols: int) -> None:
        mask = np.zeros((n_rows, n_cols), dtype=np.uint16)
        items = list(self._iter_items(self._selection_options, n_rows, n_cols))
        for mask_id, (ri, ci) in enumerate(items, start=1):
            mask[ri, ci] = np.uint16(mask_id)
        self._write_mask(mat, mask, n_rows, n_cols)

        opts_rgba = self._rgba(self._options_color, self._options_alpha)
        lut = mat._highlight_lut_buffer.data
        lut[:] = 0.0
        for i in range(len(items)):
            lut[i] = opts_rgba
        n_sel = len(self._selected_indices)
        if n_sel > 0:
            sel_colors = _build_lut(self._color, self._lut, n_sel, self._lut_wrap)
            sel_colors[:, 3] *= self._alpha
            for i, opt_idx in enumerate(self._selected_indices):
                lut[opt_idx] = sel_colors[i]
        mat._highlight_lut_buffer.update_range()

    def _update_free_mode(self, mat, n_rows: int, n_cols: int) -> None:
        mask = np.zeros((n_rows, n_cols), dtype=np.uint16)
        for mask_id, (ri, ci) in enumerate(
            self._iter_items(self._selection, n_rows, n_cols), start=1
        ):
            mask[ri, ci] = np.uint16(mask_id)
        self._write_mask(mat, mask, n_rows, n_cols)

        n = self._count_items(self._selection)
        lut = mat._highlight_lut_buffer.data
        lut[:] = 0.0
        if n > 0:
            built = _build_lut(self._color, self._lut, n, self._lut_wrap)
            built[:, 3] *= self._alpha
            lut[:n] = built
        mat._highlight_lut_buffer.update_range()

    def _clear_highlight_buffers(self, graphic) -> None:
        mat = graphic._material
        n_rows, n_cols = graphic.data.value.shape[:2]
        mat._highlight_mask_texture = Texture(
            np.zeros((n_rows, n_cols), dtype=np.uint16), dim=2
        )
        mat._highlight_lut_buffer.data[:] = 0.0
        mat._highlight_lut_buffer.update_range()

    def __len__(self) -> int:
        if self._selection_options is not None:
            return len(self._selected_indices)
        return self._count_items(self._selection)

    def __contains__(self, item) -> bool:
        if self._selection_options is not None:
            return int(item) in self._selected_indices
        return item in self._selection

    def __iter__(self):
        if self._selection_options is not None:
            return iter(self._selected_indices)
        return iter(self._selection.values())

    def __repr__(self) -> str:
        if self._selection_options is not None:
            n_opts = self._count_items(self._selection_options)
            return (
                f"ImageHighlightSelector("
                f"selected={self._selected_indices}, "
                f"n_options={n_opts}, "
                f"n_graphics={len(self._graphics)})"
            )
        summary = {k: len(v) for k, v in self._selection.items()}
        return (
            f"ImageHighlightSelector("
            f"selection={summary}, "
            f"n_graphics={len(self._graphics)})"
        )
