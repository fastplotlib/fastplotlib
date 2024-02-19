from ._base import GraphicFeature, FeatureEvent


class Deleted(GraphicFeature):
    """
    Used when a graphic is deleted, triggers events that can be useful to indicate this graphic has been deleted

    **event pick info:**

     ==================== ======================== =========================================================================
      key                  type                     description
     ==================== ======================== =========================================================================
      "collection-index"   int                      the index of the graphic within the collection that triggered the event
      "world_object"       pygfx.WorldObject        world object
     ==================== ======================== =========================================================================
    """

    def __init__(self, parent, value: bool):
        super(Deleted, self).__init__(parent, value)

    def _set(self, value: bool):
        value = self._parse_set_value(value)
        self._feature_changed(key=None, new_data=value)

    def _feature_changed(self, key, new_data):
        # this is a non-indexable feature so key=None

        pick_info = {
            "index": None,
            "collection-index": self._collection_index,
            "world_object": self._parent.world_object,
            "new_data": new_data,
        }

        event_data = FeatureEvent(type="deleted", pick_info=pick_info)

        self._call_event_handlers(event_data)

    def __repr__(self) -> str:
        s = f"DeletedFeature for {self._parent}"
        return s
