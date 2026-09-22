from __future__ import annotations

import itertools
from typing import Any
from warnings import warn
import weakref

import numpy as np
import pygfx
from imgui_bundle import imgui

from ..graphics import Graphic
from ..graphics.features import BufferManager, VertexColors, parse_dash_pattern
from ..graphics.features._scatter import user_input_to_marker
from ._base import ImguiContainer, ImguiWindow
from ._colorbar import ImguiColorbar

# marker shapes a legend can draw, the rest of the pygfx marker shapes are not made of imgui draw
# list primitives
MARKER_SHAPES = (
    "circle",
    "ring",
    "square",
    "diamond",
    "plus",
    "cross",
    "asterisk6",
    "asterisk8",
    "tick",
    "tick_left",
    "tick_right",
    "triangle_up",
    "triangle_down",
    "triangle_left",
    "triangle_right",
)

# angles of the legs of the asterisks, in radians
ASTERISK6_ANGLES = np.arange(3) * np.pi / 3
ASTERISK8_ANGLES = np.arange(4) * np.pi / 4

SWATCH_WIDTH = 28  # width in pixels of the swatch drawn to the left of a label
SWATCH_GAP = 6  # gap in pixels between the swatch and its label
INDENT = 8  # indent in pixels of the elements drawn below an item's label


def check_marker(marker: str) -> str:
    """the pygfx marker shape name for ``marker``, raises if a legend cannot draw it"""
    marker = user_input_to_marker(marker)

    if marker not in MARKER_SHAPES:
        raise ValueError(
            f"a legend cannot draw the marker: {marker!r}, it is not made of imgui draw list "
            f"primitives. The markers a legend can draw are: {MARKER_SHAPES}"
        )

    return marker


def imgui_color(color: pygfx.Color) -> int:
    """a color as an imgui packed color"""
    return imgui.color_convert_float4_to_u32(tuple(pygfx.Color(color)))


def bar_corners(
    cx: float, cy: float, length: float, width: float, angle: float
) -> tuple:
    """the corners of a ``length`` by ``width`` bar centered on (cx, cy), rotated by ``angle``"""
    along = 0.5 * length * np.array([np.cos(angle), np.sin(angle)])
    across = 0.5 * width * np.array([-np.sin(angle), np.cos(angle)])
    center = np.array([cx, cy])

    corners = [
        center - along - across,
        center + along - across,
        center + along + across,
        center - along + across,
    ]

    return tuple((float(x), float(y)) for x, y in corners)


def draw_marker(
    draw_list,
    marker: str,
    cx: float,
    cy: float,
    size: float,
    color,
    edge_color,
    edge_width: float,
):
    """
    Draw a scatter marker centered on (cx, cy), with the geometry of the pygfx marker SDFs.

    ``marker`` must be one of ``MARKER_SHAPES``.
    """
    fill = imgui_color(color)
    edge = imgui_color(edge_color)
    radius = 0.5 * size

    match marker:
        case "circle":
            draw_list.add_circle_filled((cx, cy), radius, fill)
            if edge_width > 0:
                draw_list.add_circle((cx, cy), radius, edge, thickness=edge_width)

        case "ring":
            # the difference of a disc of size/2 and a disc of size/4
            draw_list.add_circle((cx, cy), 0.375 * size, fill, thickness=0.25 * size)

        case "square":
            draw_list.add_rect_filled(
                (cx - radius, cy - radius), (cx + radius, cy + radius), fill
            )
            if edge_width > 0:
                draw_list.add_rect(
                    (cx - radius, cy - radius),
                    (cx + radius, cy + radius),
                    edge,
                    thickness=edge_width,
                )

        case "diamond":
            draw_list.add_quad_filled(
                (cx, cy - radius),
                (cx + radius, cy),
                (cx, cy + radius),
                (cx - radius, cy),
                fill,
            )

        case "plus" | "cross":
            # two bars of size by size/3, a cross is a plus rotated by 45 degrees
            angle = 0.0 if marker == "plus" else 0.25 * np.pi
            for a in (angle, angle + 0.5 * np.pi):
                draw_list.add_quad_filled(*bar_corners(cx, cy, size, size / 3, a), fill)

        case "asterisk6" | "asterisk8":
            # legs of size by size/5
            angles = ASTERISK6_ANGLES if marker == "asterisk6" else ASTERISK8_ANGLES
            for a in angles:
                draw_list.add_quad_filled(*bar_corners(cx, cy, size, size / 5, a), fill)

        case "tick" | "tick_left" | "tick_right":
            # a tick has no fill, only its edge is visible, and it is a half tick on one side
            top = cy - radius if marker != "tick_right" else cy
            bottom = cy + radius if marker != "tick_left" else cy
            draw_list.add_line((cx, top), (cx, bottom), edge, max(edge_width, 1.0))

        case "triangle_up" | "triangle_down" | "triangle_left" | "triangle_right":
            # the base spans `size` and the apex is size/2 from it, centered on size/4
            half = 0.5 * radius
            match marker:
                case "triangle_up":
                    points = [
                        (cx - radius, cy + half),
                        (cx + radius, cy + half),
                        (cx, cy - half),
                    ]
                case "triangle_down":
                    points = [
                        (cx - radius, cy - half),
                        (cx + radius, cy - half),
                        (cx, cy + half),
                    ]
                case "triangle_left":
                    points = [
                        (cx + half, cy - radius),
                        (cx + half, cy + radius),
                        (cx - half, cy),
                    ]
                case _:
                    points = [
                        (cx - half, cy - radius),
                        (cx - half, cy + radius),
                        (cx + half, cy),
                    ]

            draw_list.add_triangle_filled(*points, fill)
            if edge_width > 0:
                draw_list.add_triangle(*points, edge, thickness=edge_width)


