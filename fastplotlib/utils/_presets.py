from ._config import global_config
from .. import graphics, layouts, axes


class presets:
    """Sets of config defaults applied together"""

    @staticmethod
    def light():
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
        presets.dark()
        presets.spaced()

    @staticmethod
    def compact():
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
        presets.very_compact()

        layouts.Subplot.config.auto_scale.zoom = 0.99
