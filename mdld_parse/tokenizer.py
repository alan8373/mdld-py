"""Block-level tokenizer using markdown-it-py for CommonMark fidelity.

Replaces the previous regex-only line scanner. Block boundaries come from
markdown-it; per-line semantics are preserved (each line within a paragraph
or blockquote becomes its own token) because MD-LD's attachment rules are
defined "on the same line" (spec/Spec.md §5).

Phase 1 scope: heading (ATX), paragraph, list, blockquote, fence. Other
CommonMark blocks (html_block, hr, indented code, tables, setext headings,
frontmatter) are recognised by markdown-it but not yet tokenised — they're
skipped. Phase 4 will emit them as raw passthrough blocks.
"""
from __future__ import annotations
import re
from typing import Optional

from markdown_it import MarkdownIt

from .constants import (
    PREFIX_REGEX, HEADING_REGEX, BLOCKQUOTE_REGEX, UNORDERED_LIST_REGEX,
    FENCE_REGEX,
)
from .shared import (
    create_token, create_list_token, parse_lang_and_attrs,
    calc_range_info, calc_attrs_range,
)


_md = MarkdownIt('gfm-like')


# ---------------------------------------------------------------------------
# Source text → line offset table
# ---------------------------------------------------------------------------

def _build_line_offsets(text: str) -> list[int]:
    """offsets[i] = absolute character position of the start of line i."""
    offsets = [0]
    for idx, ch in enumerate(text):
        if ch == '\n':
            offsets.append(idx + 1)
    return offsets


def _line_slice(text: str, line_offsets: list[int],
                line_idx: int) -> tuple[str, int, int]:
    """Return (line_without_newline, line_start_offset, line_end_offset_excl)."""
    start = line_offsets[line_idx] if line_idx < len(line_offsets) else len(text)
    if line_idx + 1 < len(line_offsets):
        end_incl_nl = line_offsets[line_idx + 1]
    else:
        end_incl_nl = len(text)
    line = text[start:end_incl_nl]
    if line.endswith('\n'):
        line = line[:-1]
    return line, start, start + len(line)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def scan_tokens(text: str) -> list[dict]:
    line_offsets = _build_line_offsets(text)

    # Frontmatter detection happens before markdown-it sees the text
    # because mdit treats `---\n...\n---` as HR + setext heading. We
    # blank out the frontmatter lines so mdit ignores them but line
    # numbers stay aligned with the original source.
    fm_token, mdit_input = _extract_frontmatter(text, line_offsets)
    md_tokens    = _md.parse(mdit_input)

    out: list[dict] = []
    if fm_token:
        out.append(fm_token)
        expected_line = fm_token['_endLine']
    else:
        expected_line = 0

    i = 0
    while i < len(md_tokens):
        t = md_tokens[i]

        # Only top-level blocks drive the scan; nested tokens are skipped via
        # the per-block emitters that consume their subtree.
        if t.level != 0 or t.nesting < 0 or not t.map:
            i += 1
            continue

        start_line, end_line = t.map
        _emit_blanks(text, line_offsets, expected_line, start_line, out)

        if t.type == 'heading_open':
            i += _emit_heading(md_tokens, i, text, line_offsets, out)
        elif t.type == 'paragraph_open':
            i += _emit_paragraph(md_tokens, i, text, line_offsets, out)
        elif t.type in ('bullet_list_open', 'ordered_list_open'):
            i += _emit_list(md_tokens, i, text, line_offsets, out)
        elif t.type == 'blockquote_open':
            i += _emit_blockquote(md_tokens, i, text, line_offsets, out)
        elif t.type == 'fence':
            _emit_fence(t, text, line_offsets, out)
            i += 1
        elif t.type == 'code_block':
            _emit_indented_code(t, text, line_offsets, out)
            i += 1
        elif t.type == 'html_block':
            _emit_html_block(t, text, line_offsets, out)
            i += 1
        elif t.type == 'hr':
            _emit_hr(t, text, line_offsets, out)
            i += 1
        elif t.type == 'table_open':
            _emit_table(t, text, line_offsets, out)
            i += _skip_subtree(md_tokens, i)
        else:
            # Unhandled: frontmatter (plugin), reference link defs.
            i += 1

        expected_line = end_line

    # Trailing blank lines after the last block. `len(line_offsets)` counts
    # a phantom empty line after a trailing '\n'; subtract it so we don't
    # invent an extra blank that wasn't in the source.
    total_lines = len(line_offsets) - (1 if text.endswith('\n') else 0)
    _emit_blanks(text, line_offsets, expected_line, total_lines, out)

    return out


