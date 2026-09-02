"""
Highlightable shader subclasses for fastplotlib.

Each shader subclass:
  1. Adds two extra bindings: s_highlight_ids (u32 storage) and s_highlight_lut (vec4 storage),
     or t_highlight_mask (R8Uint texture) + s_highlight_lut for images.
  2. Patches the compiled WGSL to mix a highlight color into out.color before returning,
     leaving out.pick completely untouched.

Anchor strings are validated at runtime; a warning is emitted and highlighting falls back
to a no-op if a pygfx version change has moved them.
"""

import warnings

from pygfx.objects import Points, Line, Image
from pygfx.renderers.wgpu.shaders.pointsshader import PointsShader
from pygfx.renderers.wgpu.shaders.lineshader import LineShader, ThinLineShader
from pygfx.renderers.wgpu.shaders.imageshader import ImageShader
from pygfx.renderers.wgpu import (
    register_wgpu_render_function,
    Binding,
    GfxTextureView,
)

from ._highlight_materials import (
    HighlightableLineMaterial,
    HighlightableLineThinMaterial,
    HighlightablePointsMaterial,
    HighlightablePointsMarkerMaterial,
    HighlightablePointsSpriteMaterial,
    HighlightablePointsGaussianBlobMaterial,
    HighlightableImageMaterial,
)

_POINTS_HELPER = """\
fn fpl_apply_highlight(base_color: vec4<f32>, vertex_idx: u32) -> vec4<f32> {
    if (vertex_idx >= arrayLength(&s_highlight_ids)) { return base_color; }
    let id = s_highlight_ids[vertex_idx];
    if (id == 0u) { return base_color; }
    let h = s_highlight_lut[id - 1u];
    return vec4<f32>(mix(base_color.rgb, h.rgb, h.a * u_material.highlight_alpha), base_color.a);
}

"""

_THIN_LINE_HELPER = """\
fn fpl_apply_highlight(base_color: vec4<f32>, hl: vec4<f32>) -> vec4<f32> {
    if (hl.a <= 0.0) { return base_color; }
    return vec4<f32>(mix(base_color.rgb, hl.rgb, hl.a * u_material.highlight_alpha), base_color.a);
}

"""

_LINE_HELPER = """\
fn fpl_apply_highlight_line(
    base_color: vec4<f32>,
    hl_node: vec4<f32>,
    hl_vert: vec4<f32>,
    is_join: bool,
    join_coord_lin: f32,
    join_coord_fan: f32,
) -> vec4<f32> {
    var hl: vec4<f32> = hl_vert;
    if (is_join) {
        let hl_seg = hl_node - (hl_node - hl_vert) / (1.0 - abs(join_coord_lin));
        hl = mix(hl_seg, hl_node, abs(join_coord_fan));
    }
    if (hl.a <= 0.0) { return base_color; }
    return vec4<f32>(mix(base_color.rgb, hl.rgb, hl.a * u_material.highlight_alpha), base_color.a);
}

"""

_IMAGE_HELPER = """\
fn fpl_apply_highlight_img(base_color: vec4<f32>, mask_id: u32) -> vec4<f32> {
    if (mask_id == 0u) { return base_color; }
    let h = s_highlight_lut[mask_id - 1u];
    return vec4<f32>(mix(base_color.rgb, h.rgb, h.a * u_material.highlight_alpha), base_color.a);
}

"""

_IMAGE_SAMPLE_ANCHOR = "    let value = sample_im(varyings.texcoord.xy, sizef);"

_IMAGE_VIS_PRE_SAMPLE = """\
    var fpl_texcoord = varyings.texcoord;
    if (u_material.fpl_n_visible > 0u) {
        let fpl_vis_px = vec2<u32>(varyings.texcoord * sizef);
        let fpl_vis_idx = select(fpl_vis_px.x, fpl_vis_px.y, u_material.fpl_vis_axis_y == 1u);
        if (fpl_vis_idx >= u_material.fpl_n_visible) { discard; }
        
        // discard Nones which we map to 0xFFFFFFFF
        let fpl_src_u = s_vis_lut[fpl_vis_idx];
        if (fpl_src_u == 0xFFFFFFFFu) { discard; }
        let fpl_src_f = f32(fpl_src_u);
        
        if (u_material.fpl_vis_axis_y == 1u) {
            fpl_texcoord.y = (fpl_src_f + 0.5) / sizef.y;
        } else {
            fpl_texcoord.x = (fpl_src_f + 0.5) / sizef.x;
        }
    }
    let value = sample_im(fpl_texcoord.xy, sizef);\
"""


# fragment shader replacement position, same for most shaders
_FS_COLOR_ANCHOR = "    out.color = out_color;"

_THIN_VS_ANCHOR = "            return varyings;\n        }"
_THIN_FS_COLOR_ANCHOR = "            out.color = out_color;"
_THIN_FRAGMENT_ENTRY = "        @fragment\n        fn fs_main"


