import inspect
import pathlib

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
            # skip base class
            continue
        modules.append(obj)


def generate_add_graphics_methods():
    # clear file and regenerate from scratch
    f = open(filename, "w", encoding="utf-8")

    f.write("# This is an auto-generated file and should not be modified directly\n\n")

    f.write("from typing import *\n\n")
    f.write("import numpy\n\n")
    f.write("from ..graphics import *\n")
    f.write("from ..graphics._base import Graphic\n\n")

    f.write("\nclass GraphicMethodsMixin:\n")

    f.write(
        "    def _create_graphic(self, graphic_class, *args, **kwargs) -> Graphic:\n"
    )
    f.write("        if 'center' in kwargs.keys():\n")
    f.write("            center = kwargs.pop('center')\n")
    f.write("        else:\n")
    f.write("            center = False\n\n")

    f.write("        if 'reference_space' in kwargs.keys():\n")
    f.write("            reference_space = kwargs.pop('reference_space')\n")
    f.write("        else:\n")
    f.write("            reference_space = 0\n\n")

    f.write("        if 'name' in kwargs.keys():\n")
    f.write("            self._check_graphic_name_exists(kwargs['name'])\n\n")
    f.write("        graphic = graphic_class(*args, **kwargs)\n")
    f.write("        self.add_graphic(graphic, center=center, reference_space=reference_space)\n\n")
    f.write("        return graphic\n\n")

    for m in modules:
        cls = m
        if cls.__name__ == "Graphic":
            # skip base class
            continue
        method_name = cls.type

        class_args = inspect.getfullargspec(cls)[0][1:]
        class_args = [arg + ", " for arg in class_args]
        s = ""
        for a in class_args:
            s += a

        f.write(
            f"    def add_{method_name}{inspect.signature(cls.__init__)} -> {cls.__name__}:\n"
        )
        f.write('        """\n')
        f.write(f"        {cls.__init__.__doc__}\n")
        f.write('        """\n')
        f.write(
            f"        return self._create_graphic({cls.__name__}, {s} **kwargs)\n\n"
        )

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
