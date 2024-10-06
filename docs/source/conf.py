# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os

# need to force offscreen rendering before importing fpl
# otherwise fpl tries to select glfw canvas
os.environ["WGPU_FORCE_OFFSCREEN"] = "1"

import fastplotlib
import pygfx
from pygfx.utils.gallery_scraper import find_examples_for_gallery
from pathlib import Path
import sys
from sphinx_gallery.sorting import ExplicitOrder
import imageio.v3 as iio

MAX_TEXTURE_SIZE = 2048
pygfx.renderers.wgpu.set_wgpu_limits(**{"max-texture-dimension2d": MAX_TEXTURE_SIZE})

ROOT_DIR = Path(__file__).parents[1].parents[0]  # repo root
EXAMPLES_DIR = Path.joinpath(ROOT_DIR, "examples", "desktop")

sys.path.insert(0, str(ROOT_DIR))

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "fastplotlib"
copyright = "2024, Kushal Kolar, Caitlin Lewis"
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


if os.environ["FETCH_ARTIFACT"] == "1":
    extensions.append("rtds_action")

    # The name of your GitHub repository
    rtds_action_github_repo = "fastplotlib/fastplotlib"

    # The path where the artifact should be extracted
    # Note: this is relative to the conf.py file!
    rtds_action_path = "_gallery"

    # The "prefix" used in the `upload-artifact` step of the action
    rtds_action_artifact_prefix = "gallery-"

    # A GitHub personal access token is required, more info below
    rtds_action_github_token = os.environ["GITHUB_TOKEN"]

    # Whether or not to raise an error on Read the Docs if the
    # artifact containing the notebooks can't be downloaded (optional)
    rtds_action_error_if_missing = False


sphinx_gallery_conf = {
    "gallery_dirs": "_gallery",
    "backreferences_dir": "_gallery/backreferences",
    "doc_module": ("fastplotlib",),
    "image_scrapers": ("pygfx",),
    "remove_config_comments": True,
    "subsection_order": ExplicitOrder(
        [
            "../../examples/desktop/image",
            "../../examples/desktop/image_widget",
            "../../examples/desktop/gridplot",
            "../../examples/desktop/line",
            "../../examples/desktop/line_collection",
            "../../examples/desktop/scatter",
            "../../examples/desktop/heatmap",
            "../../examples/desktop/misc",
            "../../examples/desktop/selectors",
            "../../examples/desktop/guis"
        ]
    ),
    "ignore_pattern": r'__init__\.py',
    "nested_sections": False,
    "thumbnail_size": (250, 250)
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

napoleon_custom_sections = ["Features"]

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
    "pygfx": ("https://docs.pygfx.org/stable/", None),
    "wgpu": ("https://wgpu-py.readthedocs.io/en/latest", None),
    "fastplotlib": ("https://fastplotlib.readthedocs.io/en/latest/", None),
}

html_theme_options = {
    "source_repository": "https://github.com/fastplotlib/fastplotlib",
    "source_branch": "main",
    "source_directory": "docs/",
}