class LegendElement:
    """One entry of a :class:`.LegendItem`, a swatch and its label."""

    def __init__(self, label: str, color):
        self._label = label
        self._color = pygfx.Color(color)

    @property
    def label(self) -> str:
        """the label drawn next to the swatch"""
        return self._label

    @property
    def color(self) -> pygfx.Color:
        """the color the swatch is drawn with"""
        return self._color

    @property
    def swatch_height(self) -> float:
        """height in pixels the swatch needs, must be implemented in subclass"""
        raise NotImplementedError

    def draw_swatch(self, draw_list, x: float, y: float, width: float, height: float):
        """draw the swatch in the given rect, must be implemented in subclass"""
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"{type(self).__name__} '{self.label}'"


class LineLegendElement(LegendElement):
    def __init__(self, label: str, color, thickness: float, dash_pattern):
        """A line sample drawn with the thickness and dash pattern of the graphic."""
        super().__init__(label, color)

        self._thickness = float(thickness)
        self._dash_pattern = parse_dash_pattern(dash_pattern)

    @property
    def swatch_height(self) -> float:
        return self._thickness

    def draw_swatch(self, draw_list, x: float, y: float, width: float, height: float):
        color = imgui_color(self._color)
        cy = y + 0.5 * height

        # the dash pattern is the length of alternating strokes and gaps, in units of the
        # thickness. An odd pattern repeats so that strokes and gaps alternate.
        pattern = np.asarray(self._dash_pattern, dtype=float) * self._thickness
        if pattern.size % 2:
            pattern = np.tile(pattern, 2)

        if pattern.sum() <= 0:
            # no pattern, or one that never advances along the line
            draw_list.add_line((x, cy), (x + width, cy), color, self._thickness)
            return

        position = x
        for stroke, gap in itertools.cycle(pattern.reshape(-1, 2)):
            if position >= x + width:
                break
            if stroke == 0:
                # a zero length stroke is a dot
                draw_list.add_circle_filled(
                    (position, cy), 0.5 * self._thickness, color
                )
            else:
                end = min(position + stroke, x + width)
                draw_list.add_line((position, cy), (end, cy), color, self._thickness)
            position += stroke + gap


class ScatterLegendElement(LegendElement):
    def __init__(
        self,
        label: str,
        color,
        marker: str,
        size: float,
        edge_color,
        edge_width: float,
    ):
        """A marker drawn with the marker shape, size and edge of the graphic."""
        super().__init__(label, color)

        self._marker = check_marker(marker)
        self._size = float(size)
        self._edge_color = pygfx.Color(edge_color)
        self._edge_width = float(edge_width)

    @property
    def swatch_height(self) -> float:
        return self._size

    def draw_swatch(self, draw_list, x: float, y: float, width: float, height: float):
        draw_marker(
            draw_list,
            self._marker,
            x + 0.5 * width,
            y + 0.5 * height,
            self._size,
            self._color,
            self._edge_color,
            self._edge_width,
        )


