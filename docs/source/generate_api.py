from typing import *
import inspect
from pathlib import Path
import os

import fastplotlib
from fastplotlib.layouts._subplot import Subplot
from fastplotlib import graphics
from fastplotlib.graphics import _features, selectors
from fastplotlib import widgets
from fastplotlib import utils
from fastplotlib import ui


current_dir = Path(__file__).parent.resolve()

API_DIR = current_dir.joinpath("api")
LAYOUTS_DIR = API_DIR.joinpath("layouts")
GRAPHICS_DIR = API_DIR.joinpath("graphics")
GRAPHIC_FEATURES_DIR = API_DIR.joinpath("graphic_features")
SELECTORS_DIR = API_DIR.joinpath("selectors")
WIDGETS_DIR = API_DIR.joinpath("widgets")
UI_DIR = API_DIR.joinpath("ui")

doc_sources = [
    API_DIR,
    LAYOUTS_DIR,
    GRAPHICS_DIR,
    GRAPHIC_FEATURES_DIR,
    SELECTORS_DIR,
    WIDGETS_DIR,
    UI_DIR,
]

for source_dir in doc_sources:
    os.makedirs(source_dir, exist_ok=True)


# this way we can just add the entire api dir to gitignore and generate before pushing
with open(API_DIR.joinpath("fastplotlib.rst"), "w") as f:
    f.write(
        "fastplotlib\n"
        "***********\n\n"
        ".. currentmodule:: fastplotlib\n\n"

        ".. autofunction:: fastplotlib.pause_events\n\n"
        
        ".. autofunction:: fastplotlib.enumerate_adapters\n\n"
        
        ".. autofunction:: fastplotlib.select_adapter\n\n"
        
        ".. autofunction:: fastplotlib.print_wgpu_report\n\n"
        
        ".. autofunction:: fastplotlib.run\n"
    )

with open(API_DIR.joinpath("utils.rst"), "w") as f:
    f.write(
        "fastplotlib.utils\n"
        "*****************\n\n"
        
        "..currentmodule:: fastplotlib.utils\n"
        "..automodule:: fastplotlib.utils.functions\n"
        "    : members:\n"
    )


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
    methods = [f"{name}.{m}" for m in methods]

    properties = [f"{name}.{p}" for p in properties]

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


