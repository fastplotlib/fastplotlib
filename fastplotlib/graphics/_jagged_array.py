import itertools
import operator
from collections.abc import Iterable

import numpy as np

from .features import BufferManager, TextureArray, TextureArrayVolume
from .features._base import GraphicFeature, GraphicFeatureEvent
from .features.utils import is_single_color
from .features.types import ColorLike, MultiColorLike, ColormapLike
from ._base import Graphic


# array-buffer features are indexed along the datapoint axis (vertex buffers, image/volume
# textures), as opposed to uniforms which hold a single value for the whole graphic
ARRAY_BUFFER_FEATURES = (BufferManager, TextureArray, TextureArrayVolume)


class Accessor(GraphicFeature):
    """
    Get and set a feature across the graphics of a collection, along the graphic axis.

    Manages features that are one value per graphic, such as ``thickness`` and
    ``edge_width``. :class:`.JaggedArray` and :class:`.Cmap` subclass this for the
    per-datapoint features and for colormaps.

    Subclasses ``GraphicFeature`` so a collection can register handlers on the accessor;
    ``__setitem__`` emits one collection-level ``GraphicFeatureEvent``.
    """

    def __init__(self, graphics: np.ndarray, feature: str, value_ndim: int = 0, feature_name: str = None):
        """
        Parameters
        ----------
        graphics: np.ndarray of Graphic
            object array of the graphics in the collection; the ``GraphicCollection`` creates
            and maintains it so it can be indexed directly by the graphic-axis key

        feature: str
            name of the graphic feature on each graphic, used with ``getattr``/``setattr``,
            e.g. "data", "colors", "offset"

        value_ndim: int
            number of dimensions of a value that applies to every graphic: a scalar for
            ``thickness``/``sizes`` -> 0, a ``[3]`` for ``offset`` -> 1, one ``[n_datapoints, 3]``
            for ``data`` -> 2. A value with more dimensions has the graphics along its first axis.

        feature_name: str, optional
            name this accessor is exposed as on the collection and used for its events;
            defaults to ``feature``. Differs when a per-graphic feature is renamed to avoid
            clashing with the collection's own feature, e.g. ``offset`` -> ``offsets``.

        """
        feature_name = feature_name if feature_name is not None else feature
        super().__init__(property_name=feature_name)
        self._graphics = graphics
        self._feature = feature
        self._feature_name = feature_name
        self._value_ndim = value_ndim

    def _parse_feature_value(self, value, buffer_key: tuple):
        # base features pass the value through; subclasses parse colors, jagged arrays, etc.
        return value

    def _is_single_value(self, value) -> bool:
        # a single value goes to every graphic; a value with the graphics along its first
        # axis does not. subclasses refine (e.g. a single color for ``colors``)
        if isinstance(value, np.ndarray) and value.dtype == object:
            return False
        return np.ndim(value) <= self._value_ndim

    def _broadcast_over_graphics(self, value, n_graphics: int):
        # one value goes to every graphic; otherwise the first axis is the graphics axis.
        # used by both the setters and the collection constructor
        if self._is_single_value(value):
            return itertools.repeat(value)

        if len(value) != n_graphics:
            raise IndexError(
                f"got {len(value)} values along the first axis for {n_graphics} graphics"
            )
        return value  # value[i] for graphic i, views along the first axis

    def _emit_event(self, key, value):
        # one collection-level event; the collection registers handlers on this accessor
        if len(self._event_handlers) < 1:
            return
        event = GraphicFeatureEvent(self._feature_name, info={"key": key, "value": value})
        self._call_event_handlers(event)

    def _apply_operator(self, func):
        # one value per graphic, so the read is a plain array numpy operates on directly
        return func(self[:])

    def __getitem__(self, graphic_key):
        if isinstance(graphic_key, (int, np.integer)):
            return getattr(self._graphics[graphic_key], self._feature)

        selected = self._graphics[graphic_key]
        return np.array([getattr(g, self._feature) for g in selected])

    def __setitem__(self, graphic_key, value):
        # a single graphic -> set it directly
        if isinstance(graphic_key, (int, np.integer)):
            setattr(self._graphics[graphic_key], self._feature, value)
            self._emit_event(graphic_key, value)
            return

        # broadcast the value over the selected graphics, then set it on each
        selected = self._graphics[graphic_key]
        for graphic, graphic_value in zip(
            selected, self._broadcast_over_graphics(value, len(selected))
        ):
            setattr(graphic, self._feature, graphic_value)
        self._emit_event(graphic_key, value)

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

    def _is_array_buffer(self, feature) -> bool:
        # a feature indexed along the datapoint axis, as opposed to a uniform (see ARRAY_BUFFER_FEATURES)
        return isinstance(feature, ARRAY_BUFFER_FEATURES)

    def _feature_value(self, graphic: Graphic) -> np.ndarray:
        # a graphic's whole feature value: the array buffer, or the uniform value
        feature = getattr(graphic, self._feature)
        if self._is_array_buffer(feature):
            return feature.value
        return np.asarray(feature)

    def _get(self, graphic, buffer_key: tuple):
        feature = getattr(graphic, self._feature)
        if self._is_array_buffer(feature):
            # a view; the buffer needs a first axis, so `()` becomes `[:]`
            return feature[buffer_key or (slice(None),)]
        value = np.asarray(feature)
        return value[buffer_key] if buffer_key else value

    def _set(self, graphic, buffer_key: tuple, value):
        # set one graphic's feature at the buffer_key (within-graphic) key
        feature: BufferManager = getattr(graphic, self._feature)
        if self._is_array_buffer(feature):
            # per-datapoint: write into the buffer, numpy broadcasts `value` within the graphic.
            # a plain slice (not a tuple) so a whole-graphic set parses color specs
            if buffer_key == ():
                # was sliced with graphic.feature[:] = value
                # we need it to call feature.set_value() rather than __setitem__ so buffer is resized if required
                feature.set_value(graphic, value)
            else:
                print("slice")
                feature[buffer_key or slice(None)] = value
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
        # every selected graphic must use either a uniform or an array buffer, not a mix
        buffer = self._is_array_buffer(getattr(graphics[0], self._feature))
        if not all(self._is_array_buffer(getattr(g, self._feature)) == buffer for g in graphics):
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
        # a sequence of per-graphic values; an object array when they are jagged (differing
        # shapes), otherwise a regular array. buffer_key is used by the ColorArray subclass
        if isinstance(value, (list, tuple)):
            if len({np.shape(v) for v in value}) > 1:
                return np.array(value, dtype=object)
            return np.asarray(value)
        return value

    def _apply_operator(self, func):
        # per-datapoint feature: apply to each graphic's view (numpy broadcasting within the
        # graphic). an object array of per-graphic results, no stacking (no copy) so it stays
        # jagged-aware
        views = self[:]
        out = np.empty(len(views), dtype=object)
        for i, view in enumerate(views):
            out[i] = func(view)
        return out

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
            self._emit_event(key, value)
            return

        # multiple graphics: they must all be the same mode, then split `value` along the
        # graphic axis and hand each graphic its piece
        selected = self._graphics[graphic_key]
        self._verify_homogenous_buffer_type(selected)
        for graphic, graphic_value in zip(
            selected, self._broadcast_over_graphics(value, len(selected))
        ):
            self._set(graphic, buffer_key, graphic_value)
        self._emit_event(key, value)