class LegendItem(ImguiContainer):
    """
    The legend representation of a graphic, created with ``Graphic.create_legend_item()``.

    An item has one :class:`.LegendElement` per labelled value of the graphic, or an
    :class:`.ImguiColorbar` when the graphic uses a quantitative colormap. It follows the graphic:
    when a feature it represents changes, its elements are made again.
    """

    COLORBAR_HEIGHT = 150  # height in pixels of the colorbar of a quantitative colormap

    # the graphic features the elements are made from, the elements are made again when one of
    # them changes
    _events: tuple[str, ...] = ()

    def __init__(
        self, graphic: Graphic, label: str = None, cmap_transform_labels: dict = None
    ):
        super().__init__()

        # the graphic owns its legend item, hold it weakly so they are not in a reference cycle
        self._graphic = weakref.ref(graphic)
        self._label = label
        self._cmap_transform_labels = cmap_transform_labels

        self._legend: Legend | None = None
        self._colorbar: ImguiColorbar | None = None
        self._elements: list[LegendElement] = list()

        # switching between uniform colors, per-vertex colors and a colormap replaces the feature
        # instance, which cannot be followed with an event, see update()
        self._colors_feature = graphic._colors
        self._cmap_feature = graphic._cmap

        self._make_item()
        self._connect()

    @property
    def graphic(self) -> Graphic | None:
        """the graphic this item represents"""
        return self._graphic()

    @property
    def legend(self) -> Legend | None:
        """the legend this item has been added to"""
        return self._legend

    @property
    def elements(self) -> tuple[LegendElement, ...]:
        """the elements of this item, empty when it is shown as a colorbar"""
        return tuple(self._elements)

    @property
    def colorbar(self) -> ImguiColorbar | None:
        """the colorbar of this item, set when the graphic uses a quantitative colormap"""
        return self._colorbar

    @property
    def label(self) -> str | None:
        """get or set the label of this item, the graphic's name is used if it is not set"""
        if self._label is not None:
            return self._label

        return self.graphic.name

    @label.setter
    def label(self, value: str | None):
        self._label = value
        self._make_item()

    @property
    def cmap_transform_labels(self) -> dict | None:
        """get or set the label of each cmap_transform value of a qualitative colormap"""
        return self._cmap_transform_labels

    @cmap_transform_labels.setter
    def cmap_transform_labels(self, labels: dict | None):
        self._cmap_transform_labels = labels
        self._make_item()

    def _fpl_add_hook(self, figure):
        super()._fpl_add_hook(figure)

        if self._colorbar is not None:
            self._colorbar._fpl_add_hook(figure)

    def _make_item(self):
        """make the colorbar or the elements that represent the graphic's current state"""
        self._colorbar = None
        self._elements = list()

        cmap = self.graphic.cmap
        if cmap is not None and cmap.interpolation != "nearest":
            # a quantitative colormap is shown as a colorbar rather than as elements
            self._colorbar = ImguiColorbar(
                graphics=self.graphic, title=self.label, height=self.COLORBAR_HEIGHT
            )
            if self._figure is not None:
                self._colorbar._fpl_add_hook(self._figure)
            return

        self._elements = self._make_elements()

    def _remake_item(self):
        """make the item again after the graphic changed"""
        try:
            self._make_item()
        except ValueError as exc:
            # the graphic changed into something the labels it has cannot represent, the user can
            # set the labels it needs now
            warn(f"the legend item of {self.graphic} cannot be made: {exc}")

    def _make_elements(self) -> list[LegendElement]:
        """the elements representing the graphic, must be implemented in subclass"""
        raise NotImplementedError

    def _get_label(self) -> str:
        """the label of the item's single element"""
        label = self.label
        if label is None:
            raise ValueError(
                "pass a `label` to `create_legend_item()`, or give the graphic a `name` to use as "
                "its legend label"
            )

        return label

    def _get_color(self) -> pygfx.Color:
        """the color an element is drawn with when it is not a colormap color itself"""
        graphic = self.graphic

        if graphic.cmap is None:
            return graphic.colors

        # a colormap has no single color, use the color of the first datapoint
        return self._get_cmap_color(graphic.cmap_transform[0])

    def _get_cmap_color(self, value: float) -> pygfx.Color:
        """the color a cmap_transform value maps onto, i.e. what the material's maprange gives it"""
        graphic = self.graphic

        vmin, vmax = graphic.cmap_range
        span = vmax - vmin

        return pygfx.Color(
            np.asarray(graphic.cmap((value - vmin) / span if span else 0.0))
        )

    def _get_cmap_colors(self) -> list[tuple[pygfx.Color, str]]:
        """(color, label) of each labelled cmap_transform value, empty without a colormap"""
        if self.graphic.cmap is None:
            return list()

        if self._cmap_transform_labels is None:
            raise ValueError(
                "a qualitative colormap needs `cmap_transform_labels`, a dict mapping each "
                "cmap_transform value onto its legend label"
            )

        return [
            (self._get_cmap_color(value), label)
            for value, label in self._cmap_transform_labels.items()
        ]

    @staticmethod
    def _get_labelled_values(
        feature, value, labels: dict, name: str
    ) -> list[tuple[Any, str]]:
        """
        (value, label) of each labelled value of a feature.

        A per-datapoint feature needs a label for each of its values. A uniform feature has the
        single ``value`` and is labelled only when ``labels`` is given.
        """
        if isinstance(feature, BufferManager):
            if labels is None:
                raise ValueError(
                    f"`{name}` is per-datapoint, pass `{name}_labels`, a dict mapping each "
                    f"{name} value onto its legend label"
                )
            return list(labels.items())

        if labels is None:
            return list()

        if value not in labels:
            raise ValueError(
                f"`{name}_labels` has no label for the graphic's {name}: {value!r}"
            )

        return [(value, labels[value])]

    @staticmethod
    def _get_feature_value(feature):
        """a feature's value, the first datapoint's value if it is per-datapoint"""
        if isinstance(feature, BufferManager):
            return feature.value[0]

        return feature.value

    def _check_vertex_colors(self) -> bool:
        """whether the graphic uses per-vertex colors, which a legend cannot represent"""
        if not isinstance(self.graphic._colors, VertexColors):
            return False

        warn(
            f"{self.graphic} uses per-vertex colors, which a legend item cannot represent. Use a "
            f"uniform color or a colormap."
        )

        return True

    def _connect(self):
        """subscribe to the events of the features the elements are made from"""
        graphic = self.graphic

        for event in (*self._events, "name", "deleted"):
            if getattr(graphic, f"_{event}", None) is None:
                # the feature does not exist in the graphic's current mode, e.g. colors while a
                # colormap is set
                continue
            graphic.add_event_handler(self._graphic_event_handler, event)

    def _disconnect(self):
        """disconnect the event handlers of the graphic"""
        graphic = self.graphic

        for event, handlers in graphic.event_handlers:
            if self._graphic_event_handler in handlers:
                graphic.remove_event_handler(self._graphic_event_handler, event)

    def _graphic_event_handler(self, ev):
        """the graphic changed, make the item again"""
        if ev.type == "deleted":
            if self._legend is not None:
                self._legend.remove(self)
            return

        self._remake_item()

    @property
    def _draws_label(self) -> bool:
        """
        whether this item draws its label above its elements, which takes whole lines

        A single element is labelled by itself, several of them are labelled by the item.
        """
        return len(self._elements) > 1 and self.label is not None

    def check_graphic_mode(self):
        """
        Make the item again if the graphic switched between uniform colors, per-vertex colors and
        a colormap, which replaces the feature instance and clears its handlers, so there is no
        event to follow. Called on each draw.
        """
        graphic = self.graphic

        if (graphic._colors is self._colors_feature) and (
            graphic._cmap is self._cmap_feature
        ):
            return

        self._colors_feature = graphic._colors
        self._cmap_feature = graphic._cmap
        self._disconnect()
        self._connect()
        self._remake_item()

    def update(self):
        draw_items([self])

    def __repr__(self) -> str:
        return f"{type(self).__name__} of {self.graphic}"


