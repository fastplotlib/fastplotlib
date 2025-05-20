from imgui_bundle import imgui
from icecream import ic

from ._base import Window


class DebugWindow(Window):
    def __init__(self, objs: list):
        self._objs = objs
        super().__init__()

    @property
    def objs(self) -> tuple:
        return tuple(self._objs)

    def add(self, obj):
        self._objs.append(obj)

    def draw_window(self):
        imgui.set_next_window_pos((300, 0), imgui.Cond_.appearing)
        imgui.set_next_window_pos((0, 0), imgui.Cond_.appearing)

        imgui.begin("Debug", None)

        info = list()

        for obj in self.objs:
            if callable(obj):
                info.append(ic.format(obj()))
            else:
                info.append(ic.format(obj))

        imgui.text_wrapped("\n\n".join(info))

        imgui.end()
