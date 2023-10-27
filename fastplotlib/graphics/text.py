from typing import *
import pygfx
import numpy as np

from ._base import Graphic


class TextGraphic(Graphic):
    def __init__(
        self,
        text: str,
        position: Tuple[int] = (0, 0, 0),
        size: int = 14,
        face_color: Union[str, np.ndarray] = "w",
        outline_color: Union[str, np.ndarray] = "w",
        outline_thickness=0,
        screen_space: bool = True,
        anchor: str = "middle-center",
        *args,
        **kwargs
    ):
        """
        Create a text Graphic

        Parameters
        ----------
        text: str
            display text

        position: int tuple, default (0, 0, 0)
            int tuple indicating location of text in scene

        size: int, default 10
            text size

        face_color: str or array, default "w"
            str or RGBA array to set the color of the text

        outline_color: str or array, default "w"
            str or RGBA array to set the outline color of the text

        outline_thickness: int, default 0
            text outline thickness

        screen_space: bool = True
            whether the text is rendered in screen space, in contrast to world space

        name: str, optional
            name of graphic, passed to Graphic

        anchor: str, default "middle-center"
            position of the origin of the text
            a string representing the vertical and horizontal anchors, separated by a dash

            * Vertical values: "top", "middle", "baseline", "bottom"
            * Horizontal values: "left", "center", "right"
        """
        super(TextGraphic, self).__init__(*args, **kwargs)

        self._text = text

        world_object = pygfx.Text(
            pygfx.TextGeometry(
                text=str(text),
                font_size=size,
                screen_space=screen_space,
                anchor=anchor,
            ),
            pygfx.TextMaterial(
                color=face_color,
                outline_color=outline_color,
                outline_thickness=outline_thickness,
            ),
        )

        self._set_world_object(world_object)

        self.world_object.position = position

    @property
    def text(self):
        """Returns the text of this graphic."""
        return self._text

    @text.setter
    def text(self, text: str):
        """Set the text of this graphic."""
        if not isinstance(text, str):
            raise ValueError("Text must be of type str.")

        self._text = text
        self.world_object.geometry.set_text(self._text)

    @property
    def text_size(self):
        """Returns the text size of this graphic."""
        return self.world_object.geometry.font_size

    @text_size.setter
    def text_size(self, size: Union[int, float]):
        """Set the text size of this graphic."""
        if not (isinstance(size, int) or isinstance(size, float)):
            raise ValueError("Text size must be of type int or float")

        self.world_object.geometry.font_size = size

    @property
    def face_color(self):
        """Returns the face color of this graphic."""
        return self.world_object.material.color

    @face_color.setter
    def face_color(self, color: Union[str, np.ndarray]):
        """Set the face color of this graphic."""
        if not (isinstance(color, str) or isinstance(color, np.ndarray)):
            raise ValueError("Face color must be of type str or np.ndarray")

        color = pygfx.Color(color)

        self.world_object.material.color = color

    @property
    def outline_size(self):
        """Returns the outline size of this graphic."""
        return self.world_object.material.outline_thickness

    @outline_size.setter
    def outline_size(self, size: Union[int, float]):
        """Set the outline size of this text graphic."""
        if not (isinstance(size, int) or isinstance(size, float)):
            raise ValueError("Outline size must be of type int or float")

        self.world_object.material.outline_thickness = size

    @property
    def outline_color(self):
        """Returns the outline color of this graphic."""
        return self.world_object.material.outline_color

    @outline_color.setter
    def outline_color(self, color: Union[str, np.ndarray]):
        """Set the outline color of this graphic"""
        if not (isinstance(color, str) or isinstance(color, np.ndarray)):
            raise ValueError("Outline color must be of type str or np.ndarray")

        self.world_object.material.outline_color = color

