import numpy as np

from . import GraphicFeature, FeatureEvent


class DragFeature(GraphicFeature):
    """
    Manages mouse and keyboard drag events
    """
    def __init__(
            self,
            parent,
            multiplier: np.ndarray = None,
            clamp: np.ndarray = None,
    ):
        """
        Feature that manages the drag state of a Graphic

        Parameters
        ----------
        parent: Graphic
            parent Graphic that this feature controls

        multiplier: array-like of size 3
            multiply the drag vector by this multplier vector. final_vector = delta * multiplier.
            by default the multiplier is set to (1, 1, 1). For example, you can disable movement along an
            axis by setting the multiplier for that axis component to zero, for example to restrict movement
            only along the x-axis: use ``multiplier = (1, 0, 0)``

        clamp: np.ndarray, of shape (2, 2) or (2, 3)
            restrict drag movement of the Graphic within the clamp limits. Argument must be in the form:
                [[xmin, ymin, zmin],
                 [xmax, ymax, zmax]]

            by default the clamp is [-inf, +inf] for all axes.

        """
        super(DragFeature, self).__init__(parent, data=None)
        self.multiplier = multiplier
        self.clamp = clamp

        self._last_position = None
        self._initial_controller_state: bool = None

        self._event_type = None  # event that caused the delta, one of "mouse" or "kb"

    @property
    def multiplier(self) -> np.ndarray:
        """
        multiply the drag vector by this multplier vector. final_vector = delta * multiplier.
        by default the multiplier is set to (1, 1, 1). For example, you can disable movement along an
        axis by setting the multiplier for that axis component to zero, for example to restrict movement
        only along the x-axis: use ``multiplier = (1, 0, 0)``
        """
        return self._multiplier

    @multiplier.setter
    def multiplier(self, value: np.ndarray):
        if value is None:
            self._multiplier = np.array([1., 1., 1.])
        else:
            self._multiplier = np.array(value)

    @property
    def clamp(self) -> np.ndarray:
        """
        restrict drag movement of the Graphic within the clamp limits. Argument must be in the form:
                [[xmin, ymin, zmin],
                 [xmax, ymax, zmax]]
        """
        return self._clamp

    @clamp.setter
    def clamp(self, clamp: np.ndarray):
        if clamp is None:
            clamp = np.zeros(shape=(2, 3), dtype=np.float32)
            clamp[0] = -np.inf
            clamp[1] = np.inf

        elif isinstance(clamp, np.ndarray):
            if clamp.shape not in [(2, 2), (2, 3)]:
                raise ValueError(
                    "clamp must be array of shape (2, 2) or (2, 3), see the docstring"
                )
            if clamp.shape == (2, 2):
                # add z with inf clamp
                clamp = np.column_stack([clamp, np.array([[np.inf], [np.inf]])])
        else:
            raise ValueError(
                "clamp must be array of shape (2, 2) or (2, 3), see the docstring"
            )

        self._clamp = clamp

    def _set(self, delta: np.ndarray):
        """

        Parameters
        ----------
        delta: (float, float, float)
            drag vector

        """
        delta = np.array(delta) * self.multiplier

        # add delta vector and clamp
        self._parent.position = (self._parent.position + delta).clip(self.clamp[0], self.clamp[1]).astype(np.float32)

        self._feature_changed(key=None, new_data=delta)

    def _feature_changed(self, key, new_data: np.ndarray):
        if len(self._event_handlers) < 1:
            return

        pick_info = {
            "world_object": self._parent.world_object,
            "delta": new_data,
            "graphic": self._parent,
        }

        event_data = FeatureEvent(type="drag", pick_info=pick_info)

        self._call_event_handlers(event_data)

    def __repr__(self) -> str:
        return f"DragFeature for {self._parent}"
