"""render: convert MD-LD text into HTML+RDFa."""
from __future__ import annotations
from typing import Optional

from .parse import parse
from .utils import DataFactory, expand_iri, shorten_iri
from .shared import escape_html, process_predicates
from .constants import DEFAULT_CONTEXT


def render(mdld: str, options: Optional[dict] = None) -> dict:
    """Render MD-LD text to HTML with RDFa annotations."""
    options = options or {}

    parsed = parse({'text': mdld, 'context': options.get('context') or {}})
    state  = _build_render_state(parsed, options, mdld)
    html   = _render_blocks(parsed['origin']['blocks'], state)
    wrapped = _wrap_with_rdfa_context(html, state['ctx'])

    result: dict = {
        'html':    wrapped,
        'context': state['ctx'],
        'metadata': {
            'blockCount':         len(parsed['origin']['blocks']),
            'quadCount':          len(parsed['quads']),
            'renderedRDFaCount':  state.get('renderedRDFaCount', 0),
        },
    }
    if options.get('strict'):
        result['quadMap']   = state.get('quadMap') or []
        rendered = state.get('quadMap') or []
        result['validation'] = {
            'allQuadsRendered': len(rendered) == len(parsed['quads']),
            'orphanedQuads':    _identify_orphaned(parsed['quads'], rendered),
        }
    return result


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

def _build_render_state(parsed: dict, options: dict, mdld: str) -> dict:
    ctx = parsed.get('context') or {**DEFAULT_CONTEXT, **(options.get('context') or {})}
    return {
        'ctx':                ctx,
        'df':                 options.get('dataFactory') or DataFactory,
        'baseIRI':            options.get('baseIRI', ''),
        'sourceText':         mdld,
        'output':             [],
        'currentSubject':     None,
        'documentSubject':    None,
        'blockStack':         [],
        'carrierStack':       [],
        'quads':              parsed.get('quads') or [],
        'quadMap':            [] if options.get('strict') else None,
        'renderedRDFaCount':  0,
        'strict':             bool(options.get('strict')),
    }


# ---------------------------------------------------------------------------
# Block rendering
# ---------------------------------------------------------------------------

def _render_blocks(blocks: dict, state: dict) -> str:
    sorted_blocks = sorted(
        blocks.values(),
        key=lambda b: (b.get('range') or {}).get('start') if isinstance(b.get('range'), dict)
        else (b.get('range', [0])[0] if b.get('range') else 0),
    )
    list_blocks  = [b for b in sorted_blocks if b.get('carrierType') == 'list' or b.get('type') == 'list']
    other_blocks = [b for b in sorted_blocks if b not in list_blocks]

    for b in other_blocks:
        _render_block(b, state)

    if list_blocks:
        _render_lists(list_blocks, state)

    return ''.join(state['output'])


def _render_lists(list_blocks: list, state: dict) -> None:
    state['output'].append('<ul>')
    for b in list_blocks:
        attrs = _build_rdfa_attrs_from_block(b, state['ctx'])
        state['output'].append(f'<li{attrs}>{escape_html(b.get("text", ""))}</li>')
    state['output'].append('</ul>')


def _block_range_tuple(block: dict):
    r = block.get('range')
    if isinstance(r, dict):
        return (r.get('start', 0), r.get('end', 0))
    if isinstance(r, (list, tuple)):
        return (r[0], r[1])
    return (0, 0)


def _render_block(block: dict, state: dict) -> None:
    if block.get('subject') and block['subject'] != 'RESET':
        state['currentSubject'] = block['subject']

    attrs = _build_rdfa_attrs_from_block(block, state['ctx'])
    btype = block.get('type') or block.get('carrierType')

    if btype == 'heading':
        text = block.get('text', '')
        level = 1
        m = text and text.lstrip()
        # heading depth is stored in raw token; default to 1 if not present
        depth = block.get('depth') or 1
        try:
            level = int(depth) if depth else 1
        except (TypeError, ValueError):
            level = 1
        tag = f'h{min(max(level, 1), 6)}'
        state['output'].append(f'<{tag}{attrs}>')
        _render_block_content(block, state)
        state['output'].append(f'</{tag}>')
    elif btype == 'para':
        state['output'].append(f'<p{attrs}>')
        _render_block_content(block, state)
        state['output'].append('</p>')
    elif btype == 'blockquote' or btype == 'quote':
        state['output'].append(f'<blockquote{attrs}>')
        _render_block_content(block, state)
        state['output'].append('</blockquote>')
    elif btype == 'code':
        lang = block.get('lang') or block.get('info') or ''
        cls  = f' class="language-{escape_html(lang)}"' if lang else ''
        state['output'].append(f'<pre><code{attrs}{cls}>')
        state['output'].append(escape_html(block.get('text', '')))
        state['output'].append('</code></pre>')
    elif btype == 'list':
        # rendered separately
        return
    else:
        state['output'].append(f'<div{attrs}>')
        _render_block_content(block, state)
        state['output'].append('</div>')


