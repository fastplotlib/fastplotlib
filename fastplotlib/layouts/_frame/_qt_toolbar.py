from fastplotlib.layouts._subplot import Subplot
from fastplotlib.layouts._frame._toolbar import ToolBar


class QtToolbar(ToolBar):
    def __init__(self, plot):
        self.plot = plot

        super().__init__(plot)

    def _get_subplot_dropdown_value(self) -> str:
        raise NotImplemented

    @property
    def current_subplot(self) -> Subplot:
        if hasattr(self.plot, "_subplots"):
            # parses dropdown value as plot name or position
            current = self._get_subplot_dropdown_value()
            if current[0] == "(":
                # str representation of int tuple to tuple of int
                current = (int(i) for i in current.strip("()").split(","))
                return self.plot[current]
            else:
                return self.plot[current]
        else:
            return self.plot

    def panzoom_handler(self, ev):
        raise NotImplemented

    def maintain_aspect_handler(self, ev):
        raise NotImplemented

    def y_direction_handler(self, ev):
        raise NotImplemented

    def auto_scale_handler(self, ev):
        raise NotImplemented

    def center_scene_handler(self, ev):
        raise NotImplemented

    def record_handler(self, ev):
        raise NotImplemented
