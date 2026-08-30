from collections.abc import Iterable

import numpy as np
import pygfx

from .features import BufferManager
from .features.utils import is_single_color
from .features.types import ColorLike, MultiColorLike, ColormapLike
from ._base import Graphic

class Accessor:
    """
    Get and set a feature across the graphics of a collection, along the graphic axis.

    Manages features that are one value per graphic, such as ``thickness`` and
    ``edge_width``. :class:`.JaggedArray` and :class:`.Cmap` subclass this for the
    per-datapoint features and for colormaps.
    """

    def __init__(self, graphics: np.ndarray, feature: str):
        """
        Parameters
        ----------
        graphics: np.ndarray of Graphic
            object array of the graphics in the collection; the ``GraphicCollection`` creates
            and maintains it so it can be indexed directly by the graphic-axis key

        feature: str
            name of the graphic feature to manage, e.g. "data", "colors", "thickness"

        """
        self._graphics = graphics
        self._feature = feature

    def __getitem__(self, graphic_key):
        if isinstance(graphic_key, (int, np.integer)):
            return getattr(self._graphics[graphic_key], self._feature)

        selected = self._graphics[graphic_key]
        return np.array([getattr(g, self._feature) for g in selected])

    def __setitem__(self, graphic_key, value):
        if isinstance(graphic_key, (int, np.integer)):
            setattr(self._graphics[graphic_key], self._feature, value)
            return

        # broadcast the value over the selected graphics, then set it on each
        selected = self._graphics[graphic_key]
        for graphic, v in zip(selected, np.broadcast_to(value, (len(selected),))):
            setattr(graphic, self._feature, v)

    def __len__(self):
        return len(self._graphics)

    def __repr__(self):
        return f"{self.__class__.__name__} of <{self._feature}> across {len(self)} graphics"


class JaggedArray(Accessor):
    """
    Get and set a per-datapoint feature (``data``, ``colors``, ``sizes``, ...) across a
    collection. Indexing follows numpy broadcasting as if the feature were a rectangular
    array, except each graphic may have a different number of datapoints (jagged).

    A graphic holds the feature per-vertex or uniform
    """

    def _feature_value(self, graphic: Graphic) -> np.ndarray:
        # a graphic's whole feature value: the buffer array, or the uniform value
        feature = getattr(graphic, self._feature)
        if isinstance(feature, BufferManager):
            return feature.value
        return np.asarray(feature)

    def _get(self, graphic, buffer_key: tuple):
        feature = getattr(graphic, self._feature)
        if isinstance(feature, BufferManager):
            # a view; the buffer needs a first axis, so `()` becomes `[:]`
            return feature[buffer_key or (slice(None),)]
        value = np.asarray(feature)
        return value[buffer_key] if buffer_key else value

    def _set(self, graphic, buffer_key: tuple, value):
        # set one graphic's feature at the buffer_key (within-graphic) key
        feature = getattr(graphic, self._feature)
        if isinstance(feature, BufferManager):
            # per-vertex: write into the buffer, numpy broadcasts `value` within the graphic
            feature[buffer_key or (slice(None),)] = value
            return
        # uniform: no datapoint axis, so set the whole value through the graphic's property
        if not buffer_key:
            setattr(graphic, self._feature, value)
            return
        # a component index into a uniform value (e.g. one channel): read it, change that
        # component, write the whole value back
        modified = np.array(feature, dtype=float)
        modified[buffer_key] = value
        setattr(graphic, self._feature, modified)

    def _feature_ndim(self) -> int:
        # graphic axis + a graphic's dimensions
        return self._feature_value(self._graphics[0]).ndim + 1

    def _verify_homogenous_buffer_type(self, graphics):
        # every selected graphic must use either a uniform or per-vertex buffer, not a mix
        buffer = isinstance(getattr(graphics[0], self._feature), BufferManager)
        if not all(isinstance(getattr(g, self._feature), BufferManager) == buffer for g in graphics):
            raise TypeError(
                f"the selected graphics mix uniform and per-vertex '{self._feature}'; "
                f"use either uniform or vertex for all graphics, not a mix"
            )

    def _split_key(self, key):
        # peel the graphic index off axis 0, expanding a trailing/leading ellipsis first
        if not isinstance(key, tuple):
            return key, ()

        if any(k is Ellipsis for k in key):
            used = sum(k is not Ellipsis and k is not None for k in key)
            fill = (slice(None),) * (self._feature_ndim() - used)
            expanded = ()
            for k in key:
                expanded += fill if k is Ellipsis else (k,)
            key = expanded

        return key[0], key[1:]

    def _parse_feature_value(self, value, buffer_key: tuple):
        # a list/tuple becomes an object array, then follows the same broadcasting
        # buffer_key is used by teh ColorArray subclass
        if isinstance(value, (list, tuple)):
            return np.array(value, dtype=object)
        return value

    def __getitem__(self, key):
        # split off the graphic axis; `buffer_key` is the key applied within each graphic
        graphic_key, buffer_key = self._split_key(key)

        # a single graphic -> return its value/view directly
        if isinstance(graphic_key, (int, np.integer)):
            return self._get(self._graphics[graphic_key], buffer_key)

        # multiple graphics -> an object array holding each graphic's view (no copy, no stacking)
        selected = self._graphics[graphic_key]
        out = np.empty(len(selected), dtype=object)
        for i, graphic in enumerate(selected):
            out[i] = self._get(graphic, buffer_key)
        return out

    def __setitem__(self, key, value):
        # split off the graphic axis; `buffer_key` is the key applied within each graphic
        graphic_key, buffer_key = self._split_key(key)
        # lists become object arrays, ColorArray subclass parses color-likes to an RGBA array
        value = self._parse_feature_value(value, buffer_key)

        # a single graphic -> set it directly
        if isinstance(graphic_key, (int, np.integer)):
            self._set(self._graphics[graphic_key], buffer_key, value)
            return

        # multiple graphics: they must all be the same mode, then split `value` along the
        # graphic axis and hand each graphic its piece
        selected = self._graphics[graphic_key]
        self._verify_homogenous_buffer_type(selected)
        for graphic, v in zip(selected, self._broadcast_over_graphics(value, len(selected), selected[0], buffer_key)):
            self._set(graphic, buffer_key, v)

    def _broadcast_over_graphics(self, value, n_selected, sample, buffer_key):
        # split the value along the graphic axis, following numpy broadcasting
        buffer_ndim = np.ndim(self._get(sample, buffer_key))
        value = value if isinstance(value, np.ndarray) else np.asarray(value)

        if value.dtype == object:
            # jagged per-graphic rows: cells are the data, newaxes line up the graphic axis
            expected = (n_selected,) + (1,) * buffer_ndim
            if value.shape != expected:
                raise ValueError(
                    f"a per-graphic object array must be shaped {expected} "
                    f"(add newaxes to line up the graphic axis, e.g. "
                    f"o[:, None{', None' * (buffer_ndim - 1)}]); got {value.shape}"
                )
            return list(value.reshape(n_selected))

        if value.ndim == buffer_ndim + 1:
            # the value carries a graphic axis
            if value.shape[0] == n_selected:
                return list(value)
            if value.shape[0] == 1:
                return [value[0]] * n_selected
            raise ValueError(
                f"could not broadcast the graphic axis: {value.shape[0]} values for "
                f"{n_selected} selected graphics"
            )

        if value.ndim <= buffer_ndim:
            # no graphic axis, the whole value goes into every selected graphic
            return [value] * n_selected

        raise ValueError(
            f"value has {value.ndim} dimensions but the selection has {buffer_ndim + 1}"
        )


