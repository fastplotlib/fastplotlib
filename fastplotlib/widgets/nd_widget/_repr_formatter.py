from __future__ import annotations

import html
from collections.abc import Callable
from typing import Any


_RESET = "\033[0m"
_BOLD  = "\033[1m"
_DIM   = "\033[2m"

_C = {
    "title":   "\033[38;5;75m",   # sky-blue
    "spatial": "\033[38;5;114m",  # sage-green
    "slider":  "\033[38;5;215m",  # soft-orange
    "label":   "\033[38;5;246m",  # mid-grey
    "value":   "\033[38;5;252m",  # near-white
    "section": "\033[38;5;68m",   # steel-blue
    "muted":   "\033[38;5;240m",  # dark-grey
    "warn":    "\033[38;5;222m",  # amber
}


def _c(key: str, text: str) -> str:
    return f"{_C[key]}{text}{_RESET}"


def _callable_name(f: Callable | None) -> str:
    if f is None:
        return "—"
    module = getattr(f, "__module__", "") or ""
    qname  = getattr(f, "__qualname__", None) or getattr(f, "__name__", repr(f))
    if module and not module.startswith("__"):
        short = module.split(".")[-1]
        return f"{short}.{qname}"
    return qname


def ndprocessor_fmt_txt(processor) -> str:
    """
    Returns a colored, ascii box
    """
    lines: list[str] = []

    cls = type(processor).__name__
    lines.append(_c("title", _BOLD + cls) + _RESET)
    lines.append(_c("muted", "─" * 72))

    lines.append(_c("section", "  Dimensions"))

    header = (
        f"  {'dim':<14}{'size':>6}   {'role':<10}  {'window_func  size':<26}  index_mapping"
    )
    lines.append(_c("label", header))
    lines.append(_c("muted", "  " + "─" * 70))

    for dim in processor.dims:
        size  = processor.shape[dim]
        is_sp = dim in processor.spatial_dims
        role_s = (_c("spatial", f"{'spatial':<10}") if is_sp
                  else _c("slider",  f"{'slider':<10}"))

        # window_func - size column
        if not is_sp:
            wf, ws = processor.window_funcs.get(dim, (None, None))
            if wf is not None and ws is not None:
                win_s = _c("value", f"{_callable_name(wf)}") + _c("muted", f" - {ws}")
            else:
                win_s = _c("muted", "—")
        else:
            win_s = ""

        # index_mapping column (slider dims only; skip identity)
        if not is_sp:
            imap = processor.index_mappings.get(dim)
            iname = getattr(imap, "__name__", "") if imap is not None else ""
            if iname != "identity" and imap is not None:
                idx_s = _c("value", _callable_name(imap))
            else:
                idx_s = _c("muted", "—")
        else:
            idx_s = ""

        # pad win_s to fixed visible width (strip ANSI for measuring)
        import re
        _ansi_re = re.compile(r"\033\[[^m]*m")
        win_visible = len(_ansi_re.sub("", win_s))
        win_pad = win_s + " " * max(0, 26 - win_visible)

        line = (
            f"  {_c('value', f'{str(dim):<14}')}"
            f"{_c('label', f'{size:>6}')}   "
            f"{role_s}  {win_pad}  {idx_s}"
        )
        lines.append(line)

    # window order
    if processor.window_order:
        lines.append("")
        order_s = " → ".join(str(d) for d in processor.window_order)
        lines.append(f"  {_c('section', 'Window order')}   {_c('value', order_s)}")

    # spatial func
    if processor.spatial_func is not None:
        lines.append("")
        lines.append(
            f"  {_c('section', 'Spatial func')}   "
            f"{_c('value', _callable_name(processor.spatial_func))}"
        )

    lines.append(_c("muted", "─" * 72))
    return "\n".join(lines)