_FM_FENCE = re.compile(r'^---\s*$')


def _extract_frontmatter(text: str, line_offsets: list[int]) -> tuple[Optional[dict], str]:
    """If the text starts with a YAML/TOML frontmatter block (---\\n…\\n---),
    return (token, replacement_text) where replacement_text has those lines
    blanked. Otherwise return (None, text)."""
    if len(line_offsets) < 2:
        return None, text
    first_line, _, _ = _line_slice(text, line_offsets, 0)
    if not _FM_FENCE.match(first_line):
        return None, text

    # Look for the closing fence
    close_line = None
    for ln in range(1, len(line_offsets)):
        line, _, _ = _line_slice(text, line_offsets, ln)
        if _FM_FENCE.match(line):
            close_line = ln
            break
    if close_line is None:
        return None, text

    block_start = line_offsets[0]
    block_end_excl = (line_offsets[close_line + 1]
                      if close_line + 1 < len(line_offsets) else len(text))
    raw = text[block_start:block_end_excl]
    if raw.endswith('\n'):
        raw = raw[:-1]

    token = {
        'type':       'frontmatter',
        'range':      [block_start, block_start + len(raw)],
        'text':       raw,
        'attrs':      None,
        'attrsRange': None,
        'valueRange': None,
        '_carriers':  None,
        '_endLine':   close_line + 1,
    }

    # Replace frontmatter region with blanks of the same line count
    blanks = '\n' * (close_line + 1)
    replacement_text = blanks + text[block_end_excl:]
    return token, replacement_text


def _emit_blanks(text, line_offsets, from_line, to_line, out) -> None:
    """Emit one token per line in [from_line, to_line). Blank lines emit
    a 'blank' token; non-blank lines (silently consumed by mdit, e.g.
    reference link definitions) emit a 'reflink' raw passthrough."""
    for ln in range(from_line, to_line):
        if ln >= len(line_offsets):
            return
        line, line_start, line_end = _line_slice(text, line_offsets, ln)
        if line.strip():
            out.append({
                'type':       'reflink',
                'range':      [line_start, line_end],
                'text':       line,
                'attrs':      None,
                'attrsRange': None,
                'valueRange': None,
                '_carriers':  None,
            })
        else:
            out.append({
                'type':       'blank',
                'range':      [line_start, line_end],
                'text':       '',
                'attrs':      None,
                'attrsRange': None,
                'valueRange': None,
                '_carriers':  None,
            })


# ---------------------------------------------------------------------------
# Block-specific emitters
# ---------------------------------------------------------------------------

def _emit_heading(md_tokens, idx, text, line_offsets, out) -> int:
    """heading_open + inline + heading_close. Handles ATX and setext."""
    open_t = md_tokens[idx]

    if open_t.markup.startswith('#'):
        # ATX heading: single-line "# body {=attrs}"
        map_start, _ = open_t.map
        line, line_start, line_end = _line_slice(text, line_offsets, map_start)

        m = HEADING_REGEX.match(line)
        if not m:
            return 3
        depth = len(m.group(1))
        attrs = m.group(3) or None
        body  = m.group(2).strip()
        ri    = calc_range_info(line, attrs, line_start, depth, len(m.group(2)))
        out.append(create_token(
            'heading',
            [line_start, line_end],
            body,
            attrs, ri['attrsRange'], ri['valueRange'],
            depth=depth,
            _heading_style='atx',
        ))
        return 3

    # Setext heading: body line followed by '=====' or '-----'.
    # mdit's `markup` is the marker char; depth is 1 for '=' and 2 for '-'.
    marker_char = open_t.markup[0] if open_t.markup else '='
    depth = 1 if marker_char == '=' else 2
    map_start, map_end = open_t.map
    body_line, body_start, body_end = _line_slice(text, line_offsets, map_start)

    body_pat = HEADING_REGEX  # won't match without '#'; do a simpler split
    bm = re.match(r'^(.+?)(?:\s*(\{[^}]+\}))?\s*$', body_line)
    body  = bm.group(1).strip() if bm else body_line.strip()
    attrs = (bm.group(2) if bm else None) or None

    if attrs:
        ri = {
            'valueRange': [body_start, body_start + len(bm.group(1))],
            'attrsRange': calc_attrs_range(body_line, attrs, body_start),
        }
    else:
        ri = {'valueRange': [body_start, body_start + len(body)],
              'attrsRange': None}

    # Range covers all setext lines (body + marker)
    last_line_end = line_offsets[map_end] - 1 if map_end < len(line_offsets) else len(text)
    out.append(create_token(
        'heading',
        [body_start, last_line_end],
        body,
        attrs, ri['attrsRange'], ri['valueRange'],
        depth=depth,
        _heading_style='setext',
        _setext_marker=marker_char,
    ))
    return 3


