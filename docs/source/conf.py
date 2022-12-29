# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html
from bs4 import BeautifulSoup
from typing import *

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'fastplotlib'
copyright = '2022, Kushal Kolar, Caitlin Lewis'
author = 'Kushal Kolar, Caitlin Lewis'
release = 'v0.1.0.a6'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = ["sphinx.ext.napoleon", "sphinx.ext.autodoc"]
autodoc_typehints = "description"

templates_path = ['_templates']
exclude_patterns = []



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'pydata_sphinx_theme'
html_theme_options = {"page_sidebar_items": ["class_page_toc"]}

html_static_path = ['_static']

autodoc_member_order = 'bysource'
autoclass_content = "both"

def _setup_navbar_side_toctree(app: Any):

    def add_class_toctree_function(app: Any, pagename: Any, templatename: Any, context: Any, doctree: Any):
        def get_class_toc() -> Any:
            soup = BeautifulSoup(context["body"], "html.parser")

            matches = soup.find_all('dl')
            if matches is None or len(matches) == 0:
                return ""
            items = []
            deeper_depth = matches[0].find('dt').get('id').count(".")
            for match in matches:
                match_dt = match.find('dt')
                if match_dt is not None and match_dt.get('id') is not None:
                    current_title = match_dt.get('id')
                    current_depth = match_dt.get('id').count(".")
                    current_link = match.find(class_="headerlink")
                    if current_link is not None:
                        if deeper_depth > current_depth:
                            deeper_depth = current_depth
                        if deeper_depth == current_depth:
                            items.append({
                                "title": current_title.split('.')[-1],
                                "link": current_link["href"],
                                "attributes_and_methods": []
                            })
                        if deeper_depth < current_depth:
                            items[-1]["attributes_and_methods"].append(
                                {
                                    "title": current_title.split('.')[-1],
                                    "link": current_link["href"],
                                }
                            )
            return items
        context["get_class_toc"] = get_class_toc

    app.connect("html-page-context", add_class_toctree_function)


def setup(app: Any):
    for setup_function in [
        _setup_navbar_side_toctree,
    ]:
        setup_function(app)