def ndgraphic_fmt_txt(ndg) -> str:
    """Text repr for NDGraphic."""
    cls  = type(ndg).__name__
    gcls = type(ndg.graphic).__name__ if ndg.graphic is not None else "—"
    name = ndg.name or "—"

    header = (
        f"{_c('title', _BOLD + cls)}{_RESET}  "
        f"{_c('muted', '·')}  "
        f"{_c('section', 'graphic')} {_c('value', gcls)}  "
        f"{_c('muted', '·')}  "
        f"{_c('section', 'name')} {_c('value', name)}\n"
    )

    proc_block = ndprocessor_fmt_txt(ndg.processor)
    # indent processor block
    indented = "\n".join("  " + l for l in proc_block.splitlines())
    return header + indented

_CSS = """
<style>
  .fpl-repr {
    font-family: "JetBrains Mono", "Fira Code", "Cascadia Code", monospace;
    font-size: 12.5px;
    line-height: 1.6;
    border: 1px solid var(--jp-border-color1, #d0d7de);
    border-radius: 6px;
    overflow: hidden;
    width: fit-content;
    max-width: 100%;
    background: var(--jp-layout-color0, #ffffff);
    color: var(--jp-content-font-color1, #24292f);
    box-shadow: 0 1px 3px rgba(0,0,0,.06);
  }

  /* ── header bar ── */
  .fpl-repr-header {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 7px 14px;
    background: var(--jp-layout-color2, #f6f8fa);
    border-bottom: 1px solid var(--jp-border-color1, #d0d7de);
    flex-wrap: wrap;
  }
  .fpl-repr-classname {
    font-weight: 700;
    font-size: 13px;
    color: #0969da;
    letter-spacing: .02em;
  }
  /* dark mode */
  @media (prefers-color-scheme: dark) {
    .fpl-repr-classname { color: #79c0ff; }
  }
  .fpl-repr-pill {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 1px 8px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: .03em;
  }
  .fpl-pill-graphic {
    background: #ddf4ff;
    color: #0550ae;
    border: 1px solid #b6e3ff;
  }
  .fpl-pill-name {
    background: #fff8c5;
    color: #7d4e00;
    border: 1px solid #f1c40f66;
  }
  @media (prefers-color-scheme: dark) {
    .fpl-pill-graphic { background: #0d2140; color: #79c0ff; border-color: #1f4068; }
    .fpl-pill-name    { background: #2d1f00; color: #e3b341; border-color: #5d4200; }
  }
  .fpl-repr-sep { color: var(--jp-content-font-color3, #b0bec5); }

  /* ── body ── */
  .fpl-repr-body { padding: 0 0 4px 0; }

  /* ── section (collapsible) ── */
  .fpl-section { border-top: 1px solid var(--jp-border-color2, #eaecef); }
  .fpl-section summary {
    list-style: none;
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 5px 14px;
    cursor: pointer;
    user-select: none;
    color: var(--jp-content-font-color2, #555);
    font-size: 11.5px;
    font-weight: 600;
    letter-spacing: .06em;
    text-transform: uppercase;
    background: var(--jp-layout-color1, #fff);
    transition: background .12s;
  }
  .fpl-section summary:hover { background: var(--jp-layout-color2, #f6f8fa); }
  .fpl-section summary::before {
    content: "▶";
    font-size: 8px;
    transition: transform .15s;
    opacity: .5;
  }
  .fpl-section[open] > summary::before { transform: rotate(90deg); }
  .fpl-section summary::-webkit-details-marker { display: none; }

  .fpl-section-title-text {
    color: #0969da;
  }
  @media (prefers-color-scheme: dark) {
    .fpl-section-title-text { color: #79c0ff; }
  }
  .fpl-section-count {
    margin-left: auto;
    padding: 0 6px;
    border-radius: 10px;
    background: var(--jp-layout-color3, #eaecef);
    color: var(--jp-content-font-color2, #888);
    font-size: 10.5px;
    font-weight: 500;
  }

  /* ── dim table ── */
  .fpl-dim-table {
    width: 100%;
    border-collapse: collapse;
    padding: 0 14px 6px;
    display: block;
  }
  .fpl-dim-table td {
    padding: 2px 10px 2px 14px;
    vertical-align: middle;
    white-space: nowrap;
  }
  .fpl-dim-name {
    font-weight: 600;
    color: var(--jp-content-font-color1, #24292f);
    min-width: 80px;
  }
  .fpl-dim-size {
    color: var(--jp-content-font-color2, #57606a);
    text-align: right;
    font-variant-numeric: tabular-nums;
    padding-right: 14px !important;
  }
  .fpl-badge {
    display: inline-block;
    padding: 1px 7px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 600;
  }
  .fpl-badge-spatial {
    background: #dcfce7;
    color: #16a34a;
    border: 1px solid #bbf7d0;
  }
  .fpl-badge-slider {
    background: #fff7ed;
    color: #c2410c;
    border: 1px solid #fed7aa;
  }
  @media (prefers-color-scheme: dark) {
    .fpl-badge-spatial { background: #0a2e1a; color: #4ade80; border-color: #166534; }
    .fpl-badge-slider  { background: #2d1200; color: #fb923c; border-color: #7c2d12; }
  }
  .fpl-dim-win { color: var(--jp-content-font-color3, #8b949e); font-size: 11.5px; }
  .fpl-dim-win code {
    background: var(--jp-layout-color2, #f6f8fa);
    border: 1px solid var(--jp-border-color2, #eaecef);
    border-radius: 3px;
    padding: 0 4px;
    font-size: 11px;
  }

  /* ── key-value list (used for spatial func, window order, index maps) ── */
  .fpl-kv-list {
    padding: 4px 14px 8px;
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 2px 16px;
  }
  .fpl-kv-key {
    font-weight: 600;
    color: var(--jp-content-font-color2, #57606a);
    white-space: nowrap;
  }
  .fpl-kv-val {
    color: var(--jp-content-font-color1, #24292f);
    font-size: 11.5px;
  }
  .fpl-kv-val code {
    background: var(--jp-layout-color2, #f6f8fa);
    border: 1px solid var(--jp-border-color2, #eaecef);
    border-radius: 3px;
    padding: 1px 5px;
    font-size: 11px;
  }

  .fpl-dim-th {
    padding: 2px 10px 4px 14px;
    font-size: 10.5px;
    font-weight: 600;
    letter-spacing: .05em;
    text-transform: uppercase;
    color: var(--jp-content-font-color3, #8b949e);
    text-align: left;
    white-space: nowrap;
  }

  /* ── arrow chain ── */
  .fpl-arrow { color: #0969da; margin: 0 3px; }
  @media (prefers-color-scheme: dark) { .fpl-arrow { color: #79c0ff; } }

  /* ── always-visible footer rows (window order, spatial func) ── */
  .fpl-footer {
    border-top: 1px solid var(--jp-border-color2, #eaecef);
    padding: 5px 14px 7px;
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 3px 16px;
    align-items: baseline;
  }
  .fpl-footer-key {
    font-size: 11px;
    font-weight: 600;
    letter-spacing: .05em;
    text-transform: uppercase;
    color: var(--jp-content-font-color3, #8b949e);
    white-space: nowrap;
  }
  .fpl-footer-val {
    font-size: 11.5px;
    color: var(--jp-content-font-color1, #24292f);
  }
  .fpl-footer-val code {
    background: var(--jp-layout-color2, #f6f8fa);
    border: 1px solid var(--jp-border-color2, #eaecef);
    border-radius: 3px;
    padding: 0 4px;
    font-size: 11px;
  }
</style>
"""


