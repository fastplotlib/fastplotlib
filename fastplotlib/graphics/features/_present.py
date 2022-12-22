from ._base import GraphicFeature, FeatureEvent
from pygfx import Scene


class PresentFeature(GraphicFeature):
    """
    Toggles if the object is present in the scene, different from visible \n
    Useful for computing bounding boxes from the Scene to only include graphics
    that are present
    """
    def __init__(self, parent, present: bool = True):
        self._scene = None
        super(PresentFeature, self).__init__(parent, present)

    def _set(self, present: bool):
        i = 0
        while not isinstance(self._scene, Scene):
            self._scene = self._parent.world_object.parent
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

        self._feature_changed(key=None, new_data=present)

    def __repr__(self):
        return repr(self.feature_data)

    def _feature_changed(self, key, new_data):
        # this is a non-indexable feature so key=None

        pick_info = {
            "index": None,
            "world_object": self._parent.world_object,
            "new_data": new_data
        }

        event_data = FeatureEvent(type="present-changed", pick_info=pick_info)

        self._call_event_handlers(event_data)