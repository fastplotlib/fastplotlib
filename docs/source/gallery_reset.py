import fastplotlib as fpl


def reset_fastplotlib_style(gallery_conf, fname):
    """run by sphinx-gallery before each example, see ``reset_modules`` in conf.py"""
    # the config is global, restore the defaults that a previous example may have set
    fpl.style.default()