def _h(s: Any) -> str:
    """html-escape a stringified value"""
    return html.escape(str(s))


def _badge(role: str) -> str:
    cls = "fpl-badge-spatial" if role == "spatial" else "fpl-badge-slider"
    return f'<span class="fpl-badge {cls}">{role}</span>'


def _code(s: str) -> str:
    return f"<code>{_h(s)}</code>"


def _section(title: str, content_html: str, count: str = "", open_: bool = True) -> str:
    open_attr = " open" if open_ else ""
    count_badge = (
        f'<span class="fpl-section-count">{_h(count)}</span>' if count else ""
    )
    return (
        f'<details class="fpl-section"{open_attr}>'
        f'<summary>'
        f'<span class="fpl-section-title-text">{_h(title)}</span>'
        f'{count_badge}'
        f'</summary>'
        f'{content_html}'
        f'</details>'
    )


def _dim_rows_html(proc) -> str:
    rows = []
    for dim in proc.dims:
        size  = proc.shape[dim]
        is_sp = dim in proc.spatial_dims
        badge = _badge("spatial" if is_sp else "slider")

        # window_func - size column
        if not is_sp:
            wf, ws = proc.window_funcs.get(dim, (None, None))
            if wf is not None and ws is not None:
                win_td = (
                    f'<td class="fpl-dim-win">'
                    f'{_code(_callable_name(wf))}'
                    f'<span style="margin:0 4px;opacity:.4">-</span>'
                    f'{_code(str(ws))}'
                    f'</td>'
                )
            else:
                win_td = '<td class="fpl-dim-win" style="opacity:.35">—</td>'
        else:
            win_td = '<td></td>'

        # index_mapping column (slider dims only; hide identity)
        if not is_sp:
            imap  = proc.index_mappings.get(dim)
            if imap is not None:
                idx_td = f'<td class="fpl-dim-win">{_code(_callable_name(imap))}</td>'
            else:
                idx_td = '<td class="fpl-dim-win" style="opacity:.35">—</td>'
        else:
            idx_td = '<td></td>'

        rows.append(
            f'<tr>'
            f'<td class="fpl-dim-name">{_h(str(dim))}</td>'
            f'<td class="fpl-dim-size">{size:,}</td>'
            f'<td>{badge}</td>'
            f'{win_td}'
            f'{idx_td}'
            f'</tr>'
        )

    # column header row
    header = (
        f'<tr style="border-bottom:0.5px solid var(--jp-border-color2,#eaecef)">'
        f'<th class="fpl-dim-th">dim</th>'
        f'<th class="fpl-dim-th" style="text-align:right">size</th>'
        f'<th class="fpl-dim-th">role</th>'
        f'<th class="fpl-dim-th">window_func - size</th>'
        f'<th class="fpl-dim-th">index_mapping</th>'
        f'</tr>'
    )

    table = (
        '<table class="fpl-dim-table">'
        '<colgroup>'
        '<col style="min-width:80px"><col style="min-width:55px">'
        '<col><col><col>'
        '</colgroup>'
        + header
        + "".join(rows)
        + "</table>"
    )
    return table


