import numpy as np

import pygfx


GRID_PLANES = ["xy", "xz", "yz"]


# very thin subclass that just adds GridMaterial properties to this world object for easier user control
class Grid(pygfx.Grid):
    @property
    def major_step(self) -> tuple[float, float]:
        """The step distance between the major grid lines."""
        return self.material.major_step

    @major_step.setter
    def major_step(self, step: tuple[float, float]):
        self.material.major_step = step

    @property
    def minor_step(self) -> tuple[float, float]:
        """The step distance between the minor grid lines."""
        return self.material.minor_step

    @minor_step.setter
    def minor_step(self, step: tuple[float, float]):
        self.material.minor_step = step

    @property
    def axis_thickness(self) -> float:
        """The thickness of the axis lines."""
        return self.material.axis_thickness

    @axis_thickness.setter
    def axis_thickness(self, thickness: float):
        self.material.axis_thickness = thickness

    @property
    def major_thickness(self) -> float:
        """The thickness of the major grid lines."""
        return self.material.major_thickness

    @major_thickness.setter
    def major_thickness(self, thickness: float):
        self.material.major_thickness = thickness

    @property
    def minor_thickness(self) -> float:
        """The thickness of the minor grid lines."""
        return self.material.minor_thickness

    @minor_thickness.setter
    def minor_thickness(self, thickness: float):
        self.material.minor_thickness = thickness

    @property
    def thickness_space(self) -> str:
        """The coordinate space in which the thicknesses are expressed.

        See :obj:`pygfx.utils.enums.CoordSpace`:
        """
        return self.material.thickness_space

    @thickness_space.setter
    def thickness_space(self, value: str):
        self.material.thickness_space = value

    @property
    def axis_color(self) -> str:
        """The color of the axis lines."""
        return self.material.axis_color

    @axis_color.setter
    def axis_color(self, color: str):
        self.material.axis_color = color

    @property
    def major_color(self) -> str:
        """The color of the major grid lines."""
        return self.material.major_color

    @major_color.setter
    def major_color(self, color: str):
        self.material.major_color = color

    @property
    def minor_color(self) -> str:
        """The color of the minor grid lines."""
        return self.material.minor_color

    @minor_color.setter
    def minor_color(self, color: str):
        self.material.minor_color = color

    @property
    def infinite(self) -> bool:
        """Whether the grid is infinite.

        If not infinite, the grid is 1x1 in world space, scaled, rotated, and
        positioned with the object's transform.

        (Infinite grids are not actually infinite. Rather they move along with
        the camera, and are sized based on the distance between the camera and
        the grid.)
        """
        return self.material.infinite

    @infinite.setter
    def infinite(self, value: str):
        self.material.infinite = value


class Grids(pygfx.Group):
    """Just a class to make accessing the grids easier"""
    def __init__(self, *, xy, xz, yz):
        super().__init__()

        self._xy = xy
        self._xz = xz
        self._yz = yz

        self.add(xy, xz, yz)

    @property
    def xy(self) -> Grid:
        """xy grid"""
        return self._xy

    @property
    def xz(self) -> Grid:
        """xz grid"""
        return self._xz

    @property
    def yz(self) -> Grid:
        """yz grid"""
        return self._yz


