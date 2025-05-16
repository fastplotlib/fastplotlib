import numpy as np
import pygfx

from ._rect import RectManager
from ._utils import IMGUI_TOOLBAR_HEIGHT
from ..utils.types import SelectorColorStates
from ..graphics import TextGraphic


"""
Each Subplot is framed by a 2D plane mesh, a rectangle.
The rectangles are viewed using the UnderlayCamera  where (0, 0) is the top left corner.
We can control the bbox of this rectangle by changing the x and y boundaries of the rectangle.

Note how the y values of the plane mesh are negative, this is because of the UnderlayCamera.
We always just keep the positive y value, and make it negative only when setting the plane mesh.

Illustration:

(0, 0) ---------------------------------------------------
----------------------------------------------------------
----------------------------------------------------------
--------------(x0, -y0) --------------- (x1, -y0) --------
------------------------|||||||||||||||-------------------
------------------------|||||||||||||||-------------------
------------------------|||||||||||||||-------------------
------------------------|||rectangle|||-------------------
------------------------|||||||||||||||-------------------
------------------------|||||||||||||||-------------------
------------------------|||||||||||||||-------------------
--------------(x0, -y1) --------------- (x1, -y1)---------
----------------------------------------------------------
------------------------------------------- (canvas_width, canvas_height)

"""


# wgsl shader snippet for SDF function that defines the resize handler, a lower right triangle.
sdf_wgsl_resize_handle = """
// hardcode square root of 2 
let m_sqrt_2 = 1.4142135;

// given a distance from an origin point, this defines the hypotenuse of a lower right triangle
let distance = (-coord.x + coord.y) / m_sqrt_2;

// return distance for this position
return distance * size;
"""


class MeshMasks:
    """Used set the x0, x1, y0, y1 positions of the plane mesh"""

    x0 = np.array(
        [
            [False, False, False],
            [True, False, False],
            [False, False, False],
            [True, False, False],
        ]
    )

    x1 = np.array(
        [
            [True, False, False],
            [False, False, False],
            [True, False, False],
            [False, False, False],
        ]
    )

    y0 = np.array(
        [
            [False, True, False],
            [False, True, False],
            [False, False, False],
            [False, False, False],
        ]
    )

    y1 = np.array(
        [
            [False, False, False],
            [False, False, False],
            [False, True, False],
            [False, True, False],
        ]
    )


masks = MeshMasks