class ColorArray(JaggedArray):
    """
    :class:`.JaggedArray` for ``colors``. Parses color specs to RGBA before the graphic-axis
    split, unless the key indexes the RGBA axis, in which case the value is used as-is.
    """

    def _parse_feature_value(self, value: ColorLike | MultiColorLike, buffer_key: tuple):
        # the RGBA axis is the last one; it is indexed when the buffer_key reaches it
        if len(buffer_key) >= self._feature_ndim() - 1:
            return super()._parse_feature_value(value, buffer_key)

        if is_single_color(value):
            return np.asarray(pygfx.Color(value), dtype=np.float32)

        arr = np.asarray(value)
        if arr.dtype.kind in "fiu" and arr.ndim >= 1 and arr.shape[-1] in (3, 4):
            # already an RGB(A) array
            return arr.astype(np.float32)

        return np.asarray([pygfx.Color(c) for c in value], dtype=np.float32)


class Cmap(Accessor):
    """
    :class:`.Accessor` for per-graphic colormaps: ``cmap[graphic_key]`` gets and sets each
    selected graphic's colormap, broadcasting one colormap to all selected graphics or a
    sequence one per graphic.

    Indexing requires per-graphic colormaps. A single colormap across the whole collection,
    which colors each graphic one color by its index, is set through the collection's
    ``cmap`` property setter rather than here.
    """

    def __getitem__(self, graphic_key):
        if isinstance(graphic_key, (int, np.integer)):
            cmaps = [getattr(self._graphics[graphic_key], self._feature)]
            self._verify_cmap_mode(cmaps)
            return cmaps[0]

        cmaps = [getattr(g, self._feature) for g in self._graphics[graphic_key]]
        self._verify_cmap_mode(cmaps)
        out = np.empty(len(cmaps), dtype=object)
        out[:] = cmaps
        return out

    def __setitem__(self, graphic_key, value: ColormapLike | Iterable[ColormapLike]):
        if isinstance(graphic_key, (int, np.integer)):
            setattr(self._graphics[graphic_key], self._feature, value)
            return

        selected = self._graphics[graphic_key]
        if isinstance(value, (list, tuple, np.ndarray)):
            if len(value) != len(selected):
                raise ValueError(f"expected {len(selected)} colormaps, got {len(value)}")
            cmaps = value
        else:
            # one colormap for all selected graphics
            cmaps = [value] * len(selected)

        for graphic, cmap in zip(selected, cmaps):
            setattr(graphic, self._feature, cmap)

    def _verify_cmap_mode(self, cmaps):
        if any(cmap is None for cmap in cmaps):
            raise TypeError(
                "some selected graphics have no per-graphic colormap; set colormaps per "
                "graphic first (a single colormap across the whole collection is set with "
                "`collection.cmap = ...`)"
            )
