# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os

# need to force offscreen rendering before importing fpl
# otherwise fpl tries to select glfw canvas
os.environ["WGPU_FORCE_OFFSCREEN"] = "1"

import fastplotlib
from pygfx.utils.gallery_scraper import find_examples_for_gallery
from pathlib import Path
import sys
from sphinx_gallery.sorting import ExplicitOrder
import imageio.v3 as iio


ROOT_DIR = Path(__file__).parents[1].parents[0]  # repo root
EXAMPLES_DIR = Path.joinpath(ROOT_DIR, "examples")

sys.path.insert(0, str(ROOT_DIR))

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "fastplotlib"
copyright = "2022-2026, Kushal Kolar, Caitlin Lewis"
author = "Kushal Kolar, Caitlin Lewis"
release = fastplotlib.__version__

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.napoleon",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "sphinx_copybutton",
    "sphinx_design",
    "sphinx_gallery.gen_gallery",
]

# note this is largely copied from the pygfx PR branch: https://github.com/pygfx/pygfx/pull/1273
# -- Build wheel so Pyodide examples can use exactly this version of fpl -----------------------------------------------------
import subprocess
import shutil

short_version = ".".join(str(i) for i in fastplotlib.version_info[:3])
wheel_name = f"fastplotlib-{short_version}-py3-none-any.whl"

# Build the wheel
subprocess.run([sys.executable, "-m", "build", "-nw"], cwd=ROOT_DIR)
wheel_filename = os.path.join(ROOT_DIR, "dist", wheel_name)
assert os.path.isfile(wheel_filename), f"{wheel_name} does not exist"

# Copy into static
# TODO: you can use --outdir on the build command directly. also use the html_static_path in this namespace
print("Copy wheel to _static dir")
shutil.copy(
    wheel_filename,
    os.path.join(ROOT_DIR, "docs", "source", "_static", wheel_name),
)

# -- Sphix Gallery -----------------------------------------------------

## pyodide demos, adapted from wgpu, adapted from rendercanvas... might make sense to put this in the scaper?
iframe_placeholder_rst = """
.. only:: html

    Interactive example
    -------------------

    Try this example in your browser using Pyodide. Might not work with all examples and all devices. Check the output and your browser's console for details.

    .. raw:: html

        <iframe src="./../pyodide.html#example.py"></iframe>
"""
python_files = {}

# I have a feeling this import might be really sketchy to have on CI... but hey - this is a hack for a hack
from examples.server_browser_examples import patch_imageio_for_pyodide


def add_pyodide_to_examples(app):
    if app.builder.name != "html":
        return

    gallery_dir = ROOT_DIR / "docs" / "source" / "_gallery"
    example_files = gallery_dir.glob("**/*.py")

    for py_file in example_files:
        fname = py_file.name
        with open(py_file, "rb") as f:
            py = f.read().decode()
            py = patch_imageio_for_pyodide(py)
        if fname:
            print("Adding Pyodide example to", fname)
            fname_rst = py_file.with_suffix(".rst")
            # Update rst file
            rst = iframe_placeholder_rst.replace("example.py", fname)
            # we likely don't want append here?
            with open(fname_rst, "ab") as f:
                # TODO: skip if it already ends with the placeholder? otherwise the append will keep on appending (we have to hook this into the gen_rst to skip if possible?)
                f.write(rst.encode())
            python_files[py_file.relative_to(gallery_dir)] = py

def add_files_to_run_pyodide_examples(app, exception):
    if app.builder.name != "html":
        return

    gallery_build_dir = os.path.join(app.outdir, "_gallery")

    # Write html file that can load pyodide examples
    with open(
        os.path.join(ROOT_DIR, "docs", "source", "_static", "_pyodide_iframe.html"), "rb"
    ) as f:
        html = f.read().decode()
    html = html.replace('"fastplotlib"', f'"../_static/{wheel_name}"')
    with open(os.path.join(gallery_build_dir, "pyodide.html"), "wb") as f:
        f.write(html.encode())

    # Write the python files
    for fname, py in python_files.items():
        print("Writing", fname)
        with open(os.path.join(gallery_build_dir, fname), "wb") as f:
            f.write(py.encode())



sphinx_gallery_conf = {
    "gallery_dirs": "_gallery",
    "notebook_extensions": {},  # remove the download notebook button
    "backreferences_dir": "_gallery/backreferences",
    "doc_module": ("fastplotlib",),
    "image_scrapers": ("pygfx",),
    "remove_config_comments": True,
    "subsection_order": ExplicitOrder(
        [
            "../../examples/image",
            "../../examples/image_volume",
            "../../examples/heatmap",
            "../../examples/image_widget",
            "../../examples/gridplot",
            "../../examples/window_layouts",
            "../../examples/controllers",
            "../../examples/line",
            "../../examples/line_collection",
            "../../examples/mesh",
            "../../examples/scatter",
            "../../examples/vectors",
            "../../examples/text",
            "../../examples/events",
            "../../examples/selection_tools",
            "../../examples/spaces_transforms",
            "../../examples/machine_learning",
            "../../examples/guis",
            "../../examples/ipywidgets",
            "../../examples/misc",
            "../../examples/qt",
        ]
    ),
    "ignore_pattern": r"__init__\.py",
    "nested_sections": False,
    "thumbnail_size": (250, 250),
}

extra_conf = find_examples_for_gallery(EXAMPLES_DIR)
sphinx_gallery_conf.update(extra_conf)

# download imageio examples for the gallery
iio.imread("imageio:clock.png")
iio.imread("imageio:astronaut.png")
iio.imread("imageio:coffee.png")
iio.imread("imageio:hubble_deep_field.png")

autosummary_generate = True

templates_path = ["_templates"]
exclude_patterns = []

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "pydata_sphinx_theme"

html_theme_options = {
    "navbar_end": ["theme-switcher", "version-switcher", "navbar-icon-links"],
    "show_version_warning_banner": True,
    "check_switcher": True,
    "switcher": {
        "json_url": "http://www.fastplotlib.org/_static/switcher.json",
        "version_match": release,
    },
    "icon_links": [
        {
            "name": "Github",
            "url": "https://github.com/fastplotlib/fastplotlib",
            "icon": "fa-brands fa-github",
        }
    ],
}

html_static_path = ["_static"]
html_logo = "_static/logo.png"
html_title = f"v{release}"

autodoc_member_order = "groupwise"
autoclass_content = "both"
add_module_names = False

autodoc_typehints = "description"
autodoc_typehints_description_target = "documented_params"
autodoc_preserve_defaults = True

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "numpy": ("https://numpy.org/doc/stable", None),
    "pygfx": ("https://docs.pygfx.org/stable", None),
    "wgpu": ("https://wgpu-py.readthedocs.io/en/latest", None),
    "rendercanvas": ("https://rendercanvas.readthedocs.io/stable/", None),
    # "fastplotlib": ("https://www.fastplotlib.org/", None),
}

html_css_files = [
    "style.css",
]

def setup(app):
    app.connect("builder-inited", add_pyodide_to_examples)
    app.connect("build-finished", add_files_to_run_pyodide_examples)
