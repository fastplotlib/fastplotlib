from __future__ import annotations

import inspect
from collections.abc import Iterable
from typing import Any

import numpy as np
import pygfx
import cmap as cmap_lib

from ._base import Graphic
from ._jagged_array import CollectionFeatureAccessor, JaggedCollectionFeature, CollectionColors, CollectionCmap, ARRAY_BUFFER_FEATURES
from .features import GraphicFeature, VertexColors, UniformColor, VertexCmap


# a feature the collection also owns as a `Graphic` is exposed under a plural name, so
# `collection.offset` is the collection's own offset and `collection.offsets` is the per-graphic
# offsets
PLURAL = {
    "name": "names",
    "offset": "offsets",
    "rotation": "rotations",
    "scale": "scales",
    "alpha": "alphas",
    "alpha_mode": "alpha_modes",
    "visible": "visibles",
}

# features not exposed across the collection
EXCLUDE = {"deleted"}


def get_accessor_class(feature: str, feature_classes: tuple[type, ...]) -> type:
    """the accessor class used to manage a feature across a collection"""
    if UniformColor in feature_classes or VertexColors in feature_classes:
        return CollectionColors
    if VertexCmap in feature_classes:
        return CollectionCmap
    if any(issubclass(c, ARRAY_BUFFER_FEATURES) for c in feature_classes if isinstance(c, type)):
        return JaggedCollectionFeature
    if feature in ("offset", "rotation", "scale"):
        return JaggedCollectionFeature
    return CollectionFeatureAccessor


def get_value_ndim(feature_classes: tuple[type[GraphicFeature], ...]) -> int:
    """number of dimensions of a value that applies to every graphic, i.e. the uniform variant"""
    return min((c.ndim for c in feature_classes if isinstance(c, type)), default=0)


def cmap_across_graphics(
    cmap_name: str, n_graphics: int, transform: np.ndarray = None
) -> np.ndarray:
    """
    ``n_graphics`` colors from a colormap, one per graphic.

    Without a transform the colors are evenly spaced along the colormap. A ``transform`` maps each
    graphic into the colormap instead: it is resampled to one value per graphic and normalized to
    index the colormap as a lookup table.
    """
    if transform is None:
        values = np.linspace(0, 1, n_graphics)
    else:
        transform = np.asarray(transform, dtype=float)
        # resample the transform to one value per graphic
        transform = np.interp(
            np.linspace(0, 1, n_graphics), np.linspace(0, 1, len(transform)), transform
        )
        # normalize to [0, 1] so the values index the colormap
        spread = np.ptp(transform)
        values = (transform - transform.min()) / spread if spread else np.zeros(n_graphics)

    return np.asarray(cmap_lib.Colormap(cmap_name)(values))


class _AccessorProperty(property):
    """marks a property as generated for a collection feature, so a subclass's own explicit
    property for a feature can be told apart from a generated one"""


def make_feature_property(feature_name: str, accessor_class: type) -> property:
    """a property that returns the feature's accessor for get/set across the collection"""

    def getter(collection_instance):
        return getattr(collection_instance, f"_{feature_name}")

    if accessor_class is CollectionCmap:
        # assigning a colormap colors each graphic one color, evenly spaced across the collection
        def setter(collection_instance, value):
            collection_instance.colors[:] = cmap_across_graphics(value, len(collection_instance))
    else:
        def setter(collection_instance, value):
            getattr(collection_instance, f"_{feature_name}")[:] = value

    doc = f"get or set the {feature_name} of the graphics in the collection"
    return _AccessorProperty(getter, setter, doc=doc)


def make_collection_signature(child_type: type, accessor_specs: dict) -> inspect.Signature:
    """
    the collection constructor's signature, derived from the child graphic

    ``data`` becomes the list of per-graphic data, each managed feature accepts one value for all
    graphics or one per graphic (``Iterable``), and construction arguments are passed through as-is.
    """
    parameters = [inspect.Parameter("data", inspect.Parameter.POSITIONAL_OR_KEYWORD)]
    added = {"data"}

    for name, parameter in inspect.signature(child_type.__init__).parameters.items():
        if name in ("self", "data") or parameter.kind in (parameter.VAR_POSITIONAL, parameter.VAR_KEYWORD):
            continue
        feature_name = PLURAL.get(name, name)
        annotation = parameter.annotation
        if feature_name in accessor_specs and annotation is not parameter.empty:
            annotation = Iterable[annotation]
        default = parameter.default if parameter.default is not parameter.empty else None
        parameters.append(
            inspect.Parameter(feature_name, inspect.Parameter.KEYWORD_ONLY, default=default, annotation=annotation)
        )
        added.add(feature_name)

    # features the collection exposes but the child takes via **kwargs, e.g. names, offsets, metadatas
    for feature_name in accessor_specs:
        if feature_name not in added:
            parameters.append(inspect.Parameter(feature_name, inspect.Parameter.KEYWORD_ONLY, default=None))

    return inspect.Signature(parameters)


