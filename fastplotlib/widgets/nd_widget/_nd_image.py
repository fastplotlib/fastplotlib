from typing import Literal

from ._processor_base import NDProcessor


class NDImageProcessor(NDProcessor):
    @property
    def n_display_dims(self) -> Literal[2, 3]:
        pass

    def _validate_n_display_dims(self, n_display_dims):
        if n_display_dims not in (2, 3):
            raise ValueError("`n_display_dims` must be")
