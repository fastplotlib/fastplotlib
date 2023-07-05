from typing import *
import inspect
from pathlib import Path
import os

import fastplotlib
from fastplotlib.layouts._subplot import Subplot
from fastplotlib import graphics
from fastplotlib.graphics import _features

current_dir = Path(__file__).parent.resolve()

API_DIR = current_dir.joinpath("api")
LAYOUTS_DIR = API_DIR.joinpath("layouts")
GRAPHICS_DIR = API_DIR.joinpath("graphics")
GRAPHIC_FEATURES_DIR = API_DIR.joinpath("graphic_features")
SELECTORS_DIR = API_DIR.joinpath("selectors")
WIDGETS_DIR = API_DIR.joinpath("widgets")

doc_sources = [
    API_DIR,
    LAYOUTS_DIR,
    GRAPHICS_DIR,
    GRAPHIC_FEATURES_DIR,
    SELECTORS_DIR,
    WIDGETS_DIR
]

for source_dir in doc_sources:
    os.makedirs(source_dir, exist_ok=True)


def get_public_members(cls) -> Tuple[List[str], List[str]]:
    """
    Returns (public_methods, public_properties)

    Parameters
    ----------
    cls

    Returns
    -------

    """
    methods = list()
    properties = list()
    for member in inspect.getmembers(cls):
        # only document public methods
        if member[0].startswith("_"):
            continue

        if callable(member[1]):
            methods.append(member[0])
        elif isinstance(member[1], property):
            properties.append(member[0])

    return methods, properties


def generate_class(
    cls: type,
    module: str,
):
    name = cls.__name__
    methods, properties = get_public_members(cls)
    methods = [
        f"{name}.{m}" for m in methods
    ]

    properties = [
        f"{name}.{p}" for p in properties
    ]

    underline = "=" * len(name)

    methods_str = "\n    ".join([""] + methods)
    properties_str = "\n    ".join([""] + properties)

    out = (
        f"{underline}\n"
        f"{name}\n"
        f"{underline}\n"
        f".. currentmodule:: {module}\n"
        f"\n"
        f"Constructor\n"
        f"~~~~~~~~~~~\n"
        f".. autosummary::\n"
        f"    :toctree: {name}_api\n"
        f"\n"
        f"    {name}\n"
        f"\n"
        f"Properties\n"
        f"~~~~~~~~~~\n"
        f".. autosummary::\n"
        f"    :toctree: {name}_api\n"
        f"{properties_str}\n"
        f"\n"
        f"Methods\n"
        f"~~~~~~~\n"
        f".. autosummary::\n"
        f"    :toctree: {name}_api\n"
        f"{methods_str}\n"
        f"\n"
    )

    return out


def generate_page(
    page_name: str,
    modules: List[str],
    classes: List[type],
    source_path: Path,
):
    page_name_underline = "*" * len(page_name)
    with open(source_path, "w") as f:
        f.write(
            f".. _api.{page_name}:"
            f"\n"
            f"{page_name}\n"
            f"{page_name_underline}\n"
            f"\n"
        )

        for cls, module in zip(classes, modules):
            to_write = generate_class(cls, module)
            f.write(to_write)


def main():
    generate_page(
        page_name="Plot",
        classes=[fastplotlib.Plot],
        modules=["fastplotlib"],
        source_path=LAYOUTS_DIR.joinpath("plot.rst")
    )

    generate_page(
        page_name="GridPlot",
        classes=[fastplotlib.GridPlot, Subplot],
        modules=["fastplotlib", "fastplotlib.layouts._subplot"],
        source_path=LAYOUTS_DIR.joinpath("gridplot.rst")
    )

    graphic_classes = [
        getattr(graphics, g) for g in graphics.__all__
    ]

    graphic_class_names = [
        g.__name__ for g in graphic_classes
    ]

    graphic_class_names_str = "\n    ".join([""] + graphic_class_names)

    # graphic classes index file
    with open(GRAPHICS_DIR.joinpath("index.rst"), "w") as f:
        f.write(
            f"Graphics\n"
            f"********\n"
            f"\n"
            f".. toctree::\n"
            f"    :maxdepth: 1\n"
            f"{graphic_class_names_str}\n"
        )

    for graphic_cls in graphic_classes:
        generate_page(
            page_name=graphic_cls.__name__,
            classes=[graphic_cls],
            modules=["fastplotlib"],
            source_path=GRAPHICS_DIR.joinpath(f"{graphic_cls.__name__}.rst")
        )


if __name__ == "__main__":
    main()
