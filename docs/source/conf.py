# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html
import fastplotlib

from sphinx_gallery.sorting import ExplicitOrder
import wgpu.gui.offscreen
import os
import sys

ROOT_DIR = os.path.abspath(os.path.join(__file__, "..", ".."))
sys.path.insert(0, ROOT_DIR)

# -- Sphix Gallery Hackz -----------------------------------------------------
# When building the gallery, render offscreen and don't process
# the event loop while parsing the example


def _ignore_offscreen_run():
    wgpu.gui.offscreen.run = lambda: None


os.environ["WGPU_FORCE_OFFSCREEN"] = "True"
_ignore_offscreen_run()

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "fastplotlib"
copyright = "2023, Kushal Kolar, Caitlin Lewis"
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
    "nbsphinx",
    "sphinx_gallery.gen_gallery"
]

autosummary_generate = True

templates_path = ["_templates"]
exclude_patterns = []

napoleon_custom_sections = ["Features"]

parent_path = os.path.abspath(os.path.join(ROOT_DIR, os.pardir))

sphinx_gallery_conf = {
    "examples_dirs": f"{parent_path}/examples/desktop",
    "gallery_dirs": "_gallery",
    "backreferences_dir": "_gallery/backreferences",
    # "exclude_implicit_doc": {
    #     "WgpuRenderer",
    #     "Resource",
    #     "WorldObject",
    #     "Geometry",
    #     "Material",
    #     "Controller",
    #     "Camera",
    #     "show",
    #     "Display",
    #     "Group",
    #     "Scene",
    #     "Light",
    # },
    "doc_module": ("fastplotlib",),
    "image_scrapers": ("fastplotlib",),
    # "subsection_order": ExplicitOrder(
    #     [
    #         f"{parent_path}/examples/desktop",
    #         # "../examples/feature_demo",
    #         # "../examples/validation",
    #         # "../examples/other",
    #     ]
    # ),
    "remove_config_comments": True,
    # Exclude files in 'other' dir from being executed
    "filename_pattern": r"^((?![\\/]other[\\/]).)*$",
}

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "furo"

html_static_path = ["_static"]
html_logo = "_static/logo.png"
html_title = f"v{release}"

autodoc_member_order = "groupwise"
autoclass_content = "both"
add_module_names = False

autodoc_typehints = "description"
autodoc_typehints_description_target = "documented_params"

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
    "pygfx": ("https://pygfx.readthedocs.io/en/latest", None),
}

html_theme_options = {
    "source_repository": "https://github.com/kushalkolar/fastplotlib",
    "source_branch": "main",
    "source_directory": "docs/",
}
