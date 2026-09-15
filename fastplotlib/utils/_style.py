from copy import deepcopy

from ._config import global_config
from .. import graphics, layouts, axes


class style:
    """Sets of config defaults applied together"""

    # the config as it exists on fastplotlib import i.e. the defaults from the method signatures
    __default_config = deepcopy(global_config.to_dict())

    @staticmethod
    def light():
        """light color mode, white background, black axes, dark graphic colors, light subplot frame"""
        axes.Axes.config.init.color = "k"

        layouts.Subplot.config.init.background_color = "w"

        graphics.LineGraphic.config.init.colors = "blue"
        graphics.ScatterGraphic.config.init.colors = "blue"
        graphics.VectorsGraphic.config.init.color = "k"

        # update function is useful when config options are dicts or nested dicts
        global_config.update(
            layouts.Subplot.config.init,
            frame_kwargs=dict(
                plane_color={
                    "idle": (0.9, 0.9, 0.9),
                    "highlight": (0.8, 0.8, 0.9),
                    "action": (0.75, 0.75, 1.0),
                },
                title_kwargs=dict(face_color="black"),
            ),
        )

    @staticmethod
    def dark():
        """dark color mode, black background, white axes, light graphic colors, dark subplot frame"""
        axes.Axes.config.init.color = "w"

        layouts.Subplot.config.init.background_color = "k"

        graphics.LineGraphic.config.init.colors = "w"
        graphics.ScatterGraphic.config.init.colors = "w"
        graphics.VectorsGraphic.config.init.color = "w"

        # update function is useful when config options are dicts or nested dicts
        global_config.update(
            layouts.Subplot.config.init,
            frame_kwargs=dict(
                plane_color=None,
                title_kwargs=dict(face_color="w"),
            ),
        )

    @staticmethod
    def spaced():
        """subplot toolbar is shown, well spaced subplot frame"""
        layouts.Subplot.config.init.toolbar = True

        global_config.update(
            layouts.Subplot.config.init,
            frame_kwargs=dict(
                spacing=dict(
                    x0=1, sides=2, title_flanks=8, resize_handle_space=13, bottom=8
                ),
                title_kwargs=dict(font_size=16),
            ),
        )

    @staticmethod
    def default():
        """default configuration"""
        for cls, method_configs in style.__default_config.items():
            for method, options in method_configs.items():
                # deepcopy since some config values can be mutable, e.g. dicts
                global_config.update(getattr(cls.config, method), **deepcopy(options))

    @staticmethod
    def compact():
        """subplot toolbar is not shown, thin subplot frame"""
        layouts.Subplot.config.init.toolbar = False

        global_config.update(
            layouts.Subplot.config.init,
            frame_kwargs=dict(
                spacing=dict(
                    x0=1, sides=2, title_flanks=6, resize_handle_space=6, bottom=6
                ),
                title_kwargs=dict(font_size=10),
            ),
        )

    @staticmethod
    def very_compact():
        """same as compact() with no visible subplot frame"""
        layouts.Subplot.config.init.toolbar = False

        global_config.update(
            layouts.Subplot.config.init,
            frame_kwargs=dict(
                spacing=dict(
                    x0=0, sides=0, title_flanks=0, resize_handle_space=0, bottom=0
                ),
                title_kwargs=dict(font_size=0),
            ),
        )

    @staticmethod
    def flynn():
        """preset that optical physiology like"""
        style.very_compact()

        layouts.Subplot.config.auto_scale.zoom = 0.99
