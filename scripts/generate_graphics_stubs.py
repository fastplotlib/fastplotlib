import ast
import inspect
import pathlib
import textwrap

import black

import fastplotlib.graphics._collections as _collections_module
from fastplotlib.graphics._collection_base import _AccessorProperty
from fastplotlib.layouts._graphic_methods_mixin import GraphicMethod, GraphicMethodsMixin

root = pathlib.Path(__file__).parent.parent.resolve()
mixin_filename = root.joinpath("fastplotlib", "layouts", "_graphic_methods_mixin.pyi")
collections_filename = root.joinpath("fastplotlib", "graphics", "_collections.pyi")

HEADER = (
    "# This is an auto-generated file and should not be modified directly\n"
    "# regenerate with: python scripts/generate_graphics_stubs.py\n\n"
)

# {method name: graphic class}, the mixin defines which methods exist and what they are called
graphic_methods = {
    name: attr.graphic_cls
    for name, attr in vars(GraphicMethodsMixin).items()
    if isinstance(attr, GraphicMethod)
}

# the collection classes defined in `_collections.py`, in definition order (base classes first)
collection_classes = [
    obj
    for obj in vars(_collections_module).values()
    if inspect.isclass(obj) and obj.__module__ == _collections_module.__name__
]


def graphic_signature(cls: type) -> str:
    """
    the constructor arguments for a graphic or collection, as source text so the type aliases
    (``ColorLike``, ...) stay intact rather than expanding into their full unions.

    A collection takes the child graphic's arguments (via ast), plus the collection's own arguments
    (e.g. a stack's ``separation``) and the plural per-graphic arguments (``names``, ``offsets``, ...).
    """
    child = getattr(cls, "_child_type", None)
    if child is None:
        return ast.unparse(
            ast.parse(textwrap.dedent(inspect.getsource(cls.__init__))).body[0].args
        )

    init = ast.parse(textwrap.dedent(inspect.getsource(child.__init__))).body[0]
    args = init.args
    child_args = {a.arg for a in args.args} | {a.arg for a in args.kwonlyargs}

    own = ast.parse(textwrap.dedent(inspect.getsource(cls.__init__))).body[0].args
    # the collection's own arguments after `data`, e.g. `name`/`metadata` or `separation`; skip any
    # the child already takes, e.g. PositionsCollection re-declares `cmap`
    own_extra = own.args[2:]
    for a, default in zip(own_extra, own.defaults[len(own.defaults) - len(own_extra):]):
        if a.arg in child_args:
            continue
        args.kwonlyargs.append(a)
        args.kw_defaults.append(default)
    for a, default in zip(own.kwonlyargs, own.kw_defaults):
        if a.arg in child_args:
            continue
        args.kwonlyargs.append(a)
        args.kw_defaults.append(default)

    # the per-graphic (plural) features, e.g. `names`, `offsets`, `metadatas`; skip any the child or
    # the collection already takes (e.g. an ``ImageGrid`` takes ``offsets``)
    present = child_args | {a.arg for a in args.kwonlyargs}
    for feature_name in cls._accessor_specs:
        if feature_name not in present:
            args.kwonlyargs.append(ast.arg(arg=feature_name))
            args.kw_defaults.append(ast.Constant(value=None))

    return ast.unparse(args)


def docstring_body(doc: str | None) -> list[str]:
    """a stub function/method body: the docstring if there is one, else ``...``"""
    if doc is None:
        return ["        ..."]
    return ['        """', f"        {doc}", '        """']


def member_stub(name: str, member) -> list[str]:
    """stub lines for an explicitly-defined property or method of a collection class"""

    def function_stub(func, decorator: str = None) -> list[str]:
        node = ast.parse(textwrap.dedent(inspect.getsource(func))).body[0]
        returns = f" -> {ast.unparse(node.returns)}" if node.returns else ""
        lines = [f"    {decorator}"] if decorator else []
        lines.append(f"    def {name}({ast.unparse(node.args)}){returns}:")
        return lines + docstring_body(func.__doc__)

    if isinstance(member, property):
        lines = function_stub(member.fget, "@property")
        if member.fset is not None:
            lines += function_stub(member.fset, f"@{name}.setter")
        return lines
    return function_stub(member)


def param_doc(docstring: str, name: str) -> str | None:
    """the numpydoc description of parameter ``name`` in ``docstring``, if present"""
    if docstring is None:
        return None
    lines = docstring.splitlines()
    for i, line in enumerate(lines):
        if line.strip().startswith((f"{name}:", f"{name} :")):
            indent = len(line) - len(line.lstrip())
            description = []
            for cont in lines[i + 1:]:
                if not cont.strip() or len(cont) - len(cont.lstrip()) <= indent:
                    break
                description.append(cont.strip())
            return "\n".join(description) or None
    return None