def _emit_hr(t, text, line_offsets, out) -> None:
    map_start, map_end = t.map
    line, line_start, line_end = _line_slice(text, line_offsets, map_start)
    out.append({
        'type':       'hr',
        'range':      [line_start, line_end],
        'text':       line,
        'attrs':      None,
        'attrsRange': None,
        'valueRange': None,
        '_carriers':  None,
    })


def _emit_html_block(t, text, line_offsets, out) -> None:
    map_start, map_end = t.map
    block_start = line_offsets[map_start]
    block_end = line_offsets[map_end] if map_end < len(line_offsets) else len(text)
    raw = text[block_start:block_end]
    if raw.endswith('\n'):
        raw = raw[:-1]
    out.append({
        'type':       'html',
        'range':      [block_start, block_start + len(raw)],
        'text':       raw,
        'attrs':      None,
        'attrsRange': None,
        'valueRange': None,
        '_carriers':  None,
    })


def _emit_table(t, text, line_offsets, out) -> None:
    """Emit a GFM table as a raw passthrough block — the source slice
    is preserved verbatim, so internal structure (cells, alignment) is
    captured by storage and reproduced on regeneration without us
    needing to model the table grid in RDF."""
    map_start, map_end = t.map
    block_start = line_offsets[map_start]
    block_end = line_offsets[map_end] if map_end < len(line_offsets) else len(text)
    raw = text[block_start:block_end]
    if raw.endswith('\n'):
        raw = raw[:-1]
    out.append({
        'type':       'table',
        'range':      [block_start, block_start + len(raw)],
        'text':       raw,
        'attrs':      None,
        'attrsRange': None,
        'valueRange': None,
        '_carriers':  None,
    })


def _emit_indented_code(t, text, line_offsets, out) -> None:
    map_start, map_end = t.map
    block_start = line_offsets[map_start]
    block_end = line_offsets[map_end] if map_end < len(line_offsets) else len(text)
    raw = text[block_start:block_end]
    if raw.endswith('\n'):
        raw = raw[:-1]
    # Strip the 4-space indent that defines an indented code block, so the
    # stored text is the logical content. Regenerate adds the indent back.
    body_lines = [ln[4:] if ln.startswith('    ') else ln for ln in raw.split('\n')]
    body = '\n'.join(body_lines)
    out.append({
        'type':       'code',
        'range':      [block_start, block_start + len(raw)],
        'text':       body,
        'lang':       '',
        'attrs':      None,
        'attrsRange': None,
        'valueRange': None,
        '_carriers':  None,
        '_code_style': 'indented',
    })


def _emit_paragraph(md_tokens, idx, text, line_offsets, out) -> int:
    """paragraph_open + inline + paragraph_close. Splits per-line for MD-LD semantics."""
    open_t = md_tokens[idx]
    map_start, map_end = open_t.map
    for ln in range(map_start, map_end):
        line, line_start, line_end = _line_slice(text, line_offsets, ln)
        if not line.strip():
            continue
        # Prefix declarations get their own token type
        m = PREFIX_REGEX.match(line)
        if m:
            out.append({
                'type':       'prefix',
                'prefix':     m.group(1),
                'iri':        m.group(2).strip(),
                # Source-preservation fields used only when
                # preserve_content=True; the parser's prefix branch ignores them.
                'range':      [line_start, line_end],
                'text':       line,
                'attrs':      None,
                'attrsRange': None,
                'valueRange': None,
                '_carriers':  None,
            })
            continue
        out.append(create_token(
            'para',
            [line_start, line_end],
            line.strip(),
        ))
    return 3


