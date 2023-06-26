import inspect
import sys
import pathlib

from fastplotlib.graphics import *


modules = list()

for name, obj in inspect.getmembers(sys.modules[__name__]):
    if inspect.isclass(obj):
        modules.append(obj)

def generate_add_graphics_methods():
    # clear file and regenerate from scratch
    current_module = pathlib.Path(__file__).parent.parent.resolve()

    open(current_module.joinpath('layouts/graphic_methods_mixin.py'), 'w').close()

    f = open(current_module.joinpath('layouts/graphic_methods_mixin.py'), 'w')

    f.write('from typing import *\n\n')
    f.write('import numpy\n')
    f.write('import weakref\n\n')
    f.write('from ..graphics import *\n\n')

    f.write("\nclass GraphicMethodsMixin:\n")
    f.write("    def __init__(self):\n")
    f.write("        pass\n\n")

    for m in modules:
        class_name = m
        method_name = class_name.type

        f.write(f"    def add_{method_name}{inspect.signature(class_name.__init__)} -> weakref.proxy({class_name.__name__}):\n")
        f.write('        """\n')
        f.write(f'        {class_name.__init__.__doc__}\n')
        f.write('        """\n')
        f.write(f"        g = {class_name.__name__}(*args, **kwargs)\n")
        f.write(f'        self.add_graphic(g)\n\n')

        f.write(f'        return weakref.proxy(g)\n\n')

    f.close()

    return


if __name__ == '__main__':
    generate_add_graphics_methods()

