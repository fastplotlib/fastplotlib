import inspect
import pathlib

# if there is an existing mixin class, replace it with an empty class
# so that fastplotlib will import
# hacky but it works
current_module = pathlib.Path(__file__).parent.parent.resolve()
with open(current_module.joinpath('layouts/graphic_methods_mixin.py'), 'w') as f:
    f.write(
        f"class GraphicMethodsMixin:\n"
        f"    pass"
    )

from fastplotlib import graphics


modules = list()

for name, obj in inspect.getmembers(graphics):
    if inspect.isclass(obj):
        modules.append(obj)


def generate_add_graphics_methods():
    # clear file and regenerate from scratch

    f = open(current_module.joinpath('layouts/graphic_methods_mixin.py'), 'w')

    f.write('# This is an auto-generated file and should not be modified directly\n\n')

    f.write('from typing import *\n\n')
    f.write('import numpy\n')
    f.write('import weakref\n\n')
    f.write('from ..graphics import *\n')
    f.write('from ..graphics._base import Graphic\n\n')

    f.write("\nclass GraphicMethodsMixin:\n")
    f.write("    def __init__(self):\n")
    f.write("        pass\n\n")

    f.write("    def _create_graphic(self, graphic_class, *args, **kwargs) -> Graphic:\n")
    f.write("        if 'center' in kwargs.keys():\n")
    f.write("            center = kwargs.pop('center')\n")
    f.write("        else:\n")
    f.write("            center = False\n\n")
    f.write("        if 'name' in kwargs.keys():\n")
    f.write("            self._check_graphic_name_exists(kwargs['name'])\n\n")
    f.write("        graphic = graphic_class(*args, **kwargs)\n")
    f.write("        self.add_graphic(graphic, center=center)\n\n")
    f.write("        # only return a proxy to the real graphic\n")
    f.write("        return weakref.proxy(graphic)\n\n")

    for m in modules:
        class_name = m
        method_name = class_name.type

        class_args = inspect.getfullargspec(class_name)[0][1:]
        class_args = [arg + ', ' for arg in class_args]
        s = ""
        for a in class_args:
            s += a

        f.write(f"    def add_{method_name}{inspect.signature(class_name.__init__)} -> {class_name.__name__}:\n")
        f.write('        """\n')
        f.write(f'        {class_name.__init__.__doc__}\n')
        f.write('        """\n')
        f.write(f"        return self._create_graphic({class_name.__name__}, {s}*args, **kwargs)\n\n")

    f.close()


if __name__ == '__main__':
    generate_add_graphics_methods()
