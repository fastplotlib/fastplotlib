import ast
import inspect
import pathlib
import re
import textwrap

import black

root = pathlib.Path(__file__).parent.parent.resolve()
filename = root.joinpath("fastplotlib", "layouts", "_graphic_methods_mixin.py")

# if there is an existing mixin class, replace it with an empty class
# so that fastplotlib will import
# hacky but it works
with open(filename, "w") as f:
    f.write(f"class GraphicMethodsMixin:\n" f"    pass")

from fastplotlib import graphics


modules = list()

for name, obj in inspect.getmembers(graphics):
    if inspect.isclass(obj):
        if obj.__name__ == "Graphic":
            continue  # skip the base class
        modules.append(obj)


def generate_add_graphics_methods():
    # clear file and regenerate from scratch
    f = open(filename, "w", encoding="utf-8")

    f.write("# This is an auto-generated file and should not be modified directly\n\n")

    # star-import each module that defines a graphic, so every reference used in the
    # graphics' __init__ annotations (aliases, np, pygfx, typing, enums) is in scope
    for module in sorted({cls.__module__ for cls in modules}):
        f.write(f"from {module} import *\n")

    f.write("from fastplotlib.graphics import Graphic\n\n")

    f.write("\nclass GraphicMethodsMixin:\n")

    f.write(
        "    def _create_graphic(self, graphic_class, *args, **kwargs) -> Graphic:\n"
    )
    f.write("        if 'center' in kwargs.keys():\n")
    f.write("            center = kwargs.pop('center')\n")
    f.write("        else:\n")
    f.write("            center = False\n\n")
    f.write("        # ignore arguments left at their default of None, i.e. not passed by the caller\n")
    f.write("        kwargs = {k: v for k, v in kwargs.items() if v is not None}\n\n")
    f.write("        if 'name' in kwargs.keys():\n")
    f.write("            self._check_graphic_name_exists(kwargs['name'])\n\n")
    f.write("        graphic = graphic_class(*args, **kwargs)\n")
    f.write("        self.add_graphic(graphic, center=center)\n\n")
    f.write("        return graphic\n\n")

    # from https://stackoverflow.com/a/1176023
    camel_to_snake = re.compile(r"(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")

    for m in modules:
        cls = m
        cls_name = cls.__name__.replace("Graphic", "")

        method_name = camel_to_snake.sub("_", cls_name).lower()

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

            # pass `data` positionally and everything else by keyword, since the collection takes
            # its features as **kwargs
            passed = ["data"]
            passed += [f"{a.arg}={a.arg}" for a in args.args if a.arg not in ("self", "data")]
            passed += [f"{a.arg}={a.arg}" for a in args.kwonlyargs]
            if args.kwarg is not None:
                passed.append(f"**{args.kwarg.arg}")
            call = ", ".join(passed)
        else:
            init = ast.parse(textwrap.dedent(inspect.getsource(cls.__init__))).body[0]
            signature = ast.unparse(init.args)
            docstring = cls.__init__.__doc__
            class_args = inspect.getfullargspec(cls)[0][1:]
            call = "".join(a + ", " for a in class_args) + "**kwargs"

        f.write(f"    def add_{method_name}({signature}) -> {cls.__name__}:\n")
        f.write('        """\n')
        f.write(f"        {docstring}\n")
        f.write('        """\n')
        f.write(f"        return self._create_graphic({cls.__name__}, {call})\n\n")

    f.close()


def blacken():
    with open(filename, "r", encoding="utf-8") as f:
        text = f.read()

    mode = black.FileMode(line_length=88)
    text = black.format_str(text, mode=mode)

    with open(filename, "w", encoding="utf-8") as f:
        f.write(text)


if __name__ == "__main__":
    generate_add_graphics_methods()
    blacken()