def _render_block_content(block: dict, state: dict) -> None:
    text     = block.get('text', '') or ''
    carriers = block.get('carriers') or []
    if not carriers:
        state['output'].append(escape_html(text))
        return

    positions = []
    for carrier in carriers:
        ctext = carrier.get('text')
        if not ctext:
            continue
        idx = text.find(ctext)
        if idx >= 0:
            positions.append((idx, len(ctext), carrier))
    positions.sort(key=lambda p: p[0])

    pos = 0
    for start, length, carrier in positions:
        if start > pos:
            state['output'].append(escape_html(text[pos:start]))
        state['output'].append(_render_carrier(carrier, state))
        pos = start + length
    if pos < len(text):
        state['output'].append(escape_html(text[pos:]))


def _render_carrier(carrier: dict, state: dict) -> str:
    attrs = _build_rdfa_attrs_from_carrier(carrier, state)
    ctype = carrier.get('type')
    text  = carrier.get('text', '')

    if ctype == 'emphasis':
        return f'<em{attrs}>{escape_html(text)}</em>'
    if ctype == 'strong':
        return f'<strong{attrs}>{escape_html(text)}</strong>'
    if ctype == 'code':
        return f'<code{attrs}>{escape_html(text)}</code>'
    if ctype == 'link':
        url = carrier.get('url') or ''
        return f'<a href="{escape_html(url)}"{attrs}>{escape_html(text)}</a>'
    return escape_html(text)


# ---------------------------------------------------------------------------
# RDFa attributes
# ---------------------------------------------------------------------------

def _build_rdfa_attrs_from_carrier(carrier: dict, state: dict) -> str:
    attrs = []
    subject = carrier.get('subject') or state.get('currentSubject')
    if not subject or subject == 'RESET' or subject.startswith('=#') or subject.startswith('+'):
        return ''
    expanded = expand_iri(subject, state['ctx'])
    short    = shorten_iri(expanded, state['ctx'])
    attrs.append(f'about="{escape_html(short)}"')

    types = carrier.get('types') or []
    if types:
        names = []
        for t in types:
            iri = t['iri'] if isinstance(t, dict) else t
            names.append(shorten_iri(expand_iri(iri, state['ctx']), state['ctx']))
        attrs.append(f'typeof="{escape_html(" ".join(names))}"')

    preds = carrier.get('predicates') or []
    if preds:
        bucket = process_predicates(preds, state['ctx'])
        if bucket['literalProps']:
            attrs.append(f'property="{escape_html(" ".join(bucket["literalProps"]))}"')
        if bucket['objectProps']:
            attrs.append(f'rel="{escape_html(" ".join(bucket["objectProps"]))}"')
        if bucket['reverseProps']:
            attrs.append(f'rev="{escape_html(" ".join(bucket["reverseProps"]))}"')

    return ' ' + ' '.join(attrs) if attrs else ''


def _build_rdfa_attrs_from_block(block: dict, ctx: dict) -> str:
    attrs = []
    s = block.get('subject')
    if s and s != 'RESET' and not s.startswith('=#') and not s.startswith('+'):
        expanded = expand_iri(s, ctx)
        short    = shorten_iri(expanded, ctx)
        attrs.append(f'about="{escape_html(short)}"')

    types = block.get('types') or []
    if types:
        names = []
        for t in types:
            iri = t['iri'] if isinstance(t, dict) else t
            names.append(shorten_iri(expand_iri(iri, ctx), ctx))
        attrs.append(f'typeof="{escape_html(" ".join(names))}"')

    preds = block.get('predicates') or []
    if preds:
        bucket = process_predicates(preds, ctx)
        if bucket['literalProps']:
            attrs.append(f'property="{escape_html(" ".join(bucket["literalProps"]))}"')
        if bucket['objectProps']:
            attrs.append(f'rel="{escape_html(" ".join(bucket["objectProps"]))}"')
        if bucket['reverseProps']:
            attrs.append(f'rev="{escape_html(" ".join(bucket["reverseProps"]))}"')

    return ' ' + ' '.join(attrs) if attrs else ''


# ---------------------------------------------------------------------------
# Wrapping / context
# ---------------------------------------------------------------------------

def _generate_prefix_declarations(ctx: dict) -> str:
    parts = [f'{p}: {iri}' for p, iri in ctx.items() if p != '@vocab']
    return f' prefix="{" ".join(parts)}"' if parts else ''


def _generate_vocab_declaration(ctx: dict) -> str:
    return f' vocab="{ctx["@vocab"]}"' if ctx.get('@vocab') else ''


def _wrap_with_rdfa_context(html: str, ctx: dict) -> str:
    return f'<div{_generate_prefix_declarations(ctx)}{_generate_vocab_declaration(ctx)}>{html}</div>'


def _identify_orphaned(all_quads: list, rendered: list) -> list:
    keys = {f'{q["subject"].value}|{q["predicate"].value}|{q["object"].value}'
            if isinstance(q, dict)
            else f'{q.subject.value}|{q.predicate.value}|{q.object.value}'
            for q in rendered}
    return [q for q in all_quads
            if f'{q.subject.value}|{q.predicate.value}|{q.object.value}' not in keys]
