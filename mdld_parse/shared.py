"""Shared utilities used by parse, generate, and render modules."""
from __future__ import annotations
import re
from typing import Optional

from .constants import (DEFAULT_CONTEXT, STANDALONE_SUBJECT_REGEX, FENCE_REGEX,
                        PREFIX_REGEX, HEADING_REGEX, UNORDERED_LIST_REGEX, BLOCKQUOTE_REGEX)
from .utils import (parse_semantic_block, expand_iri, shorten_iri, hash_str,
                    NamedNode, Term, quad_index_key as _qik)

# ---------------------------------------------------------------------------
# Fence close-pattern cache
# ---------------------------------------------------------------------------

_fence_close_patterns: dict[str, re.Pattern] = {}


def get_fence_close_pattern(fence_char: str) -> re.Pattern:
    if fence_char not in _fence_close_patterns:
        _fence_close_patterns[fence_char] = re.compile(rf'^({re.escape(fence_char)}{{3,}})')
    return _fence_close_patterns[fence_char]


# ---------------------------------------------------------------------------
# Range helpers
# ---------------------------------------------------------------------------

def calc_attrs_range(line: str, attrs: Optional[str], line_start: int) -> Optional[list]:
    if not attrs:
        return None
    idx = line.rfind(attrs)
    if idx < 0:
        return None
    return [line_start + idx, line_start + idx + len(attrs)]


def calc_range_info(line: str, attrs: Optional[str], line_start: int,
                    prefix_length: int, value_length: int) -> dict:
    rest = line[prefix_length:]
    ws = len(rest) - len(rest.lstrip())
    val_start = prefix_length + ws
    return {
        'valueRange': [line_start + val_start, line_start + val_start + value_length],
        'attrsRange': calc_attrs_range(line, attrs, line_start),
    }


# ---------------------------------------------------------------------------
# Token / carrier creation
# ---------------------------------------------------------------------------

def create_token(type_: str, range_: list, text: str,
                 attrs: Optional[str] = None, attrs_range: Optional[list] = None,
                 value_range: Optional[list] = None, **extra) -> dict:
    tok = {'type': type_, 'range': range_, 'text': text,
           'attrs': attrs, 'attrsRange': attrs_range, 'valueRange': value_range,
           '_carriers': None, **extra}
    return tok


def create_carrier(type_: str, text: str, attrs: Optional[str],
                   attrs_range: Optional[list], value_range: Optional[list],
                   range_: list, pos: int, **extra) -> dict:
    return {'type': type_, 'text': text, 'attrs': attrs,
            'attrsRange': attrs_range, 'valueRange': value_range,
            'range': range_, 'pos': pos, **extra}


def create_list_token(line: str, line_start: int, pos: int, match) -> dict:
    attrs   = match.group(4) or None
    indent  = len(match.group(1))
    marker  = match.group(2) or ''
    # Whitespace between marker end and body start (preserves "-  body" exactly).
    spacing = line[match.end(2):match.start(3)] if match.group(3) else ' '
    prefix  = indent + len(marker)
    ri = calc_range_info(line, attrs, line_start, prefix, len(match.group(3)))
    return create_token(
        'list', [line_start, pos - 1], match.group(3).strip(), attrs,
        ri['attrsRange'], ri['valueRange'],
        indent=indent,
        _listMarker=marker,
        _listMarkerSpacing=spacing,
    )


# ---------------------------------------------------------------------------
# Semantic block cache
# ---------------------------------------------------------------------------

_sem_cache: dict[str, dict] = {}
EMPTY_SEM: dict = {'predicates': [], 'types': [], 'subject': None, 'object': None,
                   'datatype': None, 'language': None, 'entries': []}


def parse_sem_cached(attrs: Optional[str]) -> dict:
    if not attrs:
        return EMPTY_SEM
    if attrs not in _sem_cache:
        _sem_cache[attrs] = parse_semantic_block(attrs)
    return _sem_cache[attrs]


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def parse_lang_and_attrs(lang_and_attrs: str) -> dict:
    si = lang_and_attrs.find(' ')
    bi = lang_and_attrs.find('{')
    lang_end = min(si if si > -1 else len(lang_and_attrs),
                   bi if bi > -1 else len(lang_and_attrs))
    lang = lang_and_attrs[:lang_end]
    attrs_text = re.search(r'\{[^{}]*\}', lang_and_attrs[lang_end:])
    return {'lang': lang, 'attrsText': attrs_text.group(0) if attrs_text else None}


# ---------------------------------------------------------------------------
# Bracket / carrier extraction helpers
# ---------------------------------------------------------------------------

def find_matching_bracket(text: str, bracket_start: int) -> Optional[int]:
    depth = 1
    i = bracket_start + 1
    while i < len(text) and depth > 0:
        if text[i] == '[':
            depth += 1
        elif text[i] == ']':
            depth -= 1
        i += 1
    return None if depth > 0 else i