class LineLegendItem(LegendItem):
    _events = (
        "colors",
        "cmap",
        "cmap_transform",
        "cmap_range",
        "thickness",
        "dash_pattern",
    )

    def __init__(
        self,
        graphic,
        label: str = None,
        dash_pattern_labels: dict = None,
        cmap_transform_labels: dict = None,
    ):
        """
        The legend representation of a :class:`.LineGraphic`, created with
        ``LineGraphic.create_legend_item()``.
        """
        self._dash_pattern_labels = self._parse_dash_pattern_labels(dash_pattern_labels)

        super().__init__(
            graphic, label=label, cmap_transform_labels=cmap_transform_labels
        )

    @staticmethod
    def _parse_dash_pattern_labels(labels: dict | None) -> dict | None:
        """the labels keyed by the parsed dash pattern, so "--" and (5, 5) are the same key"""
        if labels is None:
            return None

        return {parse_dash_pattern(pattern): label for pattern, label in labels.items()}

    @property
    def dash_pattern_labels(self) -> dict | None:
        """get or set the label of each dash pattern"""
        return self._dash_pattern_labels

    @dash_pattern_labels.setter
    def dash_pattern_labels(self, labels: dict | None):
        self._dash_pattern_labels = self._parse_dash_pattern_labels(labels)
        self._make_item()

    def _make_elements(self) -> list[LegendElement]:
        graphic = self.graphic

        if self._check_vertex_colors():
            return list()

        color = self._get_color()
        thickness = graphic.thickness
        dash_pattern = parse_dash_pattern(graphic.dash_pattern)

        elements = [
            LineLegendElement(label, cmap_color, thickness, dash_pattern)
            for cmap_color, label in self._get_cmap_colors()
        ]

        elements += [
            LineLegendElement(label, color, thickness, value)
            for value, label in self._get_labelled_values(
                graphic._dash_pattern,
                dash_pattern,
                self._dash_pattern_labels,
                "dash_pattern",
            )
        ]

        if elements:
            return elements

        return [LineLegendElement(self._get_label(), color, thickness, dash_pattern)]