def _footer_kv(pairs: list[tuple[str, str]]) -> str:
    """Always-visible key/value rows rendered below the dim table."""
    inner = ""
    for k, v in pairs:
        inner += (
            f'<div class="fpl-footer-key">{_h(k)}</div>'
            f'<div class="fpl-footer-val">{v}</div>'
        )
    return f'<div class="fpl-footer">{inner}</div>'


def _kv_list_html(pairs: list[tuple[str, str]]) -> str:
    inner = ""
    for k, v in pairs:
        inner += (
            f'<div class="fpl-kv-key">{_h(k)}</div>'
            f'<div class="fpl-kv-val">{v}</div>'
        )
    return f'<div class="fpl-kv-list">{inner}</div>'


def _html_processor(proc) -> str:
    cls = _h(type(proc).__name__)

    # header
    ndim_pill = (
        f'<span class="fpl-repr-pill" style="'
        f'background:#f0f3fa;border:1px solid #c8d2e0;color:#444">'
        f'{proc.ndim}D</span>'
    )
    header = (
        f'<div class="fpl-repr-header">'
        f'<span class="fpl-repr-classname">{cls}</span>'
        f'{ndim_pill}'
        f'</div>'
    )

    # dims section (always open)
    dim_content = _dim_rows_html(proc)
    sections    = _section("Dimensions", dim_content,
                            count=str(proc.ndim), open_=True)

    # always-visible footer rows
    footer_pairs: list[tuple[str, str]] = []

    if proc.window_order:
        chain = " → ".join(
            f'<span class="fpl-arrow">&#x25B6;</span>{_h(str(d))}'
            if i > 0 else _h(str(d))
            for i, d in enumerate(proc.window_order)
        )
        footer_pairs.append(("window order", f'<span>{chain}</span>'))

    if proc.spatial_func is not None:
        footer_pairs.append(("spatial func", _code(_callable_name(proc.spatial_func))))

    if footer_pairs:
        sections += _footer_kv(footer_pairs)

    body = f'<div class="fpl-repr-body">{sections}</div>'
    return f'{_CSS}<div class="fpl-repr">{header}{body}</div>'


