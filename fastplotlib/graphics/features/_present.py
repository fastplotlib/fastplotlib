from ._base import GraphicFeature, FeatureEvent
from pygfx import Scene, Group


class PresentFeature(GraphicFeature):
    """
    Toggles if the object is present in the scene, different from visible.
    Useful for computing bounding boxes from the Scene to only include graphics
    that are present.

    **event pick info:**

     ==================== ======================== =========================================================================
      key                  type                     description
     ==================== ======================== =========================================================================
      "index"              ``None``                 not used
      "new_data"           ``bool``                 new data, ``True`` or ``False``
      "collection-index"   int                      the index of the graphic within the collection that triggered the event
      "world_object"       pygfx.WorldObject        world object
     ==================== ======================== ========================================================================
    """
    def __init__(self, parent, present: bool = True, collection_index: int = False):
        self._scene = None
        super(PresentFeature, self).__init__(parent, present, collection_index)

    def _set(self, present: bool):
        present = self._parse_set_value(present)

        i = 0
        wo = self._parent.world_object
        while not isinstance(self._scene, (Group, Scene)):
            wo_parent = wo.parent
            self._scene = wo_parent
            wo = wo_parent
            i += 1

            if i > 100:
                raise RecursionError(
                    "Exceded scene graph depth threshold, cannot find Scene associated with"
                    "this graphic."
                )

        if present:
            if self._parent.world_object not in self._scene.children:
                self._scene.add(self._parent.world_object)

        else:
            if self._parent.world_object in self._scene.children:
                self._scene.remove(self._parent.world_object)

        self._data = present
        self._feature_changed(key=None, new_data=present)

    def _feature_changed(self, key, new_data):
        # this is a non-indexable feature so key=None

        pick_info = {
            "index": None,
            "collection-index": self._collection_index,
            "world_object": self._parent.world_object,
            "new_data": new_data
        }

        event_data = FeatureEvent(type="present", pick_info=pick_info)

        self._call_event_handlers(event_data)
