from pathlib import Path

import imageio.v3 as iio
from sphinx_gallery.scrapers import figure_rst
from wgpu.gui import WgpuCanvasBase

from pygfx.renderers import Renderer
from pygfx.utils.show import Display

# The scraper's default configuration. An example code-block
# may overwrite these values by setting comments of the form
#
#     # sphinx_gallery_pygfx_<name> = <value>
#
# inside the code block. These comments will not be shown in the generated
# gallery example and will be reset after each code block.
default_config = {
    "render": False,  # if True, render an image
    "animate": False,  # if True, render a GIF
    "target_name": "renderer",  # the display to use
    # GIF settings
    "duration": 3,  # how many seconds to record
    "loop": 0,  # loop forever
}


def fpl_scraper(block, block_vars, gallery_conf, **kwargs):
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

    # parse block-level config
    scraper_config = default_config.copy()
    config_prefix = "# sphinx_gallery_fpl_"
    for line in block[1].split("\n"):
        if not line.startswith(config_prefix):
            continue

        name, value = line[len(config_prefix):].split(" = ")
        scraper_config[name] = eval(value)

    if not scraper_config["render"] and not scraper_config["animate"]:
        return ""  # nothing to do

    target = block_vars["example_globals"][scraper_config["target_name"]]
    if isinstance(target, Display):
        canvas = target.canvas
    elif isinstance(target, Renderer):
        canvas = target.target
    elif isinstance(target, WgpuCanvasBase):
        canvas = target
    else:
        raise ValueError("`target` must be a Display, Renderer, or Canvas.")

    images = []

    if scraper_config["render"]:
        path_generator = block_vars["image_path_iterator"]
        img_path = next(path_generator)
        iio.imwrite(img_path, canvas.draw())
        images.append(img_path)

    if scraper_config["animate"]:
        frames = []

        # by default videos are rendered at ~ 30 FPS
        n_frames = scraper_config["duration"] * 30

        for _ in range(n_frames):
            frames.append(canvas.draw())

        path_generator = block_vars["image_path_iterator"]
        img_path = Path(next(path_generator)).with_suffix(".webp")
        iio.imwrite(
            img_path,
            frames,
            duration=33,
            loop=scraper_config["loop"],
            lossless=True,
        )
        images.append(img_path)

    return figure_rst(images, gallery_conf["src_dir"])