def generate_functions_module(module, name: str):
    underline = "*" * len(name)
    out = (
        f"{name}\n"
        f"{underline}\n"
        f"\n"
        f".. currentmodule:: {name}\n"
        f".. automodule:: {module.__name__}\n"
        f"    :members:\n"
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
            f".. _api.{page_name}:\n"
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
        page_name="Figure",
        classes=[fastplotlib.layouts._figure.Figure],
        modules=["fastplotlib.layouts"],
        source_path=LAYOUTS_DIR.joinpath("figure.rst"),
    )

    generate_page(
        page_name="ImguiFigure",
        classes=[fastplotlib.layouts.ImguiFigure],
        modules=["fastplotlib.layouts"],
        source_path=LAYOUTS_DIR.joinpath("imgui_figure.rst"),
    )

    generate_page(
        page_name="Subplot",
        classes=[Subplot],
        modules=["fastplotlib.layouts._subplot"],
        source_path=LAYOUTS_DIR.joinpath("subplot.rst"),
    )

    # layouts classes index file
    with open(LAYOUTS_DIR.joinpath("index.rst"), "w") as f:
        f.write(
            f"Layouts\n"
            f"********\n"
            f"\n"
            f".. toctree::\n"
            f"    :maxdepth: 1\n"
            f"\n"
            f"    imgui_figure\n"
            f"    figure\n"
            f"    subplot\n"
        )

    # the rest of this is a mess and can be refactored later

    graphic_classes = [getattr(graphics, g) for g in graphics.__all__]

    graphic_class_names = [g.__name__ for g in graphic_classes]

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
            source_path=GRAPHICS_DIR.joinpath(f"{graphic_cls.__name__}.rst"),
        )
    ##############################################################################

    feature_classes = [getattr(_features, f) for f in _features.__all__]

    feature_class_names = [f.__name__ for f in feature_classes]

    feature_class_names_str = "\n    ".join([""] + feature_class_names)

    with open(GRAPHIC_FEATURES_DIR.joinpath("index.rst"), "w") as f:
        f.write(
            f"Graphic Features\n"
            f"****************\n"
            f"\n"
            f".. toctree::\n"
            f"    :maxdepth: 1\n"
            f"{feature_class_names_str}\n"
        )

    for feature_cls in feature_classes:
        generate_page(
            page_name=feature_cls.__name__,
            classes=[feature_cls],
            modules=["fastplotlib.graphics._features"],
            source_path=GRAPHIC_FEATURES_DIR.joinpath(f"{feature_cls.__name__}.rst"),
        )
    ##############################################################################

    selector_classes = [getattr(selectors, s) for s in selectors.__all__]

    selector_class_names = [s.__name__ for s in selector_classes]

    selector_class_names_str = "\n    ".join([""] + selector_class_names)

    with open(SELECTORS_DIR.joinpath("index.rst"), "w") as f:
        f.write(
            f"Selectors\n"
            f"*********\n"
            f"\n"
            f".. toctree::\n"
            f"    :maxdepth: 1\n"
            f"{selector_class_names_str}\n"
        )

    for selector_cls in selector_classes:
        generate_page(
            page_name=selector_cls.__name__,
            classes=[selector_cls],
            modules=["fastplotlib"],
            source_path=SELECTORS_DIR.joinpath(f"{selector_cls.__name__}.rst"),
        )
    ##############################################################################

    widget_classes = [getattr(widgets, w) for w in widgets.__all__]

    widget_class_names = [w.__name__ for w in widget_classes]

    widget_class_names_str = "\n    ".join([""] + widget_class_names)

    with open(WIDGETS_DIR.joinpath("index.rst"), "w") as f:
        f.write(
            f"Widgets\n"
            f"*******\n"
            f"\n"
            f".. toctree::\n"
            f"    :maxdepth: 1\n"
            f"{widget_class_names_str}\n"
        )

    for widget_cls in widget_classes:
        generate_page(
            page_name=widget_cls.__name__,
            classes=[widget_cls],
            modules=["fastplotlib"],
            source_path=WIDGETS_DIR.joinpath(f"{widget_cls.__name__}.rst"),
        )
    ##############################################################################

    ui_classes = [ui.BaseGUI, ui.Window, ui.EdgeWindow, ui.Popup]

    ui_class_names = [cls.__name__ for cls in ui_classes]

    ui_class_names_str = "\n    ".join([""] + ui_class_names)

    with open(UI_DIR.joinpath("index.rst"), "w") as f:
        f.write(
            f"UI Bases\n"
            f"********\n"
            f"\n"
            f".. toctree::\n"
            f"    :maxdepth: 1\n"
            f"{ui_class_names_str}\n"
        )

    for ui_cls in ui_classes:
        generate_page(
            page_name=ui_cls.__name__,
            classes=[ui_cls],
            modules=["fastplotlib.ui"],
            source_path=UI_DIR.joinpath(f"{ui_cls.__name__}.rst"),
        )

    ##############################################################################

    utils_str = generate_functions_module(utils.functions, "fastplotlib.utils")

    with open(API_DIR.joinpath("utils.rst"), "w") as f:
        f.write(utils_str)

    # nake API index file
    with open(API_DIR.joinpath("index.rst"), "w") as f:
        f.write(
            "API Reference\n"
            "*************\n\n"
            ".. toctree::\n"
            "    :caption: API Reference\n"
            "    :maxdepth: 2\n\n"
            "    layouts/index\n"
            "    graphics/index\n"
            "    graphic_features/index\n"
            "    selectors/index\n"
            "    ui/index\n"
            "    widgets/index\n"
            "    fastplotlib\n"
            "    utils\n"
        )

if __name__ == "__main__":
    main()