def find_param(child_type: type, name: str) -> tuple[str, str | None]:
    """
    the annotation (as source text) and docstring of a child graphic's ``__init__`` parameter,
    searching the child's MRO so a collection's plural feature finds e.g. ``Graphic.offset``.
    """
    for klass in child_type.__mro__:
        init = klass.__dict__.get("__init__")
        if not inspect.isfunction(init):
            continue
        node = ast.parse(textwrap.dedent(inspect.getsource(init))).body[0]
        for arg in node.args.args + node.args.kwonlyargs:
            if arg.arg == name:
                annotation = ast.unparse(arg.annotation) if arg.annotation else "Any"
                return annotation, param_doc(init.__doc__, name)
    return "Any", None


def generate_mixin_stub():
    f = open(mixin_filename, "w", encoding="utf-8")
    f.write(HEADER)

    # star-import each module that defines a graphic, so every reference used in the graphics'
    # __init__ annotations (aliases, np, pygfx, typing, enums) is in scope
    referenced = set(graphic_methods.values())
    referenced |= {cls._child_type for cls in referenced if getattr(cls, "_child_type", None)}
    for module in sorted({cls.__module__ for cls in referenced}):
        f.write(f"from {module} import *\n")

    f.write("\n\nclass GraphicMethodsMixin:\n")

    for method_name, cls in graphic_methods.items():
        docstring = (getattr(cls, "_child_type", None) or cls).__init__.__doc__
        f.write(f"    def {method_name}({graphic_signature(cls)}) -> {cls.__name__}:\n")
        f.write("\n".join(docstring_body(docstring)) + "\n\n")

    f.close()


def generate_collections_stub():
    f = open(collections_filename, "w", encoding="utf-8")
    f.write(HEADER)

    # the child graphic modules bring the annotation aliases (ColorLike, np, Literal, ...) into scope
    f.write("from fastplotlib.graphics.line import *\n")
    f.write("from fastplotlib.graphics.scatter import *\n")
    f.write("from fastplotlib.graphics.image import *\n")
    f.write("from fastplotlib.graphics._collection_base import GraphicCollection\n")
    # only the accessor classes the collections actually expose
    accessor_classes = sorted(
        {
            accessor_cls.__name__
            for cls in collection_classes
            if "_child_type" in cls.__dict__
            for _, accessor_cls, _ in cls._accessor_specs.values()
        }
    )
    f.write(f"from fastplotlib.graphics._jagged_array import {', '.join(accessor_classes)}\n")
    f.write(
        "from fastplotlib.graphics.selectors import "
        "LinearSelector, LinearRegionSelector, RectangleSelector, PolygonSelector\n"
    )

    constructors = set(graphic_methods.values())

    for cls in collection_classes:
        bases = ", ".join(base.__name__ for base in cls.__bases__ if base is not object)
        body = []

        # the constructor for the concrete collection classes, docstring from the child graphic
        if cls in constructors:
            # graphic_signature already includes `self` (it is the child __init__'s first arg)
            body.append(f"    def __init__({graphic_signature(cls)}) -> None:")
            doc = cls._child_type.__init__.__doc__
            # a collection may append collection-specific notes, e.g. how cmap works across graphics;
            # authored at column 0 like the child docstring, black re-indents both together
            note = getattr(cls, "_stub_constructor_notes", None)
            if note is not None:
                doc = f"{doc.rstrip()}\n\n{note}"
            body += docstring_body(doc)

        # the per-graphic feature accessors, on the classes that set the child type: a property whose
        # getter returns the feature's accessor (indexable) and whose setter takes the feature's value
        # (one for all graphics, or one per graphic), with the docstring from the child constructor
        if "_child_type" in cls.__dict__:
            for feature_name, (child_feature, accessor_cls, _) in cls._accessor_specs.items():
                annotation, doc = find_param(cls._child_type, child_feature)
                value = "Any" if annotation == "Any" else f"{annotation} | Iterable[{annotation}]"
                body.append("    @property")
                body.append(f"    def {feature_name}(self) -> {accessor_cls.__name__}:")
                if doc is None:
                    body.append("        ...")
                else:
                    # indent every line so a multi-line param description stays aligned
                    body += ['        """', *(f"        {line}" for line in doc.splitlines()), '        """']
                body.append(f"    @{feature_name}.setter")
                body.append(f"    def {feature_name}(self, value: {value}) -> None: ...")

        # explicitly-defined public members, e.g. the cmap and selectors of PositionsCollection or
        # the separation of GraphicStack, ast-copied so their annotations and docstrings are kept
        for member_name, member in vars(cls).items():
            if member_name.startswith("_") or isinstance(member, _AccessorProperty):
                continue
            if isinstance(member, property) or inspect.isfunction(member):
                body += member_stub(member_name, member)

        f.write(f"\n\nclass {cls.__name__}({bases}):\n" if bases else f"\n\nclass {cls.__name__}:\n")
        f.write("\n".join(body) if body else "    ...")
        f.write("\n")

    f.close()


def blacken(filename):
    with open(filename, "r", encoding="utf-8") as f:
        text = f.read()

    text = black.format_str(text, mode=black.FileMode(is_pyi=True))

    with open(filename, "w", encoding="utf-8") as f:
        f.write(text)


if __name__ == "__main__":
    generate_mixin_stub()
    blacken(mixin_filename)
    generate_collections_stub()
    blacken(collections_filename)