class ColorArray(JaggedArray):
    """
    :class:`.JaggedArray` for ``colors``. Parses color specs to RGBA before the graphic-axis
    split, unless the key indexes the RGBA axis, in which case the value is used as-is.
    """

    def _parse_feature_value(self, value: ColorLike | MultiColorLike, buffer_key: tuple):
        # the RGBA axis is the last one; when the buffer_key reaches it the value is raw numbers
        if buffer_key and len(buffer_key) >= self._feature_ndim() - 1:
            return super()._parse_feature_value(value, buffer_key)
        # a color spec, or a sequence of them; each graphic parses its own colors
        return value

    def _is_single_value(self, value) -> bool:
        # a single color, or a scalar (e.g. one raw channel value), goes to every graphic
        if isinstance(value, (list, tuple)):
            return is_single_color(value)
        return np.ndim(value) == 0 or is_single_color(value)


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
            graphic = self._graphics[graphic_key]
            self._verify_cmap_mode([getattr(graphic, self._feature)])
            setattr(graphic, self._feature, value)
            self._emit_event(graphic_key, value)
            return

        selected = self._graphics[graphic_key]
        self._verify_cmap_mode([getattr(g, self._feature) for g in selected])
        if isinstance(value, (list, tuple, np.ndarray)):
            if len(value) != len(selected):
                raise ValueError(f"expected {len(selected)} colormaps, got {len(value)}")
            cmaps = value
        else:
            # one colormap for all selected graphics
            cmaps = itertools.repeat(value)

        for graphic, cmap in zip(selected, cmaps):
            setattr(graphic, self._feature, cmap)
        self._emit_event(graphic_key, value)

    def _verify_cmap_mode(self, cmaps):
        if any(cmap is None for cmap in cmaps):
            raise TypeError(
                "some selected graphics have no per-graphic colormap; set colormaps per "
                "graphic first (a single colormap across the whole collection is set with "
                "`collection.cmap = ...`)"
            )


def _binary_operator(op):  # collection <op> other
    def method(self, other):
        return self._apply_operator(lambda view: op(view, other))

    return method


def _reflected_operator(op):  # other <op> collection
    def method(self, other):
        return self._apply_operator(lambda view: op(other, view))

    return method


def _unary_operator(op):
    def method(self):
        return self._apply_operator(op)

    return method


# comparison, arithmetic, and bitwise operators act on the values across the graphics like a numpy
# array, jagged along the datapoint axis, e.g. `collection.thickness < 3` or `collection.colors ==
# "r"`; useful for masking the graphic axis, e.g. `collection[collection.thickness < 3]`
for _name in ("lt", "le", "eq", "ne", "gt", "ge", "add", "sub", "mul", "truediv", "floordiv",
              "mod", "pow", "matmul", "and_", "or_", "xor", "lshift", "rshift"):
    setattr(Accessor, f"__{_name.rstrip('_')}__", _binary_operator(getattr(operator, _name)))

for _name in ("add", "sub", "mul", "truediv", "floordiv", "mod", "pow", "matmul",
              "and_", "or_", "xor", "lshift", "rshift"):
    setattr(Accessor, f"__r{_name.rstrip('_')}__", _reflected_operator(getattr(operator, _name)))

for _name in ("neg", "pos", "abs", "invert"):
    setattr(Accessor, f"__{_name}__", _unary_operator(getattr(operator, _name)))