class ScatterLegendItem(LegendItem):
    _events = (
        "colors",
        "cmap",
        "cmap_transform",
        "cmap_range",
        "markers",
        "sizes",
        "edge_colors",
        "edge_width",
    )

    def __init__(
        self,
        graphic,
        label: str = None,
        markers_labels: dict = None,
        sizes_labels: dict = None,
        cmap_transform_labels: dict = None,
    ):
        """
        The legend representation of a :class:`.ScatterGraphic`, created with
        ``ScatterGraphic.create_legend_item()``.
        """
        if graphic.mode != "markers":
            raise ValueError(
                f"a legend item is only supported for a scatter with mode 'markers', the mode of "
                f"this scatter is: {graphic.mode!r}"
            )

        self._markers_labels = self._parse_markers_labels(markers_labels)
        self._sizes_labels = sizes_labels

        super().__init__(
            graphic, label=label, cmap_transform_labels=cmap_transform_labels
        )

    @staticmethod
    def _parse_markers_labels(labels: dict | None) -> dict | None:
        """the labels keyed by the pygfx marker shape name, so "o" and "circle" are the same key"""
        if labels is None:
            return None

        return {check_marker(marker): label for marker, label in labels.items()}

    @property
    def markers_labels(self) -> dict | None:
        """get or set the label of each marker"""
        return self._markers_labels

    @markers_labels.setter
    def markers_labels(self, labels: dict | None):
        self._markers_labels = self._parse_markers_labels(labels)
        self._make_item()

    @property
    def sizes_labels(self) -> dict | None:
        """get or set the label of each point size"""
        return self._sizes_labels

    @sizes_labels.setter
    def sizes_labels(self, labels: dict | None):
        self._sizes_labels = labels
        self._make_item()

    def _make_elements(self) -> list[LegendElement]:
        graphic = self.graphic

        if self._check_vertex_colors():
            return list()

        color = self._get_color()
        marker = check_marker(self._get_feature_value(graphic._markers))
        size = self._get_feature_value(graphic._sizes)
        edge_color = self._get_feature_value(graphic._edge_colors)
        edge_width = graphic.edge_width

        elements = [
            ScatterLegendElement(
                label, cmap_color, marker, size, edge_color, edge_width
            )
            for cmap_color, label in self._get_cmap_colors()
        ]

        elements += [
            ScatterLegendElement(label, color, value, size, edge_color, edge_width)
            for value, label in self._get_labelled_values(
                graphic._markers, marker, self._markers_labels, "markers"
            )
        ]

        elements += [
            ScatterLegendElement(label, color, marker, value, edge_color, edge_width)
            for value, label in self._get_labelled_values(
                graphic._sizes, size, self._sizes_labels, "sizes"
            )
        ]

        if elements:
            return elements

        return [
            ScatterLegendElement(
                self._get_label(), color, marker, size, edge_color, edge_width
            )
        ]


def get_element_width(element: LegendElement) -> float:
    """width in pixels an element needs for its swatch and its label"""
    return SWATCH_WIDTH + SWATCH_GAP + imgui.calc_text_size(element.label).x


