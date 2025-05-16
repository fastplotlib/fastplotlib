import numpy as np


class RectManager:
    """
    Backend management of a rect. Allows converting between rects and extents, also works with fractional inputs.
    """

    def __init__(self, x: float, y: float, w: float, h: float, canvas_rect: tuple):
        # initialize rect state arrays
        # used to store internal state of the rect in both fractional screen space and absolute screen space
        # the purpose of storing the fractional rect is that it remains constant when the canvas resizes
        self._rect_frac = np.zeros(4, dtype=np.float64)
        self._rect_screen_space = np.zeros(4, dtype=np.float64)
        self._canvas_rect = np.asarray(canvas_rect)

        self._set((x, y, w, h))

    def _set(self, rect):
        """
        Using the passed rect which is either absolute screen space or fractional,
        set the internal fractional and absolute screen space rects
        """
        rect = np.asarray(rect)
        for val, name in zip(rect, ["x-position", "y-position", "width", "height"]):
            if val < 0:
                raise ValueError(
                    f"Invalid rect value < 0: {rect}\n All values must be non-negative."
                )

        if (rect[2:] <= 1).all():  # fractional bbox
            self._set_from_fract(rect)

        elif (rect[2:] > 1).all():  # bbox in already in screen coords coordinates
            self._set_from_screen_space(rect)

        else:
            raise ValueError(f"Invalid rect: {rect}")

    def _set_from_fract(self, rect):
        """set rect from fractional representation"""
        _, _, cw, ch = self._canvas_rect
        mult = np.array([cw, ch, cw, ch])

        # check that widths, heights are valid:
        if rect[0] + rect[2] > 1:
            raise ValueError(
                f"invalid fractional rect: {rect}\n x + width > 1: {rect[0]} + {rect[2]} > 1"
            )
        if rect[1] + rect[3] > 1:
            raise ValueError(
                f"invalid fractional rect: {rect}\n y + height > 1: {rect[1]} + {rect[3]} > 1"
            )

        # assign values to the arrays, don't just change the reference
        self._rect_frac[:] = rect
        self._rect_screen_space[:] = self._rect_frac * mult

    def _set_from_screen_space(self, rect):
        """set rect from screen space representation"""
        _, _, cw, ch = self._canvas_rect
        mult = np.array([cw, ch, cw, ch])
        # for screen coords allow (x, y) = 1 or 0, but w, h must be > 1
        # check that widths, heights are valid
        if rect[0] + rect[2] > cw:
            raise ValueError(
                f"invalid rect: {rect}\n x + width > canvas width: {rect[0]} + {rect[2]} > {cw}"
            )
        if rect[1] + rect[3] > ch:
            raise ValueError(
                f"invalid rect: {rect}\n y + height > canvas height: {rect[1]} + {rect[3]} >{ch}"
            )

        self._rect_frac[:] = rect / mult
        self._rect_screen_space[:] = rect

    @property
    def x(self) -> np.float64:
        """x position"""
        return self._rect_screen_space[0]

    @property
    def y(self) -> np.float64:
        """y position"""
        return self._rect_screen_space[1]

    @property
    def w(self) -> np.float64:
        """width"""
        return self._rect_screen_space[2]

    @property
    def h(self) -> np.float64:
        """height"""
        return self._rect_screen_space[3]

    @property
    def rect(self) -> np.ndarray:
        """rect, (x, y, w, h)"""
        return self._rect_screen_space

    @rect.setter
    def rect(self, rect: np.ndarray | tuple):
        self._set(rect)

    def canvas_resized(self, canvas_rect: tuple):
        # called by Frame when canvas is resized
        self._canvas_rect[:] = canvas_rect
        # set new rect using existing rect_frac since this remains constant regardless of resize
        self._set(self._rect_frac)

    @property
    def x0(self) -> np.float64:
        """x0 position"""
        return self.x

    @property
    def x1(self) -> np.float64:
        """x1 position"""
        return self.x + self.w

    @property
    def y0(self) -> np.float64:
        """y0 position"""
        return self.y

    @property
    def y1(self) -> np.float64:
        """y1 position"""
        return self.y + self.h

    @classmethod
    def from_extent(cls, extent, canvas_rect):
        """create a RectManager from an extent"""
        rect = cls.extent_to_rect(extent, canvas_rect)
        return cls(*rect, canvas_rect)

    @property
    def extent(self) -> np.ndarray:
        """extent, (xmin, xmax, ymin, ymax)"""
        # not actually stored, computed when needed
        return np.asarray([self.x0, self.x1, self.y0, self.y1])

    @extent.setter
    def extent(self, extent):
        rect = RectManager.extent_to_rect(extent, canvas_rect=self._canvas_rect)

        self._set(rect)

    @staticmethod
    def extent_to_rect(extent, canvas_rect):
        """convert an extent to a rect"""
        RectManager.validate_extent(extent, canvas_rect)
        x0, x1, y0, y1 = extent

        # width and height
        w = x1 - x0
        h = y1 - y0

        return x0, y0, w, h

    @staticmethod
    def validate_extent(extent: np.ndarray | tuple, canvas_rect: tuple):
        extent = np.asarray(extent)
        cx0, cy0, cw, ch = canvas_rect

        # make sure extent is valid
        if (extent < 0).any():
            raise ValueError(f"extent must be non-negative, you have passed: {extent}")

        if extent[1] <= 1 or extent[3] <= 1:  # if x1 <= 1, or y1 <= 1
            # if fractional rect, convert to full
            if not (extent <= 1).all():  # if x1 and y1 <= 1, then all vals must be <= 1
                raise ValueError(
                    f"if passing a fractional extent, all values must be fractional, you have passed: {extent}"
                )
            extent *= np.asarray([cw, cw, ch, ch])

        x0, x1, y0, y1 = extent

        # width and height
        w = x1 - x0
        h = y1 - y0

        # check if x1 - x0 <= 0
        if w <= 0:
            raise ValueError(f"extent x-range must be non-negative: {extent}")

        # check if y1 - y0 <= 0
        if h <= 0:
            raise ValueError(f"extent y-range must be non-negative: {extent}")

        # calc canvas extent
        cx1 = cx0 + cw
        cy1 = cy0 + ch
        canvas_extent = np.asarray([cx0, cx1, cy0, cy1])

        if x0 < cx0 or x1 < cx0 or x0 > cx1 or x1 > cx1:
            raise ValueError(
                f"extent: {extent} x-range is beyond the bounds of the canvas: {canvas_extent}"
            )
        if y0 < cy0 or y1 < cy0 or y0 > cy1 or y1 > cy1:
            raise ValueError(
                f"extent: {extent} y-range is beyond the bounds of the canvas: {canvas_extent}"
            )

    def is_above(self, y0, dist: int = 1) -> bool:
        # our bottom < other top within given distance
        return self.y1 < y0 + dist

    def is_below(self, y1, dist: int = 1) -> bool:
        # our top > other bottom
        return self.y0 > y1 - dist

    def is_left_of(self, x0, dist: int = 1) -> bool:
        # our right_edge < other left_edge
        # self.x1 < other.x0
        return self.x1 < x0 + dist

    def is_right_of(self, x1, dist: int = 1) -> bool:
        # self.x0 > other.x1
        return self.x0 > x1 - dist

    def overlaps(self, extent: np.ndarray) -> bool:
        """returns whether this rect overlaps with the given extent"""
        x0, x1, y0, y1 = extent
        return not any(
            [
                self.is_above(y0),
                self.is_below(y1),
                self.is_left_of(x0),
                self.is_right_of(x1),
            ]
        )

    def __repr__(self):
        s = f"{self._rect_frac}\n{self.rect}"

        return s
