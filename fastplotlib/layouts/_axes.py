import pygfx


# very thin subclass that just adds GridMaterial properties to this world object for easier user control
class Grid(pygfx.Grid):
    @property
    def major_step(self):
        """The step distance between the major grid lines."""
        return self.material.major_step

    @major_step.setter
    def major_step(self, step):
        self.material.major_step = step

    @property
    def minor_step(self):
        """The step distance between the minor grid lines."""
        return self.material.minor_step

    @minor_step.setter
    def minor_step(self, step):
        self.material.minor_step = step

    @property
    def axis_thickness(self):
        """The thickness of the axis lines."""
        return self.material.axis_thickness

    @axis_thickness.setter
    def axis_thickness(self, thickness):
        self.material.axis_thickness = thickness

    @property
    def major_thickness(self):
        """The thickness of the major grid lines."""
        return self.material.major_thickness

    @major_thickness.setter
    def major_thickness(self, thickness):
        self.material.major_thickness = thickness

    @property
    def minor_thickness(self):
        """The thickness of the minor grid lines."""
        return self.material.minor_thickness

    @minor_thickness.setter
    def minor_thickness(self, thickness):
        self.material.minor_thickness = thickness

    @property
    def thickness_space(self):
        """The coordinate space in which the thicknesses are expressed.

        See :obj:`pygfx.utils.enums.CoordSpace`:
        """
        return self.material.thickness_space

    @thickness_space.setter
    def thickness_space(self, value):
        self.material.thickness_space = value

    @property
    def axis_color(self):
        """The color of the axis lines."""
        return self.material.axis_color

    @axis_color.setter
    def axis_color(self, color):
        self.material.axis_color = color

    @property
    def major_color(self):
        """The color of the major grid lines."""
        return self.material.major_color

    @major_color.setter
    def major_color(self, color):
        self.material.major_color = color

    @property
    def minor_color(self):
        """The color of the minor grid lines."""
        return self.material.minor_color

    @minor_color.setter
    def minor_color(self, color):
        self.material.minor_color = color

    @property
    def infinite(self):
        """Whether the grid is infinite.

        If not infinite, the grid is 1x1 in world space, scaled, rotated, and
        positioned with the object's transform.

        (Infinite grids are not actually infinite. Rather they move along with
        the camera, and are sized based on the distance between the camera and
        the grid.)
        """
        return self.material.infinite

    @infinite.setter
    def infinite(self, value):
        self.material.infinite = value


