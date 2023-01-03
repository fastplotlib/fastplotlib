from typing import *
import pygfx
import numpy as np

from ._base import Graphic


class TextGraphic(Graphic):
    def __init__(
            self,
            text: str,
            position: Tuple[int] = (0, 0, 0),
            size: int = 10,
            face_color: Union[str, np.ndarray] = "w",
            outline_color: Union[str, np.ndarray] = "w",
            outline_thickness=0,
            name: str = None,
    ):
        super(TextGraphic, self).__init__(name=name)

        self._world_object = pygfx.Text(
            pygfx.TextGeometry(text=text, font_size=size, screen_space=False),
            pygfx.TextMaterial(color=face_color, outline_color=outline_color, outline_thickness=outline_thickness)
        )

        self.world_object.position.set(*position)

        self.name = None

    def update_text(self, text: str):
        self.world_object.geometry.set_text(text)

    def update_size(self, size: int):
        self.world_object.geometry.font_size = size

    def update_face_color(self, color: Union[str, np.ndarray]):
        self.world_object.material.color = color

    def update_outline_size(self, size: int):
        self.world_object.material.outline_thickness = size

    def update_outline_color(self, color: Union[str, np.ndarray]):
        self.world_object.material.outline_color = color

    def update_position(self, pos: Tuple[int, int, int]):
        self.world_object.position.set(*pos)