def _warn_anchor_missing(label: str, anchor: str) -> None:
    warnings.warn(
        f"fpl highlight: anchor {anchor!r} not found in {label} WGSL. "
        "Highlighting disabled for this graphic type. "
        "This is likely caused by a pygfx version change, update the anchor string.",
        stacklevel=3,
    )


def _check(wgsl: str, anchor: str, label: str) -> bool:
    if wgsl.count(anchor) != 1:
        _warn_anchor_missing(label, anchor)
        return False
    return True


def _add_ids_bindings(shader, group0: dict, material) -> None:
    """Append s_highlight_ids and s_highlight_lut bindings to group0."""
    next_idx = max(group0.keys()) + 1
    new = {
        next_idx: Binding(
            "s_highlight_ids",
            "buffer/read_only_storage",
            material._highlight_ids_buffer,
            "FRAGMENT",
        ),
        next_idx
        + 1: Binding(
            "s_highlight_lut",
            "buffer/read_only_storage",
            material._highlight_lut_buffer,
            "FRAGMENT",
        ),
    }
    shader.define_bindings(0, new)
    group0.update(new)


def _add_ids_bindings_vs_fs(shader, group0: dict, material) -> None:
    """Append s_highlight_ids (VERTEX+FRAGMENT) and s_highlight_lut bindings to group0."""
    import wgpu as _wgpu

    vs_fs = _wgpu.ShaderStage.VERTEX | _wgpu.ShaderStage.FRAGMENT
    next_idx = max(group0.keys()) + 1
    new = {
        next_idx: Binding(
            "s_highlight_ids",
            "buffer/read_only_storage",
            material._highlight_ids_buffer,
            vs_fs,
        ),
        next_idx
        + 1: Binding(
            "s_highlight_lut",
            "buffer/read_only_storage",
            material._highlight_lut_buffer,
            vs_fs,
        ),
    }
    shader.define_bindings(0, new)
    group0.update(new)


def _add_mask_bindings(shader, group0: dict, material) -> None:
    """Append t_highlight_mask, s_highlight_lut, and s_vis_lut bindings to group0."""
    next_idx = max(group0.keys()) + 1
    mask_view = GfxTextureView(material._highlight_mask_texture)
    new = {
        next_idx: Binding(
            "t_highlight_mask",
            "texture/auto",
            mask_view,
            "FRAGMENT",
        ),
        next_idx
        + 1: Binding(
            "s_highlight_lut",
            "buffer/read_only_storage",
            material._highlight_lut_buffer,
            "FRAGMENT",
        ),
        next_idx
        + 2: Binding(
            "s_vis_lut",
            "buffer/read_only_storage",
            material._vis_lut_buffer,
            "FRAGMENT",
        ),
    }
    shader.define_bindings(0, new)
    group0.update(new)


@register_wgpu_render_function(Points, HighlightablePointsMaterial)
@register_wgpu_render_function(Points, HighlightablePointsMarkerMaterial)
@register_wgpu_render_function(Points, HighlightablePointsSpriteMaterial)
@register_wgpu_render_function(Points, HighlightablePointsGaussianBlobMaterial)
class HighlightablePointsShader(PointsShader):

    def get_bindings(self, wobject, shared, scene):
        result = super().get_bindings(wobject, shared, scene)
        group0 = result[0]
        _add_ids_bindings(self, group0, wobject.material)
        return {0: group0}

    def get_code(self):
        wgsl = super().get_code()
        if not _check(wgsl, _FS_COLOR_ANCHOR, "points.wgsl"):
            return wgsl
        if not _check(wgsl, "@fragment\nfn fs_main", "points.wgsl"):
            return wgsl

        wgsl = wgsl.replace(
            _FS_COLOR_ANCHOR,
            "    out.color = fpl_apply_highlight(out_color, varyings.pick_idx);",
            1,
        )
        wgsl = wgsl.replace(
            "@fragment\nfn fs_main",
            _POINTS_HELPER + "@fragment\nfn fs_main",
            1,
        )
        return wgsl


@register_wgpu_render_function(Image, HighlightableImageMaterial)
class HighlightableImageShader(ImageShader):

    def get_bindings(self, wobject, shared, scene):
        result = super().get_bindings(wobject, shared, scene)
        group0 = result[0]
        _add_mask_bindings(self, group0, wobject.material)
        return {0: group0}

    def get_code(self):
        wgsl = super().get_code()

        # Pre-sample: inject visibility LUT remapping. fpl_texcoord is always
        # declared here so the highlight block below can safely reference it
        # regardless of whether visibility is active
        if not _check(wgsl, _IMAGE_SAMPLE_ANCHOR, "image.wgsl sample"):
            return wgsl
        wgsl = wgsl.replace(_IMAGE_SAMPLE_ANCHOR, _IMAGE_VIS_PRE_SAMPLE, 1)

        # Post-sample: highlight blend. Uses fpl_texcoord (source coords) so that
        # highlight indices always refer to original data positions whether or not
        # visibility remapping is active.
        if not _check(wgsl, _FS_COLOR_ANCHOR, "image.wgsl"):
            return wgsl
        mask_lines = (
            "    let fpl_px = vec2<u32>(fpl_texcoord * vec2<f32>(textureDimensions(t_highlight_mask)));\n"
            "    let fpl_mask_id = textureLoad(t_highlight_mask, fpl_px, 0).r;\n"
            "    out.color = fpl_apply_highlight_img(out_color, fpl_mask_id);"
        )
        wgsl = wgsl.replace(_FS_COLOR_ANCHOR, mask_lines, 1)

        if not _check(wgsl, "@fragment\nfn fs_main", "image.wgsl FS entry"):
            return wgsl
        wgsl = wgsl.replace(
            "@fragment\nfn fs_main",
            _IMAGE_HELPER + "@fragment\nfn fs_main",
            1,
        )
        return wgsl