def extract_url_from_brackets(text: str, bracket_end: int) -> dict:
    url = None
    span_end = bracket_end
    if bracket_end < len(text) and text[bracket_end] == '(':
        paren_end = text.find(')', bracket_end)
        if paren_end != -1:
            url = text[bracket_end + 1:paren_end]
            span_end = paren_end + 1
    return {'url': url, 'spanEnd': span_end}


def extract_attributes_from_text(text: str, span_end: int, base_offset: int) -> dict:
    attrs = None
    attrs_range = None
    remaining = text[span_end:]
    ws_m = re.match(r'^\s+', remaining)
    attrs_start = len(ws_m.group(0)) if ws_m else 0
    if attrs_start < len(remaining) and remaining[attrs_start] == '{':
        brace_end = remaining.find('}', attrs_start)
        if brace_end != -1:
            attrs = remaining[attrs_start:brace_end + 1]
            abs_start = base_offset + span_end + attrs_start
            attrs_range = [abs_start, abs_start + len(attrs)]
            span_end += brace_end + 1
    return {'attrs': attrs, 'attrsRange': attrs_range, 'finalSpanEnd': span_end}


def determine_carrier_type(url: Optional[str]) -> dict:
    if url and not url.startswith('='):
        return {'carrierType': 'link', 'resourceIRI': url}
    return {'carrierType': 'span', 'resourceIRI': None}


def calc_carrier_ranges(match, base_offset: int, match_start: int) -> dict:
    full = match.group(0)
    g1   = match.group(1)
    g2   = match.group(2)
    val_start_in_full = full.index(g1)
    val_start = base_offset + match_start + val_start_in_full
    brace_in_full = full.index('{')
    attrs_start = base_offset + match_start + brace_in_full
    attrs_end   = attrs_start + len(g2) + 2
    return {
        'valueRange': [val_start, val_start + len(g1)],
        'attrsRange': [attrs_start, attrs_end],
        'range':      [base_offset + match_start, attrs_end],
        'pos':        match_start + len(full),
    }


# ---------------------------------------------------------------------------
# Clean text extraction
# ---------------------------------------------------------------------------

def extract_clean_text(token: dict) -> str:
    text = token.get('text', '') or ''
    attrs_range = token.get('attrsRange')
    tok_range   = token.get('range')
    base = tok_range[0] if tok_range else 0

    if attrs_range:
        before = text[:attrs_range[0] - base]
        after  = text[attrs_range[1] - base:]
        text   = before + after

    carriers = token.get('_carriers') or []
    ranges = sorted(
        [c['attrsRange'] for c in carriers if c.get('attrsRange')],
        key=lambda r: r[0], reverse=True,
    )
    for ar in ranges:
        rs, re_ = ar[0] - base, ar[1] - base
        if 0 <= rs and re_ <= len(text):
            text = text[:rs] + text[re_:]

    t = token.get('type', '')
    if t == 'heading':
        return re.sub(r'^#+\s*', '', text).strip()
    if t == 'list':
        return re.sub(r'^[-*+]\s*', '', text).strip()
    if t == 'blockquote':
        return re.sub(r'^>\s*', '', text).strip()
    return text.strip()


# ---------------------------------------------------------------------------
# RDF constants
# ---------------------------------------------------------------------------

RDF_TYPE      = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'
RDF_STATEMENT = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#Statement'
RDF_SUBJECT   = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#subject'
RDF_PREDICATE = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#predicate'
RDF_OBJECT    = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#object'
XSD_STRING    = 'http://www.w3.org/2001/XMLSchema#string'


# ---------------------------------------------------------------------------
# Origin entry
# ---------------------------------------------------------------------------

def create_lean_origin_entry(block: dict, subject: Term, predicate: Term,
                              meta: Optional[dict] = None) -> dict:
    return {
        'blockId':     block['id'],
        'range':       block['range'],
        'carrierType': block.get('carrierType'),
        'subject':     subject.value,
        'predicate':   predicate.value,
        'context':     block.get('context'),
        'polarity':    '-' if (meta and meta.get('remove')) else '+',
        'value':       block.get('text', ''),
    }


# ---------------------------------------------------------------------------
# Subject / object resolution helpers
# ---------------------------------------------------------------------------

def resolve_fragment(fragment: str, current_subject: Optional[Term], df) -> Optional[Term]:
    if not current_subject:
        return None
    sv = current_subject.value
    base = sv[:sv.index('#')] if '#' in sv else sv
    return df.named_node(base + '#' + fragment)


def resolve_subject(sem: dict, state: dict) -> Optional[Term]:
    s = sem.get('subject')
    if not s:
        return None
    if s == 'RESET':
        state['current_subject'] = None
        return None
    if s.startswith('=#'):
        return resolve_fragment(s[2:], state['current_subject'], state['df'])
    return state['df'].named_node(expand_iri(s, state['ctx']))


