import ast
import inspect
import pathlib
import textwrap

import black

from fastplotlib.layouts._graphic_methods_mixin import GraphicMethod, GraphicMethodsMixin

root = pathlib.Path(__file__).parent.parent.resolve()
filename = root.joinpath("fastplotlib", "layouts", "_graphic_methods_mixin.pyi")

# {method name: graphic class}, the mixin defines which methods exist and what they are called
graphic_methods = {
    name: attr.graphic_cls
    for name, attr in vars(GraphicMethodsMixin).items()
    if isinstance(attr, GraphicMethod)
}


def generate_stub():
    # clear file and regenerate from scratch
    f = open(filename, "w", encoding="utf-8")

    f.write(
        "# This is an auto-generated file and should not be modified directly\n"
        "# regenerate with: python scripts/generate_add_graphics_stub.py\n\n"
    )

    # star-import each module that defines a graphic, so every reference used in the
    # graphics' __init__ annotations (aliases, np, pygfx, typing, enums) is in scope
    referenced = set(graphic_methods.values())
    referenced |= {
        cls._child_type for cls in referenced if getattr(cls, "_child_type", None)
    }
    for module in sorted({cls.__module__ for cls in referenced}):
        f.write(f"from {module} import *\n")

    f.write("\n\nclass GraphicMethodsMixin:\n")

    for method_name, cls in graphic_methods.items():
        child = getattr(cls, "_child_type", None)
        if child is not None:
            # a graphic collection: take the arguments and docstring from the child graphic's
            # __init__ (via ast, so the type aliases stay intact), then add the collection's own
            # arguments (e.g. a stack's `separation`) and the plural per-graphic arguments
            init = ast.parse(textwrap.dedent(inspect.getsource(child.__init__))).body[0]
            args = init.args
            child_args = {a.arg for a in args.args} | {a.arg for a in args.kwonlyargs}

            own = ast.parse(textwrap.dedent(inspect.getsource(cls.__init__))).body[0].args
            # the collection's own arguments after `data`, e.g. `name`/`metadata` or `separation`;
            # skip any the child already takes, e.g. PositionsCollection re-declares `cmap`
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

            # the per-graphic (plural) features, e.g. `names`, `offsets`, `metadatas`; skip any the
            # child or the collection already takes (e.g. an ``ImageGrid`` takes ``offsets``)
            present = child_args | {a.arg for a in args.kwonlyargs}
            for feature_name in cls._accessor_specs:
                if feature_name not in present:
                    args.kwonlyargs.append(ast.arg(arg=feature_name))
                    args.kw_defaults.append(ast.Constant(value=None))

            signature = ast.unparse(args)
            docstring = child.__init__.__doc__
        else:
            init = ast.parse(textwrap.dedent(inspect.getsource(cls.__init__))).body[0]
            signature = ast.unparse(init.args)
            docstring = cls.__init__.__doc__

        f.write(f"    def {method_name}({signature}) -> {cls.__name__}:\n")
        f.write('        """\n')
        f.write(f"        {docstring}\n")
        f.write('        """\n\n')

    f.close()


def blacken():
    with open(filename, "r", encoding="utf-8") as f:
        text = f.read()

    mode = black.FileMode(line_length=88, is_pyi=True)
    text = black.format_str(text, mode=mode)

    with open(filename, "w", encoding="utf-8") as f:
        f.write(text)


if __name__ == "__main__":
    generate_stub()
    blacken()