_THIN_VS_INJECTION = (
    "            let fpl_hl_id = select(0u, s_highlight_ids[u32(i0)],\n"
    "                u32(i0) < arrayLength(&s_highlight_ids));\n"
    "            varyings.fpl_hl_color = select(\n"
    "                vec4<f32>(0.0), s_highlight_lut[fpl_hl_id - 1u], fpl_hl_id != 0u);\n"
    "            return varyings;\n"
    "        }"
)


@register_wgpu_render_function(Line, HighlightableLineThinMaterial)
class HighlightableThinLineShader(ThinLineShader):

    def get_bindings(self, wobject, shared, scene):
        result = super().get_bindings(wobject, shared, scene)
        group0 = result[0]
        # Needs VERTEX stage so the VS can read the ids buffer
        _add_ids_bindings_vs_fs(self, group0, wobject.material)
        return {0: group0}

    def get_code(self):
        wgsl = super().get_code()

        if not _check(wgsl, _THIN_VS_ANCHOR, "ThinLineShader VS"):
            return wgsl
        wgsl = wgsl.replace(_THIN_VS_ANCHOR, _THIN_VS_INJECTION, 1)

        if not _check(wgsl, _THIN_FS_COLOR_ANCHOR, "ThinLineShader FS"):
            return wgsl
        wgsl = wgsl.replace(
            _THIN_FS_COLOR_ANCHOR,
            "            out.color = fpl_apply_highlight(out_color, varyings.fpl_hl_color);",
            1,
        )

        if not _check(wgsl, _THIN_FRAGMENT_ENTRY, "ThinLineShader FS entry"):
            return wgsl
        wgsl = wgsl.replace(
            _THIN_FRAGMENT_ENTRY,
            _THIN_LINE_HELPER + _THIN_FRAGMENT_ENTRY,
            1,
        )
        return wgsl


_LINE_VS_ANCHOR = "    varyings.pick_idx = u32(node_index);"

_LINE_VS_INJECTION = """\
    let fpl_other_idx = select(node_index_prev, node_index_next, node_index_is_even);
    let fpl_hl_id_node = select(0u, s_highlight_ids[u32(node_index)],
        u32(node_index) < arrayLength(&s_highlight_ids));
    let fpl_hl_id_other = select(0u, s_highlight_ids[u32(fpl_other_idx)],
        u32(fpl_other_idx) < arrayLength(&s_highlight_ids));
    let fpl_hl_raw_node = select(vec4<f32>(0.0), s_highlight_lut[fpl_hl_id_node - 1u], fpl_hl_id_node != 0u);
    let fpl_hl_raw_other = select(vec4<f32>(0.0), s_highlight_lut[fpl_hl_id_other - 1u], fpl_hl_id_other != 0u);
    varyings.fpl_hl_color_node = fpl_hl_raw_node;
    varyings.fpl_hl_color_vert = mix(fpl_hl_raw_node, fpl_hl_raw_other, ratio_interp);
    varyings.pick_idx = u32(node_index);\
"""

_LINE_FS_REPLACEMENT = (
    "    out.color = fpl_apply_highlight_line(\n"
    "        out_color, varyings.fpl_hl_color_node, varyings.fpl_hl_color_vert,\n"
    "        is_join, join_coord_lin, join_coord_fan);"
)


@register_wgpu_render_function(Line, HighlightableLineMaterial)
class HighlightableLineShader(LineShader):

    def get_bindings(self, wobject, shared, scene):
        result = super().get_bindings(wobject, shared, scene)
        group0 = result[0]
        _add_ids_bindings_vs_fs(self, group0, wobject.material)
        return {0: group0}

    def get_code(self):
        wgsl = super().get_code()

        if not _check(wgsl, _LINE_VS_ANCHOR, "line.wgsl VS"):
            return wgsl
        wgsl = wgsl.replace(_LINE_VS_ANCHOR, _LINE_VS_INJECTION, 1)

        if not _check(wgsl, _FS_COLOR_ANCHOR, "line.wgsl FS"):
            return wgsl
        wgsl = wgsl.replace(_FS_COLOR_ANCHOR, _LINE_FS_REPLACEMENT, 1)

        if not _check(wgsl, "@fragment\nfn fs_main", "line.wgsl FS entry"):
            return wgsl
        wgsl = wgsl.replace(
            "@fragment\nfn fs_main",
            _LINE_HELPER + "@fragment\nfn fs_main",
            1,
        )
        return wgsl
