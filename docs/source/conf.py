# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html
import fastplotlib

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
]

autosummary_generate = True

templates_path = ['_templates']
exclude_patterns = []

napoleon_custom_sections = ['Features']

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "furo"
# html_theme_options = {"page_sidebar_items": ["class_page_toc"]}

html_static_path = ['_static']

autodoc_member_order = 'groupwise'
autoclass_content = "both"

autodoc_typehints = "description"
autodoc_typehints_description_target = "documented_params"


intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'numpy': ('https://numpy.org/doc/stable/', None),
    'pygfx': ('https://pygfx.readthedocs.io/en/latest', None)
}


# html_theme_options = {
    # "show_toc_level": 3,
    # "github_url": "https://github.com/kushalkolar/fastplotlib",
    # "navbar_end": ["theme-switcher", "navbar-icon-links"],
    # "secondary_sidebar_items": ["page-toc"]
# }

#
# html_sidebars = {
#     "**": ["sidebar-nav-bs.html"],
#     'index': []  # don't show sidebar on main landing page
# }
#