class Frame:
    # resize handle color states
    resize_handle_color = SelectorColorStates(
        idle=(0.6, 0.6, 0.6, 1),  # gray
        highlight=(1, 1, 1, 1),  # white
        action=(1, 0, 1, 1),  # magenta
    )

    # plane color states
    plane_color = SelectorColorStates(
        idle=(0.1, 0.1, 0.1),  # dark grey
        highlight=(0.2, 0.2, 0.2),  # less dark grey
        action=(0.1, 0.1, 0.2),  # dark gray-blue
    )

    def __init__(
        self,
        viewport,
        rect,
        extent,
        resizeable,
        title,
        docks,
        toolbar_visible,
        canvas_rect,
    ):
        """
        Manages the plane mesh, resize handle point, and subplot title.
        It also sets the viewport rects for the subplot rect and the rects of the docks.

        Note: This is a backend class not meant to be user-facing.

        Parameters
        ----------
        viewport: pygfx.Viewport
            Subplot viewport

        rect: tuple | np.ndarray
            rect of this subplot

        extent: tuple | np.ndarray
            extent of this subplot

        resizeable: bool
            if the Frame is resizeable or not

        title: str
            subplot title

        docks: dict[str, PlotArea]
            subplot dock

        toolbar_visible: bool
            toolbar visibility

        canvas_rect: tuple
            figure canvas rect, the render area excluding any areas taken by imgui edge windows

        """

        self.viewport = viewport
        self.docks = docks
        self._toolbar_visible = toolbar_visible

        # create rect manager to handle all the backend rect calculations
        if rect is not None:
            self._rect_manager = RectManager(*rect, canvas_rect)
        elif extent is not None:
            self._rect_manager = RectManager.from_extent(extent, canvas_rect)
        else:
            raise ValueError("Must provide `rect` or `extent`")

        wobjects = list()

        # make title graphic
        if title is None:
            title_text = ""
        else:
            title_text = title
        self._title_graphic = TextGraphic(title_text, font_size=16, face_color="white")
        wobjects.append(self._title_graphic.world_object)

        # init mesh of size 1 to graphically represent rect
        geometry = pygfx.plane_geometry(1, 1)
        material = pygfx.MeshBasicMaterial(color=self.plane_color.idle, pick_write=True)
        self._plane = pygfx.Mesh(geometry, material)
        wobjects.append(self._plane)

        # otherwise text isn't visible
        self._plane.world.z = 0.5

        # create resize handler at point (x1, y1)
        x1, y1 = self.extent[[1, 3]]
        self._resize_handle = pygfx.Points(
            # note negative y since y is inverted in UnderlayCamera
            # subtract 7 so that the bottom right corner of the triangle is at the center
            pygfx.Geometry(positions=[[x1 - 7, -y1 + 7, 0]]),
            pygfx.PointsMarkerMaterial(
                color=self.resize_handle_color.idle,
                marker="custom",
                custom_sdf=sdf_wgsl_resize_handle,
                size=12,
                size_space="screen",
                pick_write=True,
            ),
        )

        if not resizeable:
            # set all color states to transparent if Frame isn't resizeable
            c = (0, 0, 0, 0)
            self._resize_handle.material.color = c
            self._resize_handle.material.edge_width = 0
            self.resize_handle_color = SelectorColorStates(c, c, c)

        wobjects.append(self._resize_handle)

        self._world_object = pygfx.Group()
        self._world_object.add(*wobjects)

        self._reset()
        self.reset_viewport()

    @property
    def rect_manager(self) -> RectManager:
        return self._rect_manager

    @property
    def extent(self) -> np.ndarray:
        """extent, (xmin, xmax, ymin, ymax)"""
        # not actually stored, computed when needed
        return self._rect_manager.extent

    @extent.setter
    def extent(self, extent):
        self._rect_manager.extent = extent
        self._reset()
        self.reset_viewport()

    @property
    def rect(self) -> np.ndarray[int]:
        """rect in absolute screen space, (x, y, w, h)"""
        return self._rect_manager.rect

    @rect.setter
    def rect(self, rect: np.ndarray):
        self._rect_manager.rect = rect
        self._reset()
        self.reset_viewport()

    def reset_viewport(self):
        """reset the viewport rect for the subplot and docks"""

        # get rect of the render area
        x, y, w, h = self.get_render_rect()

        # dock sizes
        s_left = self.docks["left"].size
        s_top = self.docks["top"].size
        s_right = self.docks["right"].size
        s_bottom = self.docks["bottom"].size

        # top and bottom have same width
        # subtract left and right dock sizes
        w_top_bottom = w - s_left - s_right
        # top and bottom have same x pos
        x_top_bottom = x + s_left

        # set dock rects
        self.docks["left"].viewport.rect = x, y, s_left, h
        self.docks["top"].viewport.rect = x_top_bottom, y, w_top_bottom, s_top
        self.docks["bottom"].viewport.rect = (
            x_top_bottom,
            y + h - s_bottom,
            w_top_bottom,
            s_bottom,
        )
        self.docks["right"].viewport.rect = x + w - s_right, y, s_right, h

        # calc subplot rect by adjusting for dock sizes
        x += s_left
        y += s_top
        w -= s_left + s_right
        h -= s_top + s_bottom

        # set subplot rect
        self.viewport.rect = x, y, w, h

    def get_render_rect(self) -> tuple[float, float, float, float]:
        """
        Get the actual render area of the subplot, including the docks.

        Excludes area taken by the subplot title and toolbar. Also adds a small amount of spacing around the subplot.
        """
        # the rect of the entire Frame
        x, y, w, h = self.rect

        x += 1  # add 1 so a 1 pixel edge is visible
        w -= 2  # subtract 2, so we get a 1 pixel edge on both sides

        # add 4 pixels above and below title for better spacing
        y = y + 4 + self._title_graphic.font_size + 4

        # spacing on the bottom if imgui toolbar is visible
        if self.toolbar_visible:
            toolbar_space = IMGUI_TOOLBAR_HEIGHT
            resize_handle_space = 0
        else:
            toolbar_space = 0
            # need some space for resize handler if imgui toolbar isn't present
            resize_handle_space = 13

        # adjust for the 4 pixels from the line above
        # also give space for resize handler if imgui toolbar is not present
        h = (
            h
            - 4
            - self._title_graphic.font_size
            - toolbar_space
            - 4
            - resize_handle_space
        )

        return x, y, w, h

    def _reset(self):
        """reset the plane mesh using the current rect state"""

        x0, x1, y0, y1 = self._rect_manager.extent
        w = self._rect_manager.w

        self._plane.geometry.positions.data[masks.x0] = x0
        self._plane.geometry.positions.data[masks.x1] = x1

        # negative y because UnderlayCamera y is inverted
        self._plane.geometry.positions.data[masks.y0] = -y0
        self._plane.geometry.positions.data[masks.y1] = -y1

        self._plane.geometry.positions.update_full()

        # note negative y since y is inverted in UnderlayCamera
        # subtract 7 so that the bottom right corner of the triangle is at the center
        self._resize_handle.geometry.positions.data[0] = [x1 - 7, -y1 + 7, 0]
        self._resize_handle.geometry.positions.update_full()

        # set subplot title position
        x = x0 + (w / 2)
        y = y0 + (self._title_graphic.font_size / 2)
        self._title_graphic.world_object.world.x = x
        self._title_graphic.world_object.world.y = -y - 4  # add 4 pixels for spacing

    @property
    def toolbar_visible(self) -> bool:
        return self._toolbar_visible

    @toolbar_visible.setter
    def toolbar_visible(self, visible: bool):
        self._toolbar_visible = visible
        self.reset_viewport()

    @property
    def title_graphic(self) -> TextGraphic:
        return self._title_graphic

    @property
    def plane(self) -> pygfx.Mesh:
        """the plane mesh"""
        return self._plane

    @property
    def resize_handle(self) -> pygfx.Points:
        """resize handler point"""
        return self._resize_handle

    def canvas_resized(self, canvas_rect):
        """called by layout is resized"""
        self._rect_manager.canvas_resized(canvas_rect)
        self._reset()
        self.reset_viewport()
