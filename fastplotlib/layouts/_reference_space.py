import numpy as np

import pygfx
from pylinalg import vec_transform, vec_unproject

from ..graphics import Graphic


class ReferenceSpace:
    def __init__(
            self,
            scene: pygfx.Scene,
            camera: pygfx.Camera,
            controller: pygfx.Controller,
            viewport: pygfx.Viewport,
            name: str | None = None,
    ):
        self._scene = scene
        self._camera = camera
        self._controller = controller
        self.viewport = viewport
        self._name = name

        self._graphics: list[Graphic] = list()

    @property
    def name(self) -> str:
        return self._name

    @property
    def scene(self) -> pygfx.Scene:
        return self._scene

    @property
    def camera(self) -> pygfx.Camera:
        return self._camera

    # @property
    # def controller(self):
        # same controller for all reference spaces in one PlotArea I think?
        # Use key events to add or remove a camera from the PlotArea dynamically?
        # pass

    def auto_scale(self):
        pass

    def center(self):
        pass

    @property
    def graphics(self) -> np.ndarray[Graphic]:
        graphics = np.asarray(self._graphics)
        graphics.flags.writeable = False
        return graphics

    def map_screen_to_world(
        self, pos: tuple[float, float] | pygfx.PointerEvent, allow_outside: bool = False
    ) -> np.ndarray | None:
        """
        Map screen position to world position

        Parameters
        ----------
        pos: (float, float) | pygfx.PointerEvent
            ``(x, y)`` screen coordinates, or ``pygfx.PointerEvent``

        """
        if isinstance(pos, pygfx.PointerEvent):
            pos = pos.x, pos.y

        if not allow_outside and not self.viewport.is_inside(*pos):
            return None

        vs = self.viewport.logical_size

        # get position relative to viewport
        pos_rel = (
            pos[0] - self.viewport.rect[0],
            pos[1] - self.viewport.rect[1],
        )

        # convert screen position to NDC
        pos_ndc = (pos_rel[0] / vs[0] * 2 - 1, -(pos_rel[1] / vs[1] * 2 - 1), 0)

        # get world position
        pos_ndc += vec_transform(self.camera.world.position, self.camera.camera_matrix)
        pos_world = vec_unproject(pos_ndc[:2], self.camera.camera_matrix)

        # default z is zero for now
        return np.array([*pos_world[:2], 0])
