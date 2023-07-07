from pathlib import Path

import imageio.v3 as iio
from sphinx_gallery.scrapers import figure_rst

default_config = {

}


def fastplotlib_scraper(block, block_vars, gallery_conf, **kwargs):
    """Scrape pygfx images and animations
        Parameters
        ----------
        block : tuple
            A tuple containing the (label, content, line_number) of the block.
        block_vars : dict
            Dict of block variables.
        gallery_conf : dict
            Contains the configuration of Sphinx-Gallery
        **kwargs : dict
            Additional keyword arguments to pass to
            :meth:`~matplotlib.figure.Figure.savefig`, e.g. ``format='svg'``.
            The ``format`` kwarg in particular is used to set the file extension
            of the output file (currently only 'png', 'jpg', and 'svg' are
            supported).
        Returns
        -------
        rst : str
            The ReSTructuredText that will be rendered to HTML containing
            the images. This is often produced by :func:`figure_rst`.
    """
    config_prefix = "# sphinx_gallery_fastplotlib_render"
    for line in block[1].split("\n"):
        if not line.startswith(config_prefix):
            continue

    images = []

    path_generator = block_vars["image_path_iterator"]
    img_path = next(path_generator)
    plot = block_vars["example_globals"]["plot"]
    iio.imwrite(img_path, plot.renderer.target.draw())
    images.append(img_path)

    return figure_rst(images, gallery_conf["src_dir"])