class Axes:
    def __init__(
            self,
            plot_area,
            follow: bool = True,
            x_kwargs: dict = None,
            y_kwargs: dict = None,
            z_kwargs: dict = None,
            grid_kwargs: dict = None,
            auto_grid: bool = True,
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

        # z_kwargs = {
        #     "tick_side": "left",
        #     **z_kwargs,
        # }

        self._x = pygfx.Ruler(**x_kwargs)
        self._y = pygfx.Ruler(**y_kwargs)
        # self._z = pygfx.Ruler(**z_kwargs)

        # *MUST* instantiate some start and end positions for the rulers else kernel crashes immediately
        # probably a WGPU rust panic
        self.x.start_pos = self._plot_area.camera.world.x - self._plot_area.camera.width / 2, 0, -1000
        self.x.end_pos = self._plot_area.camera.world.x + self._plot_area.camera.width / 2, 0, -1000
        self.x.start_value = self.x.start_pos[0]
        statsx = self.x.update(self._plot_area.camera, self._plot_area.canvas.get_logical_size())

        self.y.start_pos = 0, self._plot_area.camera.world.y - self._plot_area.camera.height / 2, -1000
        self.y.end_pos = 0, self._plot_area.camera.world.y + self._plot_area.camera.height / 2, -1000
        self.y.start_value = self.y.start_pos[1]
        statsy = self.y.update(self._plot_area.camera, self._plot_area.canvas.get_logical_size())

        self._world_object = pygfx.Group()
        self.world_object.add(
            self.x,
            self.y,
            # self._z,
        )

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

        self._grids = dict()

        for plane in ["xy", "xz", "yz"]:
            self._grids[plane] = Grid(
                geometry=None,
                material=pygfx.GridMaterial(**grid_kwargs),
                orientation=plane,
            )

            self._grids[plane].local.z = -1001

            self.world_object.add(self._grids[plane])

        major_step_x, major_step_y = statsx["tick_step"], statsy["tick_step"]

        if "xy" in self.grids.keys():
            self.grids["xy"].material.major_step = major_step_x, major_step_y
            self.grids["xy"].material.minor_step = 0.2 * major_step_x, 0.2 * major_step_y

        self._follow = follow
        self._auto_grid = auto_grid

    @property
    def world_object(self) -> pygfx.WorldObject:
        return self._world_object

    @property
    def x(self) -> pygfx.Ruler:
        """x axis ruler"""
        return self._x

    @property
    def y(self) -> pygfx.Ruler:
        """y axis ruler"""
        return self._y
    #
    # @property
    # def z(self) -> pygfx.Ruler:
    #     return self._z
    #
    @property
    def grids(self) -> dict[str, pygfx.Grid]:
        """grids for each plane if present: 'xy', 'xz', 'yz'"""
        return self._grids

    @property
    def auto_grid(self) -> bool:
        return self._auto_grid

    @auto_grid.setter
    def auto_grid(self, value: bool):
        self._auto_grid = value

    @property
    def visible(self) -> bool:
        return self._world_object.visible

    @visible.setter
    def visible(self, value: bool):
        self._world_object.visible = value

    @property
    def follow(self) -> bool:
        return self._follow

    @follow.setter
    def follow(self, value: bool):
        if not isinstance(value, bool):
            raise TypeError
        self._follow = value

    def animate(self):
        # TODO: figure out z
        rect = self._plot_area.get_rect()

        # get range of screen space
        xmin, xmax = rect[0], rect[2]
        ymin, ymax = rect[3], rect[1]

        world_xmin, world_ymin, _ = self._plot_area.map_screen_to_world((xmin, ymin))
        world_xmax, world_ymax, _ = self._plot_area.map_screen_to_world((xmax, ymax))

        if self.follow:
            # place the ruler close to the left and bottom edges of the viewport
            xscreen_10, yscreen_10 = 0.1 * rect[2], 0.9 * rect[3]
            world_x_10, world_y_10, _ = self._plot_area.map_screen_to_world((xscreen_10, yscreen_10))

        else:
            # axes intersect at the origin
            world_x_10, world_y_10 = 0, 0

        # swap min and max for each dimension if necessary
        if self._plot_area.camera.local.scale_y < 0:
            world_ymin, world_ymax = world_ymax, world_ymin

        if self._plot_area.camera.local.scale_x < 0:
            world_xmin, world_xmax = world_xmax, world_xmin

        self.x.start_pos = world_xmin, world_y_10, -1000
        self.x.end_pos = world_xmax, world_y_10, -1000

        self.x.start_value = self.x.start_pos[0]
        statsx = self.x.update(self._plot_area.camera, self._plot_area.canvas.get_logical_size())

        self.y.start_pos = world_x_10, world_ymin, -1000
        self.y.end_pos = world_x_10, world_ymax, -1000

        self.y.start_value = self.y.start_pos[1]
        statsy = self.y.update(self._plot_area.camera, self._plot_area.canvas.get_logical_size())

        if self.auto_grid:
            major_step_x, major_step_y = statsx["tick_step"], statsy["tick_step"]

            if "xy" in self.grids.keys():
                self.grids["xy"].material.major_step = major_step_x, major_step_y
                self.grids["xy"].material.minor_step = 0.2 * major_step_x, 0.2 * major_step_y