def resolve_object(sem: dict, state: dict) -> Optional[Term]:
    o = sem.get('object')
    if not o:
        return None
    if o.startswith('#'):
        return resolve_fragment(o[1:], state['current_subject'], state['df'])
    return state['df'].named_node(expand_iri(o, state['ctx']))


# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------

def escape_html(text: str) -> str:
    if not text:
        return ''
    return (text.replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace("'", '&#x27;'))


# ---------------------------------------------------------------------------
# Term-type helpers
# ---------------------------------------------------------------------------

def is_literal(term) -> bool:
    return getattr(term, 'term_type', None) == 'Literal'


def is_named_node(term) -> bool:
    return getattr(term, 'term_type', None) == 'NamedNode'


def is_rdf_type(term) -> bool:
    return getattr(term, 'value', None) == RDF_TYPE


# ---------------------------------------------------------------------------
# Prefix / generate utilities
# ---------------------------------------------------------------------------

def get_prefix_from_iri(iri: str, context: dict) -> Optional[str]:
    if not iri:
        return None
    shortened = shorten_iri(iri, context)
    if ':' in shortened:
        return shortened.split(':')[0]
    return None


def collect_used_prefixes(subject_groups: dict, context: dict) -> set:
    used = set()
    for quads in subject_groups.values():
        for q in quads:
            for iri in (q.subject.value, q.predicate.value):
                p = get_prefix_from_iri(iri, context)
                if p:
                    used.add(p)
            if is_named_node(q.object):
                p = get_prefix_from_iri(q.object.value, context)
                if p:
                    used.add(p)
            if is_literal(q.object) and q.object.datatype:
                p = get_prefix_from_iri(q.object.datatype.value, context)
                if p:
                    used.add(p)
    return used


def generate_prefix_declaration(prefix: str, namespace: str) -> str:
    return f'[{prefix}] <{namespace}>\n'


def generate_deterministic_prefixes(context: dict, used_prefixes: set) -> str:
    text = ''
    for prefix, ns in sorted(context.items()):
        if (prefix != '@vocab' and not prefix.startswith('@')
                and prefix not in DEFAULT_CONTEXT and prefix in used_prefixes):
            text += generate_prefix_declaration(prefix, ns)
    return text


def sort_quads_by_predicate(quads: list) -> list:
    return sorted(quads, key=lambda q: q.predicate.value)


def sort_quads_deterministically(quads: list) -> list:
    return sorted(quads, key=lambda q: (q.subject.value, q.predicate.value, q.object.value))


def filter_quads_by_type(quads: list) -> dict:
    types, literals, objects = [], [], []
    for q in quads:
        if is_rdf_type(q.predicate):
            types.append(q)
        elif is_literal(q.object):
            literals.append(q)
        elif is_named_node(q.object):
            objects.append(q)
    return {'types': types, 'literals': literals, 'objects': objects}


def generate_literal_text(quad, context: dict) -> str:
    pred_short = shorten_iri(quad.predicate.value, context)
    annotation = pred_short
    if quad.object.language:
        annotation += f' @{quad.object.language}'
    elif quad.object.datatype and quad.object.datatype.value != XSD_STRING:
        annotation += f' ^^{shorten_iri(quad.object.datatype.value, context)}'

    value = quad.object.value or ''
    datatype = (quad.object.datatype.value if quad.object.datatype else '') or ''

    if '\n' in value:
        return f'~~~ {{{annotation}}}\n{value}\n~~~\n\n'
    if any(t in datatype for t in ('integer', 'decimal', 'double', 'float')):
        return f'`{value}` {{{annotation}}}\n'
    if any(t in datatype for t in ('date', 'time')):
        return f'*{value}* {{{annotation}}}\n'
    if 'boolean' in datatype:
        return f'**{value}** {{{annotation}}}\n'
    return f'[{value}] {{{annotation}}}\n'


def generate_object_text(quad, context: dict, label_lookup: Optional[dict] = None) -> str:
    obj_short  = shorten_iri(quad.object.value, context)
    pred_short = shorten_iri(quad.predicate.value, context)
    display    = (label_lookup.get(quad.object.value) if label_lookup else None) or obj_short
    return f'[{display}] {{+{obj_short} ?{pred_short}}}\n'


def process_predicates(predicates: list, ctx: dict) -> dict:
    literal_props, object_props, reverse_props = [], [], []
    for pred in predicates:
        iri  = pred if isinstance(pred, str) else pred.get('iri', '')
        form = '' if isinstance(pred, str) else pred.get('form', '')
        expanded = expand_iri(iri, ctx)
        shortened = shorten_iri(expanded, ctx)
        if form == '!':
            reverse_props.append(shortened)
        elif form == '?':
            object_props.append(shortened)
        else:
            literal_props.append(shortened)
    return {'literalProps': literal_props, 'objectProps': object_props, 'reverseProps': reverse_props}
