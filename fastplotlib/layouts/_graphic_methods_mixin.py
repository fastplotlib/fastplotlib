from collections.abc import Callable
from inspect import Parameter, getdoc, signature

from ..graphics import (
    Graphic,
    ImageCollection,
    ImageGraphic,
    ImageGrid,
    ImageVolumeGraphic,
    ImageYUVGraphic,
    InfLineGraphic,
    LineCollection,
    LineGraphic,
    LineStack,
    MeshGraphic,
    PolygonGraphic,
    ScatterCollection,
    ScatterGraphic,
    ScatterStack,
    SurfaceGraphic,
    TextGraphic,
    VectorsGraphic,
)


def make_graphic_method(
    graphic_cls: type[Graphic], owner: type, name: str
) -> Callable[..., Graphic]:
    """the ``add_<graphic>`` method for a graphic class"""

    def add_graphic(self, *args, **kwargs) -> Graphic:
        return self._create_graphic(graphic_cls, *args, **kwargs)

    # the graphic's own signature, `self` included so that it is stripped again when bound
    sig = signature(graphic_cls)
    add_graphic.__signature__ = sig.replace(
        parameters=[
            Parameter("self", Parameter.POSITIONAL_ONLY),
            *sig.parameters.values(),
        ],
        return_annotation=graphic_cls,
    )

    # a collection's arguments come from the graphic it holds, and so does its documentation
    documented = getattr(graphic_cls, "_child_type", None) or graphic_cls
    add_graphic.__doc__ = getdoc(documented.__init__)
    add_graphic.__name__ = name
    add_graphic.__qualname__ = f"{owner.__qualname__}.{name}"

    return add_graphic


class GraphicMethod:
    """
    Descriptor for an ``add_<graphic>`` method.

    The method has the graphic constructor's signature and passes on only the arguments it was
    given, so an argument that is left out is filled in from the graphic's config.
    """

    def __init__(self, graphic_cls: type[Graphic]):
        self.graphic_cls = graphic_cls

    def __set_name__(self, owner: type, name: str):
        self._method = make_graphic_method(self.graphic_cls, owner, name)

    def __get__(self, instance, owner: type = None) -> Callable[..., Graphic]:
        # bind like a plain function: the function on class access, a bound method on an instance
        return self._method.__get__(instance, owner)


class GraphicMethodsMixin:
    # While we could have this directly in `PlotArea`, the reason it's in a separate module as a mixin
    # is because the .pyi file which provides function signatures for IDEs is a module-level feature
    # we cannot have a .pyi file for just a few method of a class in a module, which is why we don't have
    # a _plot_area.pyi. That would require redundantly re-generating for the entire PlotArea class.
    add_line = GraphicMethod(LineGraphic)
    add_inf_line = GraphicMethod(InfLineGraphic)

    add_line_collection = GraphicMethod(LineCollection)
    add_line_stack = GraphicMethod(LineStack)

    add_scatter = GraphicMethod(ScatterGraphic)

    add_scatter_collection = GraphicMethod(ScatterCollection)
    add_scatter_stack = GraphicMethod(ScatterStack)

    add_image = GraphicMethod(ImageGraphic)
    add_image_yuv = GraphicMethod(ImageYUVGraphic)
    add_image_volume = GraphicMethod(ImageVolumeGraphic)

    add_image_collection = GraphicMethod(ImageCollection)
    add_image_grid = GraphicMethod(ImageGrid)

    add_mesh = GraphicMethod(MeshGraphic)
    add_surface = GraphicMethod(SurfaceGraphic)
    add_polygon = GraphicMethod(PolygonGraphic)

    add_vectors = GraphicMethod(VectorsGraphic)

    add_text = GraphicMethod(TextGraphic)

    def _create_graphic(self, graphic_cls: type[Graphic], *args, **kwargs) -> Graphic:
        center = kwargs.pop("center", False)

        if "name" in kwargs:
            # check the name before creating the graphic
            self._check_graphic_name_exists(kwargs["name"])

        graphic = graphic_cls(*args, **kwargs)
        self.add_graphic(graphic, center=center)

        return graphic
