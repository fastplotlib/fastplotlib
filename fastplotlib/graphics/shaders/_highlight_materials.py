import numpy as np
import pygfx
from pygfx.resources import Buffer, Texture

_HIGHLIGHT_UNIFORM_FIELDS = dict(highlight_alpha="f4")


class HighlightableLineMaterial(pygfx.LineMaterial):
    uniform_type = dict(pygfx.LineMaterial.uniform_type, **_HIGHLIGHT_UNIFORM_FIELDS)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._highlight_ids_buffer = Buffer(np.zeros(1, dtype=np.uint32))
        self._highlight_lut_buffer = Buffer(np.zeros((1, 4), dtype=np.float32))
        self.uniform_buffer.data["highlight_alpha"] = 1.0
        self.uniform_buffer.update_range()


class HighlightableLineThinMaterial(pygfx.LineThinMaterial):
    uniform_type = dict(pygfx.LineThinMaterial.uniform_type, **_HIGHLIGHT_UNIFORM_FIELDS)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._highlight_ids_buffer = Buffer(np.zeros(1, dtype=np.uint32))
        self._highlight_lut_buffer = Buffer(np.zeros((1, 4), dtype=np.float32))
        self.uniform_buffer.data["highlight_alpha"] = 1.0
        self.uniform_buffer.update_range()


class HighlightablePointsMaterial(pygfx.PointsMaterial):
    uniform_type = dict(pygfx.PointsMaterial.uniform_type, **_HIGHLIGHT_UNIFORM_FIELDS)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._highlight_ids_buffer = Buffer(np.zeros(1, dtype=np.uint32))
        self._highlight_lut_buffer = Buffer(np.zeros((1, 4), dtype=np.float32))
        self.uniform_buffer.data["highlight_alpha"] = 1.0
        self.uniform_buffer.update_range()


class HighlightablePointsMarkerMaterial(pygfx.PointsMarkerMaterial):
    uniform_type = dict(pygfx.PointsMarkerMaterial.uniform_type, **_HIGHLIGHT_UNIFORM_FIELDS)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._highlight_ids_buffer = Buffer(np.zeros(1, dtype=np.uint32))
        self._highlight_lut_buffer = Buffer(np.zeros((1, 4), dtype=np.float32))
        self.uniform_buffer.data["highlight_alpha"] = 1.0
        self.uniform_buffer.update_range()


class HighlightablePointsSpriteMaterial(pygfx.PointsSpriteMaterial):
    uniform_type = dict(pygfx.PointsSpriteMaterial.uniform_type, **_HIGHLIGHT_UNIFORM_FIELDS)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._highlight_ids_buffer = Buffer(np.zeros(1, dtype=np.uint32))
        self._highlight_lut_buffer = Buffer(np.zeros((1, 4), dtype=np.float32))
        self.uniform_buffer.data["highlight_alpha"] = 1.0
        self.uniform_buffer.update_range()


class HighlightablePointsGaussianBlobMaterial(pygfx.PointsGaussianBlobMaterial):
    uniform_type = dict(
        pygfx.PointsGaussianBlobMaterial.uniform_type, **_HIGHLIGHT_UNIFORM_FIELDS
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._highlight_ids_buffer = Buffer(np.zeros(1, dtype=np.uint32))
        self._highlight_lut_buffer = Buffer(np.zeros((1, 4), dtype=np.float32))
        self.uniform_buffer.data["highlight_alpha"] = 1.0
        self.uniform_buffer.update_range()


class HighlightableImageMaterial(pygfx.ImageBasicMaterial):
    uniform_type = dict(pygfx.ImageBasicMaterial.uniform_type, **_HIGHLIGHT_UNIFORM_FIELDS)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Store through _store so the PropTracker detects replacement and re-calls get_bindings().
        self._store.highlight_mask_texture = Texture(np.zeros((1, 1), dtype=np.uint16), dim=2)
        self._highlight_lut_buffer = Buffer(np.zeros((65535, 4), dtype=np.float32))
        self.uniform_buffer.data["highlight_alpha"] = 1.0
        self.uniform_buffer.update_range()

    @property
    def _highlight_mask_texture(self):
        return self._store.highlight_mask_texture

    @_highlight_mask_texture.setter
    def _highlight_mask_texture(self, texture):
        self._store.highlight_mask_texture = texture
