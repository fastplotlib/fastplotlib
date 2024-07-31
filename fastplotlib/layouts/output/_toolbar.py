from .._subplot import Subplot


class ToolBar:
    def __init__(self, figure):
        self.figure = figure

    def _get_subplot_dropdown_value(self) -> str:
        raise NotImplemented

    @property
    def current_subplot(self) -> Subplot:
        """Returns current subplot"""
        if hasattr(self.figure, "_subplots"):
            # parses dropdown or label value as plot name or position
            current = self._get_subplot_dropdown_value()
            if current[0] == "(":
                # str representation of int tuple to tuple of int
                current = tuple(int(i) for i in current.strip("()").split(","))
                return self.figure[current]
            else:
                return self.figure[current]
        else:
            return self.figure

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

    def add_polygon(self, ev):
        raise NotImplemented
