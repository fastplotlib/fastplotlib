import inspect
import sys
from fastplotlib.graphics import *
modules = list()

for name, obj in inspect.getmembers(sys.modules[__name__]):
    if inspect.isclass(obj):
        modules.append(obj)

def generate_add_graphics_methods():
    # clear file and regenerate from scratch
    open('_add_graphic_mixin.py', 'w').close()

    f = open('_add_graphic_mixin.py', 'w')

    f.write('from typing import *\n')
    f.write('import numpy\n')
    f.write('from ..graphics import *\n')
    f.write('import weakref\n\n')

    f.write("\nclass GraphicMethodsMixin:\n")
    f.write("\tdef __init__(self):\n")
    f.write("\t\tpass\n\n")

    for m in modules:
        class_name = m
        method_name = class_name.type

        f.write(f"\tdef add_{method_name}{inspect.signature(class_name.__init__)} -> weakref.proxy({class_name.__name__}):\n")
        f.write('\t\t"""\n')
        f.write(f'\t{class_name.__init__.__doc__}\n')
        f.write('\t\t"""\n')
        f.write(f"\t\tg = {class_name.__name__}(*args, **kwargs)\n")
        f.write(f'\t\tself.add_graphic(g)\n\n')

        f.write(f'\t\treturn weakref.proxy(g)\n\n')

    f.close()

    return


if __name__ == '__main__':
    generate_add_graphics_methods()
