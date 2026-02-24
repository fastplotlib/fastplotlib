from typing import Any

from ._index import ReferenceRangeContinuous, ReferenceRangeDiscrete
from ._ndw_subplot import NDWSubplot
from ._ui import NDWidgetUI
from ...layouts import ImguiFigure, Subplot


class NDWidget:
    def __init__(self, ref_ranges: list[tuple], **kwargs):
        # TODO: this should maybe be an ordered dict??
        self._ref_ranges = list()

        for r in ref_ranges:
            if len(r) == 4:
                # assume start, stop, step, unit
                refr = ReferenceRangeContinuous(*r)
            elif len(r) == 2:
                refr = ReferenceRangeDiscrete(*r)
            else:
                raise ValueError

            self._ref_ranges.append(refr)

        self._figure = ImguiFigure(**kwargs)

        self._subplots_nd: dict[Subplot, NDWSubplot] = dict()
        for subplot in self.figure:
            self._subplots_nd[subplot] = NDWSubplot(self, subplot)

        # starting index for all dims
        self._indices = tuple(refr[0] for refr in self.ref_ranges)

        # hard code the expected height so that the first render looks right in tests, docs etc.
        ui_size = 57 + (50 * len(self.indices))

        self._sliders_ui = NDWidgetUI(self.figure, ui_size, self)
        self.figure.add_gui(self._sliders_ui)

    @property
    def figure(self) -> ImguiFigure:
        return self._figure

    @property
    def ref_ranges(self) -> tuple[ReferenceRangeContinuous | ReferenceRangeDiscrete]:
        return tuple(self._ref_ranges)

    @property
    def indices(self) -> tuple:
        return self._indices

    @indices.setter
    def indices(self, new_indices: tuple[Any]):
        for subplot in self._subplots_nd.values():
            for ndg in subplot.nd_graphics:
                ndg.indices = new_indices

        self._indices = new_indices

    def __getitem__(self, key: str | tuple[int, int] | Subplot):
        if not isinstance(key, Subplot):
            key = self.figure[key]
        return self._subplots_nd[key]

    def show(self, **kwargs):
        return self.figure.show(**kwargs)
