import numpy as np

import pygfx
from pylinalg import quat_from_vecs, vec_transform_quat


GRID_PLANES = ["xy", "xz", "yz"]

CANONICAL_BAIS = np.array([
    [1., 0., 0.],
    [0., 1., 0.],
    [0., 0., 1.]
])


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


class Ruler(pygfx.Ruler):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.tick_text_mapper = None
        self.font_size = 14

    def _update_sub_objects(self, ticks, tick_auto_step):
        """Update the sub-objects to show the given ticks."""
        assert isinstance(ticks, dict)

        tick_size = 5
        min_n_slots = 8  # todo: can be (much) higher when we use a single text object!

        # Load config
        start_pos = self._start_pos
        end_pos = self._end_pos
        start_value = self._start_value
        end_value = self.end_value

        # Derive some more variables
        length = end_value - start_value
        vec = end_pos - start_pos
        if length:
            vec /= length

        # Get array to store positions
        n_slots = self.points.geometry.positions.nitems
        n_positions = len(ticks) + 2
        if n_positions <= n_slots <= max(min_n_slots, 2 * n_positions):
            # Re-use existing buffers
            positions = self.points.geometry.positions.data
            sizes = self.points.geometry.sizes.data
            self.points.geometry.positions.update_range()
            self.points.geometry.sizes.update_range()
        else:
            # Allocate new buffers
            new_n_slots = max(min_n_slots, int(n_positions * 1.2))
            positions = np.zeros((new_n_slots, 3), np.float32)
            sizes = np.zeros((new_n_slots,), np.float32)
            self.points.geometry.positions = pygfx.Buffer(positions)
            self.points.geometry.sizes = pygfx.Buffer(sizes)
            # Allocate text objects
            while len(self._text_object_pool) < new_n_slots:
                ob = pygfx.Text(
                    pygfx.TextGeometry("", screen_space=True, font_size=self.font_size),
                    pygfx.TextMaterial(aa=False),
                )
                self._text_object_pool.append(ob)
            self._text_object_pool[new_n_slots:] = []
            # Reset children
            self.clear()
            self.add(self._line, self._points, *self._text_object_pool)

        def define_text(pos, text):
            if self.tick_text_mapper is not None and text != "":
                text = self.tick_text_mapper(text)

            ob = self._text_object_pool[index]
            ob.geometry.anchor = self._text_anchor
            ob.geometry.anchor_offset = self._text_anchor_offset
            ob.geometry.set_text(text)
            ob.local.position = pos

        # Apply start point
        index = 0
        positions[0] = start_pos
        if self._ticks_at_end_points:
            sizes[0] = tick_size
            define_text(start_pos, f"{self._start_value:0.4g}")
        else:
            sizes[0] = 0
            define_text(start_pos, f"")

        # Collect ticks
        index += 1
        for value, text in ticks.items():
            pos = start_pos + vec * (value - start_value)
            positions[index] = pos
            sizes[index] = tick_size
            define_text(pos, text)
            index += 1

        # Handle end point, and nullify remaining slots
        positions[index:] = end_pos
        sizes[index:] = 0
        for ob in self._text_object_pool[index:]:
            ob.geometry.set_text("")

        # Show last tick?
        if self._ticks_at_end_points:
            sizes[index] = tick_size
            define_text(end_pos, f"{end_value:0.4g}")

        # Hide the ticks close to the ends?
        if self._ticks_at_end_points and ticks:
            tick_values = list(ticks.keys())
            if abs(tick_values[0] - start_value) < 0.5 * tick_auto_step:
                self._text_object_pool[1].geometry.set_text("")
            if abs(tick_values[-1] - end_value) < 0.5 * tick_auto_step:
                self._text_object_pool[index - 1].geometry.set_text("")


