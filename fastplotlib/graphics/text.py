import pygfx
import numpy as np

from ._base import Graphic
from ._features import (
    TextData,
    FontSize,
    TextFaceColor,
    TextOutlineColor,
    TextOutlineThickness,
)


class TextGraphic(Graphic):
    _features = {
        "text",
        "font_size",
        "face_color",
        "outline_color",
        "outline_thickness",
    }

    def __init__(
        self,
        text: str,
        font_size: float | int = 14,
        face_color: str | np.ndarray | list[float] | tuple[float] = "w",
        outline_color: str | np.ndarray | list[float] | tuple[float] = "w",
        outline_thickness: float = 0.0,
        screen_space: bool = True,
        offset: tuple[float] = (0, 0, 0),
        anchor: str = "middle-center",
        **kwargs,
    ):
        """
        Create a text Graphic

        Parameters
        ----------
        text: str
            text to display

        font_size: float | int, default 10
            font size

        face_color: str or array, default "w"
            str or RGBA array to set the color of the text

        outline_color: str or array, default "w"
            str or RGBA array to set the outline color of the text

        outline_thickness: float, default 0
            relative outline thickness, value between 0.0 - 0.5

        screen_space: bool = True
            if True, text size is in screen space, if False the text size is in data space

        offset: (float, float, float), default (0, 0, 0)
            places the text at this location

        anchor: str, default "middle-center"
            position of the origin of the text
            a string representing the vertical and horizontal anchors, separated by a dash

            * Vertical values: "top", "middle", "baseline", "bottom"
            * Horizontal values: "left", "center", "right"

        **kwargs
            passed to Graphic

        """

        super().__init__(**kwargs)

        self._text = TextData(text)
        self._font_size = FontSize(font_size)
        self._face_color = TextFaceColor(face_color)
        self._outline_color = TextOutlineColor(outline_color)
        self._outline_thickness = TextOutlineThickness(outline_thickness)

        world_object = pygfx.Text(
            text=self.text,
            font_size=self.font_size,
            screen_space=screen_space,
            anchor=anchor,
            material=pygfx.TextMaterial(
                color=self.face_color,
                outline_color=self.outline_color,
                outline_thickness=self.outline_thickness,
                pick_write=True,
            ),
        )

        self._set_world_object(world_object)

        self.offset = offset

    @property
    def world_object(self) -> pygfx.Text:
        """Text world object"""
        return super(TextGraphic, self).world_object

    @property
    def text(self) -> str:
        """the text displayed"""
        return self._text.value

    @text.setter
    def text(self, text: str):
        self._text.set_value(self, text)

    @property
    def font_size(self) -> float | int:
        """ "text font size"""
        return self._font_size.value

    @font_size.setter
    def font_size(self, size: float | int):
        self._font_size.set_value(self, size)

    @property
    def face_color(self) -> pygfx.Color:
        """text face color"""
        return self._face_color.value

    @face_color.setter
    def face_color(self, color: str | np.ndarray | list[float] | tuple[float]):
        self._face_color.set_value(self, color)

    @property
    def outline_thickness(self) -> float:
        """text outline thickness"""
        return self._outline_thickness.value

    @outline_thickness.setter
    def outline_thickness(self, thickness: float):
        self._outline_thickness.set_value(self, thickness)

    @property
    def outline_color(self) -> pygfx.Color:
        """text outline color"""
        return self._outline_color.value

    @outline_color.setter
    def outline_color(self, color: str | np.ndarray | list[float] | tuple[float]):
        self._outline_color.set_value(self, color)