class GraphicCollection(Graphic):
    """
    A collection of graphics of the same type.

    Subclasses set only ``_child_type``. Each feature of the child graphic is then exposed as a
    property returning an accessor that gets and sets that feature across all of the graphics using
    numpy broadcasting, e.g. ``collection.colors[:10, 30:50] = "r"``. Features the collection also
    owns as a ``Graphic`` (``name``, ``offset``, ``rotation``, ``scale``, ``alpha``, ``alpha_mode``,
    ``visible``, ``metadata``) are exposed under a plural name (``names``, ``offsets``, ...). The
    constructor signature is derived from the child graphic as well.
    """

    _child_type: type[Graphic] = None

    # tooltips come from the child graphics
    _fpl_support_tooltip = False

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls._child_type is None:
            return

        # exposed feature name -> (child feature, accessor class, value_ndim)
        specs = dict()
        for feature, feature_classes in cls._child_type._features.items():
            if feature in EXCLUDE:
                continue
            feature_classes = feature_classes if isinstance(feature_classes, tuple) else (feature_classes,)
            feature_name = PLURAL.get(feature, feature)
            existing = getattr(cls, feature_name, None)
            if isinstance(existing, property) and not isinstance(existing, _AccessorProperty):
                continue  # the subclass implements this feature with its own property; no accessor
            specs[feature_name] = (
                feature,
                get_accessor_class(feature, feature_classes),
                get_value_ndim(feature_classes),
            )
        # metadata is a plain attribute, not a graphic feature, so add it explicitly
        specs["metadatas"] = ("metadata", CollectionFeatureAccessor, 0)
        cls._accessor_specs = specs

        # install a property for each feature, unless the class already defines one
        for feature_name, (feature, accessor_class, _) in cls._accessor_specs.items():
            if isinstance(getattr(cls, feature_name, None), property):
                continue
            setattr(cls, feature_name, make_feature_property(feature_name, accessor_class))

        # expose the feature names so `add_event_handler` routes feature events to the accessor
        cls._features = {**cls._features, **{name: spec[1] for name, spec in cls._accessor_specs.items()}}

        try:
            cls.__signature__ = make_collection_signature(cls._child_type, cls._accessor_specs)
        except (ValueError, TypeError):
            pass

    def __init__(self, data, name: str = None, metadata: Any = None, **kwargs):
        """
        Create a collection of graphics of the same type.

        Parameters
        ----------
        data: list of array-like
            one entry per graphic; its length is the number of graphics in the collection

        name: str, optional
            name of the collection

        metadata: Any, optional
            metadata attached to the collection

        **kwargs
            any feature of the child graphic (``colors``, ``thickness``, ``sizes``, ...), each
            accepting one value for all graphics or one value per graphic. Any argument that is not
            a feature is passed unchanged to every child graphic.
        """
        super().__init__(name=name, metadata=metadata)

        n_graphics = len(data)
        self._graphics = np.empty(n_graphics, dtype=object)
        self._set_world_object(pygfx.Group())

        self._create_accessors(data_value_ndim=int(np.ndim(data[0])))

        feature_values = dict()  # child feature -> iterator of one value per graphic
        graphic_kwargs = dict()  # non-feature kwargs, same for every graphic

        # split each feature into one value per graphic, other kwargs go to every graphic
        for feature_name, value in kwargs.items():
            if feature_name not in self._accessor_specs:
                graphic_kwargs[feature_name] = value
                continue
            feature = self._accessor_specs[feature_name][0]
            accessor = getattr(self, f"_{feature_name}")
            value = accessor._parse_feature_value(value, ())
            feature_values[feature] = iter(accessor._broadcast_over_graphics(value, n_graphics))

        # one graphic per data entry, filled into the preallocated array
        for i, graphic_data in enumerate(data):
            feature_kwargs = {feature: next(values) for feature, values in feature_values.items()}
            graphic = self._child_type(graphic_data, **feature_kwargs, **graphic_kwargs)
            self._check_graphic_features_modes(graphic)
            self._graphics[i] = graphic
            self.world_object.add(graphic.world_object)

    def _create_accessors(self, data_value_ndim: int):
        # one accessor per exposed feature, over the collection's graphics array
        for feature_name, (feature, accessor_class, value_ndim) in self._accessor_specs.items():
            setattr(
                self,
                f"_{feature_name}",
                accessor_class(self._graphics, feature, value_ndim, feature_name=feature_name),
            )
        # data is the loop driver, so its value_ndim comes from the data, not a feature class
        self._data._value_ndim = data_value_ndim

    @classmethod
    def _from_graphics(cls, graphics: np.ndarray, data_value_ndim: int) -> GraphicCollection:
        """a sub-collection over a subset of graphics, e.g. from slicing"""
        subcollection = cls.__new__(cls)
        subcollection._graphics = graphics
        subcollection._create_accessors(data_value_ndim=data_value_ndim)
        return subcollection

    @property
    def graphics(self) -> np.ndarray[Graphic]:
        """the graphics in the collection"""
        graphics = self._graphics.view()
        graphics.flags.writeable = False
        return graphics

    def add_graphic(self, graphic: Graphic):
        """
        Add a graphic to the collection.

        Parameters
        ----------
        graphic: Graphic
            the graphic to add; must be of the collection's ``_child_type`` and match the
            per-vertex or uniform buffer mode of the graphics already in the collection
        """
        if not isinstance(graphic, self._child_type):
            raise TypeError(
                f"cannot add a `{type(graphic).__name__}` to a collection of `{self._child_type.__name__}`"
            )
        self._check_graphic_features_modes(graphic)

        graphics = np.empty(self._graphics.size + 1, dtype=object)
        graphics[:-1] = self._graphics
        graphics[-1] = graphic
        self._graphics = graphics
        self._refresh_accessors()

        self.world_object.add(graphic.world_object)

    def remove_graphic(self, graphic: Graphic):
        """
        Remove a graphic from the collection.

        Parameters
        ----------
        graphic: Graphic
            the graphic to remove
        """
        index = next((i for i, g in enumerate(self._graphics) if g is graphic), None)
        if index is None:
            raise KeyError("graphic is not in the collection")

        self._graphics = np.delete(self._graphics, index)
        self._refresh_accessors()

        self.world_object.remove(graphic.world_object)

    def _check_graphic_features_modes(self, graphic: Graphic):
        # every graphic must use the same feature types (per-vertex vs uniform) as the first one,
        # so the accessors can index them all the same way
        if self._graphics.size == 0 or self._graphics[0] is None:
            return
        reference = self._graphics[0]
        for feature, _, _ in self._accessor_specs.values():
            reference_feature = getattr(reference, f"_{feature}", None)
            if not isinstance(reference_feature, GraphicFeature):
                continue  # e.g. metadata, not a graphic feature
            if not isinstance(getattr(graphic, f"_{feature}", None), type(reference_feature)):
                raise TypeError(
                    f"graphics in a collection must use the same `{feature}` type; the collection "
                    f"uses `{type(reference_feature).__name__}`"
                )

    def _refresh_accessors(self):
        # point each accessor at the current graphics array
        for feature_name in self._accessor_specs:
            getattr(self, f"_{feature_name}")._graphics = self._graphics

    def _fpl_add_plot_area_hook(self, plot_area):
        super()._fpl_add_plot_area_hook(plot_area)
        for graphic in self._graphics:
            graphic._fpl_add_plot_area_hook(plot_area)

    def _fpl_prepare_del(self):
        self.world_object._event_handlers.clear()
        self.world_object.clear()

        for graphic in self._graphics:
            graphic._fpl_prepare_del()

    def __getitem__(self, key) -> Graphic | GraphicCollection:
        if np.issubdtype(type(key), np.integer):
            return self._graphics[key]
        return self._from_graphics(self._graphics[key], self._data._value_ndim)

    def __len__(self) -> int:
        return self._graphics.size

    def __iter__(self):
        return iter(self._graphics)

    def __contains__(self, graphic: Graphic) -> bool:
        return graphic in self._graphics

    def __repr__(self) -> str:
        return f"{type(self).__name__} of <{len(self)}> {self._child_type.__name__}"