class Axes:
    def __init__(
            self,
            plot_area,
            follow: bool = True,
            x_kwargs: dict = None,
            y_kwargs: dict = None,
            z_kwargs: dict = None,
            grids: bool = True,
            grid_kwargs: dict = None,
            auto_grid: bool = True,
            offset: np.ndarray = np.array([0., 0., 0.])
    ):
        self._plot_area = plot_area

        if x_kwargs is None:
            x_kwargs = dict()

        if y_kwargs is None:
            y_kwargs = dict()

        if z_kwargs is None:
            z_kwargs = dict()

        x_kwargs = {
            "tick_side": "right",
            **x_kwargs,
        }

        y_kwargs = {
            "tick_side": "left",
            **y_kwargs
        }

        z_kwargs = {
            "tick_side": "left",
            **z_kwargs,
        }

        # create ruler for each dim
        self._x = pygfx.Ruler(**x_kwargs)
        self._y = pygfx.Ruler(**y_kwargs)
        self._z = pygfx.Ruler(**z_kwargs)

        self._offset = offset

        # *MUST* instantiate some start and end positions for the rulers else kernel crashes immediately
        # probably a WGPU rust panic
        self.x.start_pos = 0, 0, 0
        self.x.end_pos = 100, 0, 0
        self.x.start_value = self.x.start_pos[0] - offset[0]
        statsx = self.x.update(self._plot_area.camera, self._plot_area.viewport.logical_size)

        self.y.start_pos = 0, 0, 0
        self.y.end_pos = 0, 100, 0
        self.y.start_value = self.y.start_pos[1] - offset[1]
        statsy = self.y.update(self._plot_area.camera, self._plot_area.viewport.logical_size)

        self.z.start_pos = 0, 0, 0
        self.z.end_pos = 0, 0, 100
        self.z.start_value = self.z.start_pos[1] - offset[2]
        self.z.update(self._plot_area.camera, self._plot_area.viewport.logical_size)

        # world object for the rulers + grids
        self._world_object = pygfx.Group()

        # add rulers
        self.world_object.add(
            self.x,
            self.y,
            self._z,
        )

        # set z ruler invisible for orthographic projections for now
        if self._plot_area.camera.fov == 0:
            # TODO: allow any orientation in the future even for orthographic projections
            self.z.visible = False

        if grid_kwargs is None:
            grid_kwargs = dict()

        grid_kwargs = {
            "major_step": 10,
            "minor_step": 1,
            "thickness_space": "screen",
            "major_thickness": 2,
            "minor_thickness": 0.5,
            "infinite": True,
            **grid_kwargs
        }

        if grids:
            _grids = dict()
            for plane in GRID_PLANES:
                grid = Grid(
                    geometry=None,
                    material=pygfx.GridMaterial(**grid_kwargs),
                    orientation=plane,
                )

                _grids[plane] = grid

            self._grids = Grids(**_grids)
            self.world_object.add(self._grids)

            if self._plot_area.camera.fov == 0:
                # orthographic projection, place grids far away
                self._grids.local.z = -1000

            major_step_x, major_step_y = statsx["tick_step"], statsy["tick_step"]

            self.grids.xy.material.major_step = major_step_x, major_step_y
            self.grids.xy.material.minor_step = 0.2 * major_step_x, 0.2 * major_step_y

        else:
            self._grids = False

        self._follow = follow
        self._auto_grid = auto_grid

    @property
    def world_object(self) -> pygfx.WorldObject:
        return self._world_object

    @property
    def offset(self) -> np.ndarray:
        """offset of the axes"""
        return self._offset

    @offset.setter
    def offset(self, value: np.ndarray):
        self._offset = value

    @property
    def x(self) -> pygfx.Ruler:
        """x axis ruler"""
        return self._x

    @property
    def y(self) -> pygfx.Ruler:
        """y axis ruler"""
        return self._y

    @property
    def z(self) -> pygfx.Ruler:
        """z axis ruler"""
        return self._z

    @property
    def grids(self) -> Grids | bool:
        """grids for each plane: xy, xz, yz"""
        return self._grids

    @property
    def auto_grid(self) -> bool:
        """auto adjust the grid on each render cycle"""
        return self._auto_grid

    @auto_grid.setter
    def auto_grid(self, value: bool):
        self._auto_grid = value

    @property
    def visible(self) -> bool:
        """set visibility of all axes elements, rulers and grids"""
        return self._world_object.visible

    @visible.setter
    def visible(self, value: bool):
        self._world_object.visible = value

    @property
    def follow(self) -> bool:
        """if True, axes will follow during pan-zoom movements, only for orthographic projections"""
        return self._follow

    @follow.setter
    def follow(self, value: bool):
        if not isinstance(value, bool):
            raise TypeError
        self._follow = value

    def update_bounded(self, bbox):
        """update the axes using the given bbox"""
        self._update(bbox, (0, 0, 0))

    def auto_update(self):
        """
        Auto update the axes

        For orthographic projections of the xy plane, it will calculate the inverse projection
        of the screen space onto world space to determine the current range of the world space
        to set the rulers and ticks

        For perspective projetions it will just use the bbox of the scene to set the rulers

        """

        rect = self._plot_area.get_rect()

        if self._plot_area.camera.fov == 0:
            # orthographic projection, get ranges using inverse

            # get range of screen space
            xmin, xmax = rect[0], rect[2]
            ymin, ymax = rect[3], rect[1]

            world_xmin, world_ymin, _ = self._plot_area.map_screen_to_world((xmin, ymin))
            world_xmax, world_ymax, _ = self._plot_area.map_screen_to_world((xmax, ymax))

            world_zmin, world_zmax = 0, 0

            bbox = np.array([
                [world_xmin, world_ymin, world_zmin],
                [world_xmax, world_ymax, world_zmax]
            ])
        else:
            # set ruler start and end positions based on scene bbox
            bbox = self._plot_area._fpl_graphics_scene.get_world_bounding_box()

        if self.follow and self._plot_area.camera.fov == 0:
            # place the ruler close to the left and bottom edges of the viewport
            # TODO: determine this for perspective projections
            xscreen_10, yscreen_10 = 0.1 * rect[2], 0.9 * rect[3]
            edge_positions = self._plot_area.map_screen_to_world((xscreen_10, yscreen_10))

        else:
            # axes intersect at the origin
            edge_positions = 0, 0, 0

        self._update(bbox, edge_positions)

    def _update(self, bbox, ruler_intersection_point):
        """update the axes using the given bbox and ruler intersection point"""

        world_xmin, world_ymin, world_zmin = bbox[0]
        world_xmax, world_ymax, world_zmax = bbox[1]
        world_x_10, world_y_10, world_z_10 = ruler_intersection_point

        # swap min and max for each dimension if necessary
        if self._plot_area.camera.local.scale_y < 0:
            world_ymin, world_ymax = world_ymax, world_ymin
            self.y.tick_side = "right"  # swap tick side
            self.x.tick_side = "left"
        else:
            self.y.tick_side = "left"
            self.x.tick_side = "right"

        if self._plot_area.camera.local.scale_x < 0:
            world_xmin, world_xmax = world_xmax, world_xmin
            self.x.tick_side = "left"

        self.x.start_pos = world_xmin, world_y_10, world_z_10
        self.x.end_pos = world_xmax, world_y_10, world_z_10

        self.x.start_value = self.x.start_pos[0] - self.offset[0]
        statsx = self.x.update(self._plot_area.camera, self._plot_area.viewport.logical_size)

        self.y.start_pos = world_x_10, world_ymin, world_z_10
        self.y.end_pos = world_x_10, world_ymax, world_z_10

        self.y.start_value = self.y.start_pos[1] - self.offset[1]
        statsy = self.y.update(self._plot_area.camera, self._plot_area.viewport.logical_size)

        if self._plot_area.camera.fov != 0:
            self.z.start_pos = world_x_10, world_y_10, world_zmin
            self.z.end_pos = world_x_10, world_y_10, world_zmax

            self.z.start_value = self.z.start_pos[1] - self.offset[2]
            statsz = self.z.update(self._plot_area.camera, self._plot_area.viewport.logical_size)
            major_step_z = statsz["tick_step"]

        if self.grids:
            if self.auto_grid:
                major_step_x, major_step_y = statsx["tick_step"], statsy["tick_step"]
                self.grids.xy.major_step = major_step_x, major_step_y
                self.grids.xy.minor_step = 0.2 * major_step_x, 0.2 * major_step_y

            if self._plot_area.camera.fov != 0:
                self.grids.xz.major_step = major_step_x, major_step_z
                self.grids.xz.minor_step = 0.2 * major_step_x, 0.2 * major_step_z

                self.grids.yz.material.major_step = major_step_y, major_step_z
                self.grids.yz.minor_step = 0.2 * major_step_y, 0.2 * major_step_z
