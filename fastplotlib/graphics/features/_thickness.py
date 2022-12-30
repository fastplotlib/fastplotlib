from ._base import GraphicFeature, FeatureEvent


class ThicknessFeature(GraphicFeature):
    """
    Toggles if the object is present in the scene, different from visible \n
    Useful for computing bounding boxes from the Scene to only include graphics
    that are present
    """
    def __init__(self, parent, thickness: float):
        self._scene = None
        super(ThicknessFeature, self).__init__(parent, thickness)

    def _set(self, value: float):
        value = self._parse_set_value(value)

        self._parent.world_object.material.thickness = value
        self._feature_changed(key=None, new_data=value)

    def _feature_changed(self, key, new_data):
        # this is a non-indexable feature so key=None

        pick_info = {
            "index": None,
            "collection-index": self._collection_index,
            "world_object": self._parent.world_object,
            "new_data": new_data
        }

        event_data = FeatureEvent(type="thickness", pick_info=pick_info)

        self._call_event_handlers(event_data)