def _emit_blockquote(md_tokens, idx, text, line_offsets, out) -> int:
    """blockquote_open + inner blocks + blockquote_close.
    Each inner line of the original source becomes one 'blockquote' token;
    lines that don't match the blockquote regex (e.g. `>` alone for a
    blank-in-quote) become raw passthrough tokens so they round-trip."""
    open_t = md_tokens[idx]
    map_start, map_end = open_t.map
    for ln in range(map_start, map_end):
        line, line_start, line_end = _line_slice(text, line_offsets, ln)
        m = BLOCKQUOTE_REGEX.match(line)
        if not m:
            _emit_blanks(text, line_offsets, ln, ln + 1, out)
            continue
        attrs = m.group(2) or None
        body  = m.group(1).strip()
        val_s = 2 if line.startswith('> ') else line.index('>') + 1
        out.append(create_token(
            'blockquote',
            [line_start, line_end],
            body,
            attrs, calc_attrs_range(line, attrs, line_start),
            [line_start + val_s, line_start + val_s + len(m.group(1))],
        ))
    return _skip_subtree(md_tokens, idx)


def _emit_list(md_tokens, idx, text, line_offsets, out) -> int:
    """bullet_list_open or ordered_list_open + items + close. Each list
    item produces a 'list' token; blank lines between items are preserved
    as 'blank' tokens for round-trip fidelity."""
    open_t = md_tokens[idx]
    map_start, map_end = open_t.map
    for ln in range(map_start, map_end):
        line, line_start, line_end = _line_slice(text, line_offsets, ln)
        m = UNORDERED_LIST_REGEX.match(line)
        if not m:
            _emit_blanks(text, line_offsets, ln, ln + 1, out)
            continue
        out.append(create_list_token(line, line_start, line_end + 1, m))
    return _skip_subtree(md_tokens, idx)


def _emit_fence(t, text: str, line_offsets, out) -> None:
    """fence is a self-closing block token with content and info string."""
    map_start, map_end = t.map
    line, line_start, _ = _line_slice(text, line_offsets, map_start)

    fm = FENCE_REGEX.match(line.strip())
    if not fm:
        return
    ra = parse_lang_and_attrs(fm.group(2))
    lang, attrs_text = ra['lang'], ra['attrsText']

    attrs_start_in_line = line.find(attrs_text) if attrs_text else -1
    attrs_range = ([line_start + attrs_start_in_line,
                    line_start + attrs_start_in_line + len(attrs_text)]
                   if attrs_text and attrs_start_in_line >= 0 else None)

    # Content body span — between fence open line end and fence close line start
    content_start = line_offsets[map_start + 1] if map_start + 1 < len(line_offsets) else len(text)
    if map_end - 1 < len(line_offsets):
        content_end = line_offsets[map_end - 1]
    else:
        content_end = len(text)
    if content_end > 0 and text[content_end - 1] == '\n':
        content_end -= 1

    range_end = line_offsets[map_end] if map_end < len(line_offsets) else len(text)

    body = t.content
    if body.endswith('\n'):
        body = body[:-1]

    out.append({
        'type':       'code',
        'range':      [line_start, range_end],
        'text':       body,
        'lang':       lang,
        'attrs':      attrs_text,
        'attrsRange': attrs_range,
        'valueRange': [content_start, max(content_start, content_end)],
        '_carriers':  None,
        '_code_style': 'fenced',
    })


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _skip_subtree(md_tokens, idx) -> int:
    """Return number of mdit tokens to skip past the open token at idx,
    including its matching close token."""
    open_t = md_tokens[idx]
    if open_t.nesting != 1:
        return 1
    depth = 1
    j = idx + 1
    while j < len(md_tokens) and depth > 0:
        if md_tokens[j].nesting == 1:
            depth += 1
        elif md_tokens[j].nesting == -1:
            depth -= 1
        j += 1
    return j - idx
