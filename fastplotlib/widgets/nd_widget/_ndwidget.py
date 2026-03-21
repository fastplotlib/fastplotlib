from __future__ import annotations

from typing import Any, Optional

from ._index import RangeContinuous, RangeDiscrete, ReferenceIndex
from ._ndw_subplot import NDWSubplot
from ._ui import NDWidgetUI, RightClickMenu
from ...layouts import ImguiFigure, Subplot


class NDWidget:
    def __init__(self, ref_ranges: dict[str, tuple], ref_index: Optional[ReferenceIndex] = None, **kwargs):
        if ref_index is None:
            self._indices = ReferenceIndex(ref_ranges)
        else:
            self._indices = ref_index

        self._indices._add_ndwidget_(self)

        self._figure = ImguiFigure(std_right_click_menu=RightClickMenu, **kwargs)
        self._figure.std_right_click_menu.set_nd_widget(self)

        self._subplots_nd: dict[Subplot, NDWSubplot] = dict()
        for subplot in self.figure:
            self._subplots_nd[subplot] = NDWSubplot(self, subplot)

        # hard code the expected height so that the first render looks right in tests, docs etc.
        ui_size = 57 + (50 * len(self.indices))

        self._sliders_ui = NDWidgetUI(self.figure, ui_size, self)
        self.figure.add_gui(self._sliders_ui)

    @property
    def figure(self) -> ImguiFigure:
        return self._figure

    @property
    def indices(self) -> ReferenceIndex:
        return self._indices

    @indices.setter
    def indices(self, new_indices: dict[str, int | float | Any]):
        self._indices.set(new_indices)

    @property
    def ranges(self) -> dict[str, RangeContinuous | RangeDiscrete]:
        return self._indices.ref_ranges

    @property
    def ndgraphics(self):
        gs = list()
        for subplot in self._subplots_nd.values():
            gs.extend(subplot.nd_graphics)

        return tuple(gs)

    def __getitem__(self, key: str | tuple[int, int] | Subplot):
        if not isinstance(key, Subplot):
            key = self.figure[key]
        return self._subplots_nd[key]

    def show(self, **kwargs):
        return self.figure.show(**kwargs)

    def close(self):
        self.figure.close()
