from typing import Any

from ._index import ReferenceRangeContinuous, ReferenceRangeDiscrete, GlobalIndex
from ._ndw_subplot import NDWSubplot
from ._ui import NDWidgetUI
from ...layouts import ImguiFigure, Subplot


class NDWidget:
    def __init__(self, ref_ranges: dict[str, tuple], **kwargs):
        self._indices = GlobalIndex(ref_ranges, self._get_ndgraphics)
        self._figure = ImguiFigure(**kwargs)

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
    def indices(self) -> GlobalIndex:
        return self._indices

    @indices.setter
    def indices(self, new_indices: dict[str, int | float | Any]):
        self._indices.set = new_indices

    @property
    def ref_ranges(self) -> dict[str, ReferenceRangeContinuous | ReferenceRangeDiscrete]:
        return self._indices.ref_ranges

    def __getitem__(self, key: str | tuple[int, int] | Subplot):
        if not isinstance(key, Subplot):
            key = self.figure[key]
        return self._subplots_nd[key]

    def _get_ndgraphics(self):
        gs = list()
        for subplot in self._subplots_nd.values():
            gs.extend(subplot.nd_graphics)

        return tuple(gs)

    def show(self, **kwargs):
        return self.figure.show(**kwargs)