def draw_element(element: LegendElement):
    """draw an element, its swatch and its label next to it"""
    draw_list = imgui.get_window_draw_list()
    text_height = imgui.get_text_line_height()
    height = max(text_height, element.swatch_height)

    pos = imgui.get_cursor_screen_pos()
    element.draw_swatch(draw_list, pos.x, pos.y, SWATCH_WIDTH, height)

    imgui.dummy((SWATCH_WIDTH, height))
    imgui.same_line(spacing=SWATCH_GAP)

    # center the label on the swatch
    imgui.set_cursor_pos_y(imgui.get_cursor_pos_y() + 0.5 * (height - text_height))
    imgui.text(element.label)


def draw_elements(elements: list[LegendElement], width: float):
    """
    Draw elements as a grid of columns of ``width``, as many of them as fit the width available
    where the grid starts. A wide window gets more columns and fewer rows, a narrow one gets one
    column.
    """
    if len(elements) == 0:
        return

    spacing = imgui.get_style().item_spacing.x
    available = imgui.get_content_region_avail().x

    n_columns = int((available + spacing) // (width + spacing))
    n_columns = min(max(n_columns, 1), len(elements))

    for i, element in enumerate(elements):
        column = i % n_columns
        if column:
            # every column is the same width, so they line up
            imgui.same_line(offset_from_start_x=column * (width + spacing))
        draw_element(element)


def draw_items(items: list):
    """
    Draw legend items as one grid of elements that fits the width available.

    Every element gets a cell of the same width, the widest of them all, so that the columns line
    up. The elements of the items that do not draw a label flow together into the grid, an item
    that draws its label, and a colorbar, take whole lines.
    """
    elements = [
        element
        for item in items
        if isinstance(item, LegendItem)
        for element in item.elements
    ]
    width = max((get_element_width(element) for element in elements), default=0.0)

    flowing: list[LegendElement] = list()

    for item in items:
        if isinstance(item, LegendItem):
            if item.graphic is None:
                # the graphic has been garbage collected
                continue

            item.check_graphic_mode()

            if item.colorbar is None and not item._draws_label:
                flowing += item.elements
                continue

        # anything that takes whole lines ends the run of flowing elements
        draw_elements(flowing, width)
        flowing = list()

        if isinstance(item, ImguiColorbar):
            item.draw()
        elif item.colorbar is not None:
            item.colorbar.draw()
        else:
            imgui.text(item.label)
            imgui.indent(INDENT)
            draw_elements(item.elements, width)
            imgui.unindent(INDENT)

    draw_elements(flowing, width)


class Legend(ImguiWindow):
    def __init__(self, items: list = None):
        """
        An imgui legend.

        Add the legend items of graphics and colorbars to it, imgui lays them out in the order they
        were added. A legend is an imgui window, place it with ``Figure.add_imgui_window()`` or
        ``Subplot.add_imgui_window()``.

        Parameters
        ----------
        items: list of LegendItem | ImguiColorbar, optional
            items to add to the legend

        """
        super().__init__()

        self._items: list[LegendItem | ImguiColorbar] = list()

        if items is not None:
            for item in items:
                self.add(item)

    @property
    def items(self) -> tuple:
        """the items in this legend, in the order they are drawn"""
        return tuple(self._items)

    def add(self, item: LegendItem | ImguiColorbar):
        """
        Add an item to the legend.

        Parameters
        ----------
        item: LegendItem | ImguiColorbar
            a graphic's legend item, created with ``Graphic.create_legend_item()``, or a colorbar

        """
        if not isinstance(item, (LegendItem, ImguiColorbar)):
            raise TypeError(
                f"a legend takes `LegendItem` and `ImguiColorbar` instances, you have passed a: "
                f"{type(item).__name__}"
            )

        if isinstance(item, LegendItem) and item.legend is not None:
            raise ValueError(
                "this legend item is already in a legend, a `LegendItem` can only be in one "
                "`Legend`"
            )

        self._items.append(item)

        if isinstance(item, LegendItem):
            item._legend = self

        if self._figure is not None:
            item._fpl_add_hook(self._figure)

    def remove(self, item: LegendItem | ImguiColorbar):
        """
        Remove an item from the legend, it can be added to a legend again later.

        Parameters
        ----------
        item: LegendItem | ImguiColorbar
            the item to remove

        """
        self._items.remove(item)

        if isinstance(item, LegendItem):
            item._legend = None

    def _fpl_add_hook(self, figure, **kwargs):
        # the items are drawn within this window, they need the figure too
        super()._fpl_add_hook(figure, **kwargs)

        for item in self._items:
            item._fpl_add_hook(figure)

    def update(self):
        draw_items(self._items)

    def __repr__(self) -> str:
        return f"Legend of <{len(self._items)}> items"
