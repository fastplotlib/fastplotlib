# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html
import fastplotlib
from sphinx_gallery.sorting import ExplicitOrder

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'fastplotlib'
copyright = '2023, Kushal Kolar, Caitlin Lewis'
author = 'Kushal Kolar, Caitlin Lewis'
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

templates_path = ['_templates']
exclude_patterns = []

napoleon_custom_sections = ['Features']

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "furo"

html_static_path = ['_static']
html_logo = "_static/logo.png"
html_title = f"v{release}"

autodoc_member_order = 'groupwise'
autoclass_content = "both"
add_module_names = False

autodoc_typehints = "description"
autodoc_typehints_description_target = "documented_params"

intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'numpy': ('https://numpy.org/doc/stable/', None),
    'pygfx': ('https://pygfx.readthedocs.io/en/latest', None)
}

html_theme_options = {
    "source_repository": "https://github.com/kushalkolar/fastplotlib",
    "source_branch": "master",
    "source_directory": "docs/",
}

sphinx_gallery_conf = {
    # exclude anything in data from ever being executed
    'filename_pattern': 'r"^((?![\\/]data[\\/]).)*$',
    'ignore_pattern': r'__init__\.py',
    'examples_dirs': '../../examples/desktop',
    'subsection_order': ExplicitOrder(
        [
            '../../examples/desktop/image/',
            '../../examples/desktop/gridplot/',
            '../../examples/desktop/line/',
            '../../examples/desktop/line_collection/',
            '../../examples/desktop/scatter/'
        ]),
    "gallery_dirs": "_gallery",
    "backreferences_dir": "_gallery/backreferences",
    'line_numbers': True,
    'remove_config_comments': True,
    "doc_module": ("fastplotlib",),
    "pypandoc": True
  #  "image_scrapers": ("fastplotlib",),
}