class Axes:
    def __init__(
        self,
        plot_area,
        intersection: tuple[int, int, int] | None = None,
        x_kwargs: dict = None,
        y_kwargs: dict = None,
        z_kwargs: dict = None,
        grids: bool = True,
        grid_kwargs: dict = None,
        auto_grid: bool = True,
        offset: np.ndarray = np.array([0.0, 0.0, 0.0]),
        basis: np.ndarray = np.array([[1., 0., 0.], [0., 1., 0.], [0., 0., 1.]])
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

        y_kwargs = {"tick_side": "left", **y_kwargs}

        z_kwargs = {
            "tick_side": "left",
            **z_kwargs,
        }

        # create ruler for each dim
        self._x = Ruler(**x_kwargs)
        self._y = Ruler(**y_kwargs)
        self._z = Ruler(**z_kwargs)

        self._offset = offset

        # *MUST* instantiate some start and end positions for the rulers else kernel crashes immediately
        # probably a WGPU rust panic
        self.x.start_pos = 0, 0, 0
        self.x.end_pos = 100, 0, 0
        self.x.start_value = self.x.start_pos[0] - offset[0]
        statsx = self.x.update(
            self._plot_area.camera, self._plot_area.viewport.logical_size
        )

        self.y.start_pos = 0, 0, 0
        self.y.end_pos = 0, 100, 0
        self.y.start_value = self.y.start_pos[1] - offset[1]
        statsy = self.y.update(
            self._plot_area.camera, self._plot_area.viewport.logical_size
        )

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
            self.z,
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
            **grid_kwargs,
        }

        if grids:
            _grids = dict()
            for plane in GRID_PLANES:
                grid = Grid(
                    geometry=None,
                    material=pygfx.GridMaterial(**grid_kwargs),
                    orientation=plane,
                    visible=False,
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

        self._intersection = intersection
        self._auto_grid = auto_grid

        self._basis = None
        self.basis = basis

    @property
    def world_object(self) -> pygfx.WorldObject:
        return self._world_object

    @property
    def basis(self) -> np.ndarray:
        """get or set the basis, shape is [3, 3]"""
        return self._basis

    @basis.setter
    def basis(self, basis: np.ndarray):
        if basis.shape != (3, 3):
            raise ValueError

        # apply quaternion to each of x, y, z rulers
        for dim, cbasis, new_basis in zip(["x", "y", "z"], CANONICAL_BAIS, basis):
            ruler: pygfx.Ruler = getattr(self, dim)
            ruler.local.rotation = quat_from_vecs(cbasis, new_basis)

    @property
    def offset(self) -> np.ndarray:
        """offset of the axes"""
        return self._offset

    @offset.setter
    def offset(self, value: np.ndarray):
        self._offset = value

    @property
    def x(self) -> Ruler:
        """x axis ruler"""
        return self._x

    @property
    def y(self) -> Ruler:
        """y axis ruler"""
        return self._y

    @property
    def z(self) -> Ruler:
        """z axis ruler"""
        return self._z

    @property
    def grids(self) -> Grids | bool:
        """grids for each plane: xy, xz, yz"""
        return self._grids

    @property
    def colors(self) -> tuple[pygfx.Color]:
        return tuple(getattr(self, dim).line.material.color for dim in ["x", "y", "z"])

    @colors.setter
    def colors(self, colors: tuple[pygfx.Color | str]):
        """get or set the colors for the x, y, and z rulers"""
        if len(colors) != 3:
            raise ValueError

        for dim, color in zip(["x", "y", "z"], colors):
            getattr(self, dim).line.material.color = color

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
    def intersection(self) -> tuple[float, float, float] | None:
        return self._intersection

    @intersection.setter
    def intersection(self, intersection: tuple[float, float, float] | None):
        """
        intersection point of [x, y, z] rulers.
        Set (0, 0, 0) for origin
        Set to `None` to follow when panning through the scene with orthographic projection
        """
        if intersection is None:
            self._intersection = None
            return

        if len(intersection) != 3:
            raise ValueError(
                "intersection must be a float of 3 elements for [x, y, z] or `None`"
            )

        self._intersection = tuple(float(v) for v in intersection)

    def update_using_bbox(self, bbox):
        """
        Update the w.r.t. the given bbox

        Parameters
        ----------
        bbox: np.ndarray
            array of shape [2, 3], [[xmin, ymin, zmin], [xmax, ymax, zmax]]

        """

        # flip axes if camera scale is flipped
        if self._plot_area.camera.local.scale_x < 0:
            bbox[0, 0], bbox[1, 0] = bbox[1, 0], bbox[0, 0]

        if self._plot_area.camera.local.scale_y < 0:
            bbox[0, 1], bbox[1, 1] = bbox[1, 1], bbox[0, 1]

        if self._plot_area.camera.local.scale_z < 0:
            bbox[0, 2], bbox[1, 2] = bbox[1, 2], bbox[0, 2]

        if self.intersection is None:
            intersection = (0, 0, 0)
        else:
            intersection = self.intersection

        self.update(bbox, intersection)

    def update_using_camera(self):
        """
        Update the axes w.r.t the current camera state

        For orthographic projections of the xy plane, it will calculate the inverse projection
        of the screen space onto world space to determine the current range of the world space
        to set the rulers and ticks

        For perspective projections it will just use the bbox of the scene to set the rulers

        """

        if not self.visible:
            return

        if self._plot_area.camera.fov == 0:
            xpos, ypos, width, height = self._plot_area.get_rect()
            # orthographic projection, get ranges using inverse

            # get range of screen space by getting the corners
            xmin, xmax = xpos, xpos + width
            ymin, ymax = ypos + height, ypos

            # apply quaternion to account for rotation of axes
            # xmin, _, _ = vec_transform_quat(
            #     [xmin, ypos + height / 2, 0],
            #     self.x.local.rotation
            # )
            #
            # xmax, _, _ = vec_transform_quat(
            #     [xmax, ypos + height / 2, 0],
            #     self.x.local.rotation,
            # )
            #
            # _, ymin, _ = vec_transform_quat(
            #     [xpos + width / 2, ymin, 0],
            #     self.y.local.rotation
            # )
            #
            # _, ymax, _ = vec_transform_quat(
            #     [xpos + width / 2, ymax, 0],
            #     self.y.local.rotation
            # )

            min_vals = self._plot_area.map_screen_to_world((xmin, ymin))
            max_vals = self._plot_area.map_screen_to_world((xmax, ymax))

            if min_vals is None or max_vals is None:
                return

            world_xmin, world_ymin, _ = min_vals
            world_xmax, world_ymax, _ = max_vals

            world_zmin, world_zmax = 0, 0

            bbox = np.array(
                [
                    [world_xmin, world_ymin, world_zmin],
                    [world_xmax, world_ymax, world_zmax],
                ]
            )

        else:
            # set ruler start and end positions based on scene bbox
            bbox = self._plot_area._fpl_graphics_scene.get_world_bounding_box()

        if self.intersection is None:
            if self._plot_area.camera.fov == 0:
                # place the ruler close to the left and bottom edges of the viewport
                # TODO: determine this for perspective projections
                xscreen_10, yscreen_10 = xpos + (width * 0.1), ypos + (height * 0.9)
                intersection = self._plot_area.map_screen_to_world(
                    (xscreen_10, yscreen_10)
                )
            else:
                # force origin since None is not supported for Persepctive projections
                self._intersection = (0, 0, 0)
                intersection = self._intersection

        else:
            # axes intersect at the origin
            intersection = self.intersection

        self.update(bbox, intersection)

    def update(self, bbox, intersection):
        """
        Update the axes using the given bbox and ruler intersection point

        Parameters
        ----------
        bbox: np.ndarray
            array of shape [2, 3], [[xmin, ymin, zmin], [xmax, ymax, zmax]]

        intersection: float, float, float
            intersection point of the x, y, z ruler

        """

        world_xmin, world_ymin, world_zmin = bbox[0]
        world_xmax, world_ymax, world_zmax = bbox[1]
        world_x_10, world_y_10, world_z_10 = intersection

        # swap min and max for each dimension if necessary
        if self._plot_area.camera.local.scale_y < 0:
            world_ymin, world_ymax = world_ymax, world_ymin
            self.y.tick_side = "right"  # swap tick side
            self.x.tick_side = "right"
        else:
            self.y.tick_side = "left"
            self.x.tick_side = "right"

        if self._plot_area.camera.local.scale_x < 0:
            world_xmin, world_xmax = world_xmax, world_xmin
            self.x.tick_side = "left"

        self.x.start_pos = world_xmin, world_y_10, world_z_10
        self.x.end_pos = world_xmax, world_y_10, world_z_10

        self.x.start_value = self.x.start_pos[0] - self.offset[0]
        statsx = self.x.update(
            self._plot_area.camera, self._plot_area.viewport.logical_size
        )

        self.y.start_pos = world_x_10, world_ymin, world_z_10
        self.y.end_pos = world_x_10, world_ymax, world_z_10

        self.y.start_value = self.y.start_pos[1] - self.offset[1]
        statsy = self.y.update(
            self._plot_area.camera, self._plot_area.viewport.logical_size
        )

        if self._plot_area.camera.fov != 0:
            self.z.start_pos = world_x_10, world_y_10, world_zmin
            self.z.end_pos = world_x_10, world_y_10, world_zmax

            self.z.start_value = self.z.start_pos[1] - self.offset[2]
            statsz = self.z.update(
                self._plot_area.camera, self._plot_area.viewport.logical_size
            )
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
