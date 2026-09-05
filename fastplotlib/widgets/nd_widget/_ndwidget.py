from __future__ import annotations

from typing import Any, Optional

from ._index import RangeContinuous, RangeDiscrete, ReferenceIndex
from ._ndw_subplot import NDWSubplot
from ._ui import NDWidgetUI, RightClickMenu
from ...layouts import ImguiFigure, Subplot


class NDWidget:
    def __init__(self, ref_ranges: dict[str, tuple] = None, ref_index: Optional[ReferenceIndex] = None, **kwargs):
        """
        Explore n-dimensional multi-modal datasets through synchronized graphical representations.

        An ``NDWidget`` manages ``NDGraphic`` objects distributed across the subplots of an ``ImguiFigure``. Each
        ``NDGraphic`` wraps one array-like object, names every dimension of that array, and declares which of those
        dims are *spatial*, i.e. rendered. All remaining dims are *slider dims*. Every slider dim gets a slider, and
        moving it re-slices every ``NDGraphic`` that has that dim and updates its ``Graphic``. Arrays of different
        shapes, dim orders and sampling rates therefore stay synchronized as long as they name their shared dims
        identically.

        Slider positions are stored in reference-space units (ex: seconds, µm, Hz) by a :class:`ReferenceIndex`
        which is shared by every ``NDGraphic`` in the widget. Each ``NDGraphic`` maps these values onto indices of
        its own array using its ``slider_dim_transforms``.

        Use ``ndw[row, col]`` or ``ndw["subplot_name"]`` to get the :class:`NDWSubplot` for a subplot, it provides
        the ``add_nd_<...>`` methods.

        Parameters
        ----------
        ref_ranges: dict[str, tuple[float, float, float] | RangeContinuous], optional
            Reference range for each slider dim, ``{dim_name: (start, stop, step)}`` or a :class:`RangeContinuous`
            instance. These are in reference-space units, ``start`` and ``stop`` bound the slider and ``step`` is
            the increment used by the step and play buttons.

            A slider dim with no entry here gets an ``AutoRangeContinuous`` of ``(0, <size of that dim>, 1)`` when
            the graphic is added, along with a warning. With the default identity ``slider_dim_transform`` this is
            a one-to-one mapping from reference-space units to array indices, i.e. the reference value *is* the
            array index. Ex: a dim of size 1000 gets the range ``(0, 1000, 1)``, the slider spans ``[0, 999]``, and
            reference value ``437`` indexes element ``437``.

            Specify a range when the reference-space units are not array indices, ex:
            ``{"time": (0.0, 10.0, 0.001)}`` for 10 seconds at 1 ms resolution, together with a
            ``slider_dim_transform`` that maps seconds onto the indices of that array. The size is unknown for a
            graphic added with ``data=None``, so its slider dims must be given a range here.

        ref_index: ReferenceIndex, optional
            Use an existing ``ReferenceIndex`` instead of creating one from ``ref_ranges``, which is then ignored.
            Multiple ``NDWidget`` instances that share a ``ReferenceIndex`` are synchronized, so one set of sliders
            can drive data displayed across several windows.

        kwargs
            passed to :class:`.ImguiFigure`

        Examples
        --------

        A video and a set of traces that share a "time" dim, driven by one slider::

            import numpy as np
            import fastplotlib as fpl

            video = np.random.rand(1000, 512, 512)  # [time, row, col]
            traces = np.random.rand(50, 1000, 2)    # [neuron, time, xy]

            ndw = fpl.NDWidget(ref_ranges={"time": (0, 1000, 1)}, shape=(1, 2))

            # all dim names, then the spatial dims in display order
            ndw[0, 0].add_nd_image(video, ("time", "row", "col"), ("row", "col"))
            ndw[0, 1].add_nd_timeseries(traces, ("neuron", "time", "xy"), ("neuron", "time", "xy"))

            ndw.show()

        """
        if ref_index is None:
            if ref_ranges is None:
                ref_ranges = dict()
            self._indices = ReferenceIndex(ref_ranges)
        else:
            self._indices = ref_index

        self._indices._add_ndwidget_(self)

        self._figure = ImguiFigure(**kwargs)
        self._figure.set_imgui_right_click(RightClickMenu(self))

        self._subplots_nd: dict[Subplot, NDWSubplot] = dict()
        for subplot in self.figure:
            self._subplots_nd[subplot] = NDWSubplot(self, subplot)

        # hard code the expected height so that the first render looks right in tests, docs etc.
        ui_size = 57 + (50 * len(self.indices))

        self._sliders_ui = NDWidgetUI(self)
        self.figure.add_imgui_window(
            self._sliders_ui, location="bottom", size=ui_size, title="NDWidget controls"
        )

    @property
    def figure(self) -> ImguiFigure:
        """The ``ImguiFigure`` that contains the subplots of this widget"""
        return self._figure

    @property
    def indices(self) -> ReferenceIndex:
        """
        Get or set the current index of each slider dim.

        Returns the ``ReferenceIndex`` that is shared by every ``NDGraphic`` in this widget. Set using a
        ``{dim_name: index}`` mapping in reference-space units, values are clamped to the reference range of
        that dim and any dim that is not given keeps its current index.
        """
        return self._indices

    @indices.setter
    def indices(self, new_indices: dict[str, int | float | Any]):
        self._indices.set(new_indices)

    @property
    def ranges(self) -> dict[str, RangeContinuous | RangeDiscrete]:
        """the reference range of each slider dim, ``{dim_name: range}``"""
        return self._indices.ref_ranges

    @property
    def ndgraphics(self):
        """all the ``NDGraphic`` instances in every subplot of this widget"""
        gs = list()
        for subplot in self._subplots_nd.values():
            gs.extend(subplot.nd_graphics)

        return tuple(gs)

    def __getitem__(self, key: str | tuple[int, int] | Subplot):
        if not isinstance(key, Subplot):
            key = self.figure[key]
        return self._subplots_nd[key]

    def show(self, **kwargs):
        """
        Show the widget.

        Parameters
        ----------

        kwargs: Any
            passed to ``Figure.show()``

        Returns
        -------
        BaseRenderCanvas
            In Qt or GLFW, the canvas window containing the Figure will be shown.
            In a notebook, it will display the plot in the output cell or sidecar.

        """

        return self.figure.show(**kwargs)

    def close(self):
        """Close the widget"""
        self.figure.close()
