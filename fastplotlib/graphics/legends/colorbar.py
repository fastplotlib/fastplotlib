from .._base import Graphic
from .. import TextGraphic
import pygfx

class CmapLegend(Graphic):
    def __init__(
        self,
        cmap_name: str,
        vmin: float,
        vmax: float,
        width: float,
        height: float,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        wo = pygfx.Group()
    
        cmap = get_cmap(cmap_name)
    
        tex = pygfx.Texture(np.repeat([cmap], 2, axis=0), dim=2)
        
        geometry = pygfx.plane_geometry(width, height, 1, 1)
        material = pygfx.MeshBasicMaterial(map=tex)
        self._rectangle = pygfx.Mesh(geometry, material)
    
        self._text_vmax = TextGraphic(
            text=str(vmax),
            size=16,
            position=(-width/2, 0),
            anchor="center",
            outline_color="black",
            outline_thickness=1,
        )

        self._text_vmax.position_x = width/2 + 5
    
        self._text_vmin = TextGraphic(
            text=str(vmin),
            size=16,
            position=(width, 0),
            anchor="center",
            outline_color="black",
            outline_thickness=1,
        )

        self._text_vmin.position_x = -width/2 - 5
    
        wo.add(self._rectangle, self._text_vmin.world_object, self._text_vmax.world_object)
        self._set_world_object(wo)