from collections import defaultdict
import inspect
from io import StringIO
import os
from pathlib import Path
from typing import *

import fastplotlib
from fastplotlib.layouts import Subplot
from fastplotlib import graphics
from fastplotlib.graphics import features, selectors
from fastplotlib import tools
from fastplotlib import widgets
from fastplotlib import utils
from fastplotlib import ui


current_dir = Path(__file__).parent.resolve()

API_DIR = current_dir.joinpath("api")
LAYOUTS_DIR = API_DIR.joinpath("layouts")
GRAPHICS_DIR = API_DIR.joinpath("graphics")
GRAPHIC_FEATURES_DIR = API_DIR.joinpath("graphic_features")
SELECTORS_DIR = API_DIR.joinpath("selectors")
TOOLS_DIR = API_DIR.joinpath("tools")
WIDGETS_DIR = API_DIR.joinpath("widgets")
UI_DIR = API_DIR.joinpath("ui")
GUIDE_DIR = current_dir.joinpath("user_guide")

doc_sources = [
    API_DIR,
    LAYOUTS_DIR,
    GRAPHICS_DIR,
    GRAPHIC_FEATURES_DIR,
    SELECTORS_DIR,
    TOOLS_DIR,
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
        
        "fastplotlib.loop\n"
        "------------------\n"
        "See the rendercanvas docs: https://rendercanvas.readthedocs.io/stable/api.html#rendercanvas.BaseLoop "
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


def generate_functions_module(module, name: str, generate_header: bool = True):
    underline = "*" * len(name)
    if generate_header:
        header = (
            f"{name}\n"
            f"{underline}\n"
            f"\n"
        )
    else:
        header = "\n"
    out = (
        f"{header}"
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

#######################################################
# Used for GraphicFeature class event table
# copy-pasted from https://pablofernandez.tech/2019/03/21/turning-a-list-of-dicts-into-a-restructured-text-table/

def _generate_header(field_names, column_widths):
    with StringIO() as output:
        for field_name in field_names:
            output.write(f"+-{'-' * column_widths[field_name]}-")
        output.write("+\n")
        for field_name in field_names:
            output.write(f"| {field_name} {' ' * (column_widths[field_name] - len(field_name))}")
        output.write("|\n")
        for field_name in field_names:
            output.write(f"+={'=' * column_widths[field_name]}=")
        output.write("+\n")
        return output.getvalue()


def _generate_row(row, field_names, column_widths):
    with StringIO() as output:
        for field_name in field_names:
            output.write(f"| {row[field_name]}{' ' * (column_widths[field_name] - len(str(row[field_name])))} ")
        output.write("|\n")
        for field_name in field_names:
            output.write(f"+-{'-' * column_widths[field_name]}-")
        output.write("+\n")
        return output.getvalue()


def _get_fields(data):
    field_names = []
    column_widths = defaultdict(lambda: 0)
    for row in data:
        for field_name in row:
            if field_name not in field_names:
                field_names.append(field_name)
            column_widths[field_name] = max(column_widths[field_name], len(field_name), len(str(row[field_name])))
    return field_names, column_widths


def dict_to_rst_table(data):
    """convert a list of dicts to an RST table"""
    field_names, column_widths = _get_fields(data)
    with StringIO() as output:
        output.write(_generate_header(field_names, column_widths))
        for row in data:
            output.write(_generate_row(row, field_names, column_widths))

        output.write("\n")

        return output.getvalue()

#######################################################


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
    ##############################################################################
    # ** Graphic classes ** #
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
    # ** GraphicFeature classes ** #
    feature_classes = [getattr(features, f) for f in features.__all__]

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
            modules=["fastplotlib.graphics.features"],
            source_path=GRAPHIC_FEATURES_DIR.joinpath(f"{feature_cls.__name__}.rst"),
        )
    ##############################################################################
    # ** Selector classes ** #
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
    # ** Tools classes ** #
    tools_classes = [getattr(tools, t) for t in tools.__all__]

    tools_class_names = [t.__name__ for t in tools_classes]

    tools_class_names_str = "\n    ".join([""] + tools_class_names)

    with open(TOOLS_DIR.joinpath("index.rst"), "w") as f:
        f.write(
            f"Tools\n"
            f"*****\n"
            f"\n"
            f".. toctree::\n"
            f"    :maxdepth: 1\n"
            f"{tools_class_names_str}\n"
        )

    for tool_cls in tools_classes:
        generate_page(
            page_name=tool_cls.__name__,
            classes=[tool_cls],
            modules=["fastplotlib"],
            source_path=TOOLS_DIR.joinpath(f"{tool_cls.__name__}.rst"),
        )

    ##############################################################################
    # ** Widget classes ** #
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
    # ** UI classes ** #
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
    utils_str += generate_functions_module(utils._plot_helpers, "fastplotlib.utils", generate_header=False)

    with open(API_DIR.joinpath("utils.rst"), "w") as f:
        f.write(utils_str)

    # make API index file
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

    ##############################################################################
    # graphic feature event tables

    def write_table(name, feature_cls):
        s = f"{name}\n"
        s += "^" * len(name) + "\n\n"

        if hasattr(feature_cls, "event_extra_attrs"):
            s += "**extra attributes**\n\n"
            s += dict_to_rst_table(feature_cls.event_extra_attrs)

        s += "**event info dict**\n\n"
        s += dict_to_rst_table(feature_cls.event_info_spec)

        return s

    with open(GUIDE_DIR.joinpath("event_tables.rst"), "w") as f:
        f.write(".. _event_tables:\n\n")
        f.write("Event Tables\n")
        f.write("============\n\n")

        for graphic_cls in [*graphic_classes, *selector_classes]:
            if graphic_cls is graphics.Graphic:
                # skip Graphic base class
                continue
            f.write(f"{graphic_cls.__name__}\n")
            f.write("-" * len(graphic_cls.__name__) + "\n\n")
            for name, type_ in graphic_cls._features.items():
                if isinstance(type_, tuple):
                    for t in type_:
                        if t is None:
                            continue
                        f.write(write_table(name, t))
                else:
                    f.write(write_table(name, type_))


if __name__ == "__main__":
    main()