def ndgraphic_fmt_html(ndg) -> str:
    cls  = _h(type(ndg).__name__)
    gcls = _h(type(ndg.graphic).__name__) if ndg.graphic is not None else "—"
    name = _h(ndg.name or "—")

    graphic_pill = f'<span class="fpl-repr-pill fpl-pill-graphic">graphic: {gcls}</span>'
    name_pill    = f'<span class="fpl-repr-pill fpl-pill-name">name: {name}</span>'

    header = (
        f'<div class="fpl-repr-header">'
        f'<span class="fpl-repr-classname">{cls}</span>'
        f'<span class="fpl-repr-sep">·</span>'
        f'{graphic_pill}{name_pill}'
        f'</div>'
    )

    # embed processor repr (without its own outer box) inside a section
    proc_inner = _dim_rows_html(ndg.processor)
    sections   = _section("Processor · Dimensions", proc_inner, open_=True)

    footer_pairs: list[tuple[str, str]] = []

    if ndg.processor.window_order:
        chain = " → ".join(
            f'<span class="fpl-arrow">&#x25B6;</span>{_h(str(d))}'
            if i > 0 else _h(str(d))
            for i, d in enumerate(ndg.processor.window_order)
        )
        footer_pairs.append(("window order", f'<span>{chain}</span>'))

    if ndg.processor.spatial_func is not None:
        footer_pairs.append(("spatial func", _code(_callable_name(ndg.processor.spatial_func))))

    if footer_pairs:
        sections += _footer_kv(footer_pairs)

    body = f'<div class="fpl-repr-body">{sections}</div>'
    return f'{_CSS}<div class="fpl-repr">{header}{body}</div>'

class ReprMixin:
    """
    Mixin that provides:
      • __repr__          → coloured ANSI text (terminal / plain REPL)
      • _repr_html_       → rich HTML (Jupyter)
      • _repr_mimebundle_ → both, so Jupyter picks the richest format

    Subclasses must implement _repr_text_() and _repr_html_() themselves OR
    rely on the dispatch below which checks the concrete type.
    """

    def _repr_text_(self) -> str:
        # lazy import avoids circular; swap for a direct call in your module
        if _is_ndgraphic(self):
            return ndgraphic_fmt_txt(self)
        return ndprocessor_fmt_txt(self)

    def _repr_html_(self) -> str:
            return ndgraphic_fmt_html(self)
        return _html_processor(self)

    def __repr__(self) -> str:
        return self._repr_text_()

    def _repr_mimebundle_(self, **kwargs) -> dict:
        return {
            "text/plain": self._repr_text_(),
            "text/html":  self._repr_html_(),
        }


def _is_ndgraphic(obj) -> bool:
    """duck-type check: does this object have a .graphic and .processor?"""
    return hasattr(obj, "graphic") and hasattr(obj, "processor")