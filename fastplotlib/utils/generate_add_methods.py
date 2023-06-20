import inspect
import fastplotlib
from fastplotlib.graphics import *
import sys

modules = dict(inspect.getmembers(fastplotlib.graphics))['__all__']


def generate_add_graphics_methods():
    # clear file and regenerate from scratch
    open('add_graphics.py', 'w').close()

    sys.stdout = open('add_graphics.py', 'w')

    print('from typing import *\n')
    print('import numpy\n')
    print('from fastplotlib.graphics import *\n')

    print("\nclass GraphicMethods:")
    print("\tdef __init__(self):")
    print("\t\tpass\n")

    for m in modules:
        class_name = getattr(sys.modules[__name__], m)
        method_name = class_name.type

        print(f"\tdef add_{method_name}{inspect.signature(class_name.__init__)}:")
        print('\t\t"""')
        print(f'\t{class_name.__init__.__doc__}')
        print('\t\t"""')
        print(f"\t\tg = {class_name.__name__}(*args, **kwargs)")
        print(f'\t\tself.add_graphic(g)\n')

    sys.stdout.close()


if __name__ == '__main__':
    generate_add_graphics_methods()
