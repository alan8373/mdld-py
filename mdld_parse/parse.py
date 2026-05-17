"""MD-LD parser: text → RDF quads."""
from __future__ import annotations
import re
from typing import Optional

from .constants import (
    DEFAULT_CONTEXT, URL_REGEX,
    STANDALONE_SUBJECT_REGEX, CARRIER_PATTERN_ARRAY,
)
from .utils import (
    DataFactory, expand_iri, quad_index_key, create_literal, hash_str,
)
from .shared import (
    create_carrier,
    parse_sem_cached,
    find_matching_bracket, extract_url_from_brackets,
    extract_attributes_from_text, determine_carrier_type,
    calc_carrier_ranges, extract_clean_text,
    RDF_TYPE, RDF_STATEMENT, RDF_SUBJECT, RDF_PREDICATE, RDF_OBJECT,
    create_lean_origin_entry, resolve_subject, resolve_object,
)
from . import content as _content
from .tokenizer import scan_tokens as _scan_tokens_mdit


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse(first_arg, second_arg=None, **kwargs) -> dict:
    """Parse MD-LD text and return quads, remove list, statements, origin, context, primary_subject."""
    if isinstance(first_arg, dict) and 'text' in first_arg:
        text = first_arg['text']
        opts: dict = {k: v for k, v in first_arg.items() if k != 'text'}
    else:
        text = first_arg
        opts = second_arg or {}
    opts.update(kwargs)

    ctx = {**DEFAULT_CONTEXT, **(opts.get('context') or {})}
    df  = opts.get('dataFactory') or opts.get('data_factory') or DataFactory
    g_raw = opts.get('graph')
    graph = df.named_node(g_raw) if g_raw else df.default_graph()

    state: dict = {
        'ctx':                 ctx,
        'df':                  df,
        'graph':               graph,
        'quads':               [],
        'quad_buffer':         {},
        'remove_set':          set(),
        'origin': {
            'quad_index':        {},
            'blocks':            {},
            'document_structure': [],
        },
        'current_subject':     None,
        'primary_subject':     None,
        'statements':          [],
        'statement_candidates': {},
        'current_block':       None,
        'block_stack':         [],
        'preserve_content':    bool(opts.get('preserve_content')),
        'doc_iri':             opts.get('doc_iri'),
        'content_target_iri':  None,
        'source_text':         text,
    }

    tokens = _scan_tokens_mdit(text)

    for token in tokens:
        if token['type'] == 'prefix':
            iri = token['iri']
            if ':' in iri:
                colon = iri.index(':')
                pot_prefix = iri[:colon]
                ref = iri[colon + 1:]
                if pot_prefix in ctx and pot_prefix != '@vocab':
                    iri = ctx[pot_prefix] + ref
            ctx[token['prefix']] = iri
            # Preserve the source line as a structural block when requested.
            if state.get('preserve_content') and token.get('range'):
                _process_token_with_block_tracking(token, state)
            continue
        processor = _TOKEN_PROCESSORS.get(token['type'])
        if processor:
            processor(token, state)

    # Filter: quads ∩ remove = ∅
    quad_keys = {quad_index_key(q.subject, q.predicate, q.object) for q in state['quads']}
    filtered_remove = [q for q in state['remove_set']
                       if quad_index_key(q.subject, q.predicate, q.object) not in quad_keys]

    return {
        'quads':          state['quads'],
        'remove':         filtered_remove,
        'statements':     state['statements'],
        'origin':         state['origin'],
        'context':        state['ctx'],
        'primary_subject': state['primary_subject'],
    }


# ---------------------------------------------------------------------------
# Inline carrier extraction
# ---------------------------------------------------------------------------

def _get_carriers(token: dict) -> list:
    if token.get('type') == 'code':
        return []
    if token['_carriers'] is None:
        token['_carriers'] = _extract_inline_carriers(token['text'], token['range'][0])
    return token['_carriers']


def _extract_inline_carriers(text: str, base_offset: int = 0) -> list:
    carriers = []
    pos = 0

    while pos < len(text):
        ch = text[pos]

        if ch == '<':
            angle_end = text.find('>', pos)
            if angle_end != -1:
                url = text[pos + 1:angle_end]
                if URL_REGEX.match(url):
                    res = extract_attributes_from_text(text, angle_end + 1, base_offset)
                    c = create_carrier('link', url, res['attrs'], res['attrsRange'],
                                       [base_offset + pos + 1, base_offset + angle_end],
                                       [base_offset + pos, base_offset + res['finalSpanEnd']],
                                       res['finalSpanEnd'], url=url)
                    carriers.append(c)
                    pos = res['finalSpanEnd']
                    continue

        elif ch == '[':
            bracket_end = find_matching_bracket(text, pos)
            if bracket_end is not None:
                carrier_text = text[pos + 1:bracket_end - 1]
                ur = extract_url_from_brackets(text, bracket_end)
                url, span_end = ur['url'], ur['spanEnd']
                res = extract_attributes_from_text(text, span_end, base_offset)
                ct = determine_carrier_type(url)
                if url and url.startswith('='):
                    pos = res['finalSpanEnd']
                    continue
                c = create_carrier(ct['carrierType'], carrier_text, res['attrs'],
                                   res['attrsRange'],
                                   [base_offset + pos + 1, base_offset + bracket_end - 1],
                                   [base_offset + pos, base_offset + res['finalSpanEnd']],
                                   res['finalSpanEnd'], url=ct['resourceIRI'])
                carriers.append(c)
                pos = res['finalSpanEnd']
                continue

        else:
            for ctype, pattern in CARRIER_PATTERN_ARRAY:
                m = pattern.match(text, pos)
                if m and m.start() == pos:
                    rr = calc_carrier_ranges(m, base_offset, pos)
                    carrier_type = 'emphasis' if ctype == 'EMPHASIS' else 'code'
                    c = create_carrier(carrier_type, m.group(1), '{' + m.group(2) + '}',
                                       rr['attrsRange'], rr['valueRange'],
                                       rr['range'], rr['pos'])
                    carriers.append(c)
                    pos = rr['pos']
                    break
            else:
                pos += 1
                continue
            continue

        pos += 1

    return carriers


# ---------------------------------------------------------------------------
# Block entry creation
# ---------------------------------------------------------------------------

def _create_block_entry(token: dict, state: dict) -> dict:
    block_id = token.get('_blockId') or hash_str(
        f"{token['type']}:{token['range'][0]}:{token['range'][1]}")
    token['_blockId'] = block_id

    carriers = _get_carriers(token)
    clean    = extract_clean_text(token)

    block: dict = {
        'id':          block_id,
        'type':        token['type'],
        'range':       token['range'],
        'text':        clean,
        'subject':     None,
        'types':       [],
        'predicates':  [],
        'carriers':    [],
        'listLevel':   token.get('indent', 0),
        'parentBlockId': state['block_stack'][-1] if state['block_stack'] else None,
        'quadKeys':    [],
    }

    for carrier in carriers:
        ci: dict = {
            'type':       carrier['type'],
            'range':      carrier.get('range'),
            'text':       carrier.get('text'),
            'subject':    None,
            'predicates': [],
            'sem':        None,
        }
        if carrier.get('attrs'):
            csem = parse_sem_cached(carrier['attrs'])
            ci['sem']        = csem
            ci['predicates'] = csem.get('predicates', [])
            ci['subject']    = csem.get('subject')
            ci['types']      = csem.get('types', [])
        block['carriers'].append(ci)

    state['origin']['blocks'][block_id] = block
    state['origin']['document_structure'].append(block)

    if state.get('preserve_content'):
        order = len(state['origin']['document_structure']) - 1
        node = _content.build_block_node(token, block_id, order, carriers,
                                         source_text=state.get('source_text'))
        state['quads'].extend(node.to_quads(doc_iri=state.get('doc_iri')))

    return block


def _create_synthetic_block(subject_val: str, sem: dict, carrier: dict,
                             state: dict) -> dict:
    types      = sem.get('types', [])
    predicates = sem.get('predicates', [])
    ctx        = state['ctx']

    exp_types = [expand_iri(t['iri'] if isinstance(t, dict) else t, ctx) for t in types]
    exp_preds = [{'iri': expand_iri(p['iri'], ctx), 'form': p.get('form', '')} for p in predicates]

    sig = '|'.join([subject_val, carrier.get('type') or 'unknown',
                    ','.join(exp_types),
                    ','.join(f"{p['form']}{p['iri']}" for p in exp_preds)])
    block_id = hash_str(sig)

    return {
        'id':          block_id,
        'range':       {'start': carrier['range'][0], 'end': carrier['range'][1]},
        'carrierType': carrier.get('type'),
        'subject':     subject_val,
        'types':       exp_types,
        'predicates':  exp_preds,
        'context':     ctx,
        'text':        carrier.get('text', ''),
    }


# ---------------------------------------------------------------------------
# Quad emission
# ---------------------------------------------------------------------------

def _emit_quad(state: dict, block: dict, subject, predicate, object_,
               meta: Optional[dict] = None) -> None:
    if not subject or not predicate or not object_:
        return

    df   = state['df']
    quad = df.quad(subject, predicate, object_)
    remove = bool(meta and meta.get('remove'))
    key  = quad_index_key(quad.subject, quad.predicate, quad.object)

    if remove:
        if key in state['quad_buffer']:
            del state['quad_buffer'][key]
            state['quads'] = [q for q in state['quads']
                              if quad_index_key(q.subject, q.predicate, q.object) != key]
            state['origin']['quad_index'].pop(key, None)
        else:
            state['remove_set'].add(quad)
    else:
        state['quad_buffer'][key] = quad
        state['quads'].append(quad)

        if state.get('preserve_content') and state.get('content_target_iri'):
            state['quads'].append(
                _content.annotate_triple(quad, state['content_target_iri']))

        _detect_statement(quad, df, state['statements'], state['statement_candidates'])

        origin_entry = create_lean_origin_entry(block, subject, predicate, meta)
        state['origin']['quad_index'][key] = origin_entry

        cb = state.get('current_block')
        if cb and block.get('id') == cb.get('id'):
            cb.setdefault('quadKeys', []).append(key)


# ---------------------------------------------------------------------------
# rdf:Statement detection
# ---------------------------------------------------------------------------

def _detect_statement(quad, df, statements: list, candidates: dict) -> None:
    pred = quad.predicate.value

    if pred not in (RDF_TYPE, RDF_SUBJECT, RDF_PREDICATE, RDF_OBJECT):
        return

    if pred == RDF_TYPE and quad.object.value == RDF_STATEMENT:
        candidates[quad.subject.value] = {'spo': {}}
        return

    candidate = candidates.get(quad.subject.value)
    if not candidate:
        return

    if pred == RDF_SUBJECT:
        candidate['spo']['subject'] = quad.object
    elif pred == RDF_PREDICATE:
        candidate['spo']['predicate'] = quad.object
    elif pred == RDF_OBJECT:
        candidate['spo']['object'] = quad.object

    spo = candidate['spo']
    if spo.get('subject') and spo.get('predicate') and spo.get('object'):
        statements.append(df.quad(spo['subject'], spo['predicate'], spo['object']))
        del candidates[quad.subject.value]


# ---------------------------------------------------------------------------
# Annotation processing
# ---------------------------------------------------------------------------

def _process_annotation(carrier: dict, sem: dict, state: dict,
                         preserve_global_subject: bool = False,
                         implicit_subject=None) -> None:
    if sem.get('subject') == 'RESET':
        state['current_subject'] = None
        return

    previous_subject = state['current_subject']
    new_subject = resolve_subject(sem, state)
    local_object = resolve_object(sem, state)

    # Track primary subject: first non-fragment subject
    if (new_subject and not state['primary_subject']
            and not (sem.get('subject') or '').startswith('=#')):
        state['primary_subject'] = new_subject.value

    if new_subject and not preserve_global_subject and not implicit_subject:
        state['current_subject'] = new_subject

    S = (new_subject or previous_subject) if preserve_global_subject else (
        implicit_subject or state['current_subject'])
    if not S:
        return

    block  = _create_synthetic_block(S.value, sem, carrier, state)
    L      = create_literal(carrier.get('text', ''), sem.get('datatype'),
                            sem.get('language'), state['ctx'], state['df'])
    url    = carrier.get('url')
    carrier_o = state['df'].named_node(expand_iri(url, state['ctx'])) if url else None
    new_sub_or_carrier_o = new_subject or carrier_o

    # enrich current block with semantic info
    cb = state.get('current_block')
    if cb:
        if new_subject and sem.get('subject') not in (None, 'RESET'):
            cb['subject'] = new_subject.value
        for t in sem.get('types', []):
            tiri = expand_iri(t['iri'] if isinstance(t, dict) else t, state['ctx'])
            if tiri not in cb.get('types', []):
                cb.setdefault('types', []).append(tiri)
        for p in sem.get('predicates', []):
            cb.setdefault('predicates', []).append({
                'iri':  expand_iri(p['iri'], state['ctx']),
                'form': p.get('form', ''),
            })

    _process_types(sem, new_subject, local_object, carrier_o, S, block, state, carrier)
    _process_predicates(sem, new_subject, previous_subject, local_object,
                        new_sub_or_carrier_o, S, L, block, state, carrier)


def _process_types(sem: dict, new_subject, local_object, carrier_o, S,
                   block: dict, state: dict, carrier: dict) -> None:
    for t in sem.get('types', []):
        tiri = t['iri'] if isinstance(t, dict) else t
        type_info = t if isinstance(t, dict) else {'entryIndex': None, 'remove': False}
        # priority: explicit subject > soft object > carrier URL > current subject
        type_subject = new_subject or local_object or carrier_o or S
        expanded = expand_iri(tiri, state['ctx'])
        _emit_quad(state, block, type_subject,
                   state['df'].named_node(expand_iri('rdf:type', state['ctx'])),
                   state['df'].named_node(expanded),
                   {'kind': 'type', 'remove': type_info.get('remove', False)})


def _determine_predicate_role(pred: dict, carrier: dict, new_subject, previous_subject,
                               local_object, new_sub_or_carrier_o, S, L) -> Optional[dict]:
    form = pred.get('form', '')
    url  = carrier.get('url')
    # skip literal predicates for angle-bracket URLs (text == url)
    if (form == '' and carrier.get('type') == 'link'
            and url and carrier.get('text') == url):
        return None

    if form == '':
        if new_subject:
            return {'subject': local_object or S, 'object': L}
        if carrier.get('type') == 'link' and url and carrier.get('text') != url:
            return {'subject': new_sub_or_carrier_o, 'object': L}
        return {'subject': local_object or S, 'object': L}

    if form == '?':
        return {'subject': previous_subject if new_subject else S,
                'object': local_object or new_sub_or_carrier_o}

    if form == '!':
        return {'subject': local_object or new_sub_or_carrier_o,
                'object': previous_subject if new_subject else S}

    return None


def _process_predicates(sem: dict, new_subject, previous_subject, local_object,
                         new_sub_or_carrier_o, S, L, block: dict, state: dict,
                         carrier: dict) -> None:
    for pred in sem.get('predicates', []):
        role = _determine_predicate_role(pred, carrier, new_subject, previous_subject,
                                          local_object, new_sub_or_carrier_o, S, L)
        if role:
            P = state['df'].named_node(expand_iri(pred['iri'], state['ctx']))
            _emit_quad(state, block, role['subject'], P, role['object'],
                       {'kind': 'pred', 'form': pred.get('form', ''),
                        'remove': pred.get('remove', False)})


# ---------------------------------------------------------------------------
# Token annotation processing
# ---------------------------------------------------------------------------

def _process_token_annotations(token: dict, state: dict, token_type: str) -> None:
    block_id = token.get('_blockId')
    preserve = state.get('preserve_content')

    if token.get('attrs'):
        sem = parse_sem_cached(token['attrs'])
        if preserve and block_id:
            state['content_target_iri'] = _content.block_iri(block_id)
        _process_annotation({
            'type':       token_type,
            'text':       token['text'],
            'range':      token['range'],
            'attrsRange': token.get('attrsRange'),
            'valueRange': token.get('valueRange'),
        }, sem, state)
        state['content_target_iri'] = None

    for carrier in _get_carriers(token):
        if carrier.get('attrs'):
            sem = parse_sem_cached(carrier['attrs'])
            if preserve and block_id and carrier.get('range'):
                pid = _content.part_id_for_carrier(block_id, carrier['range'])
                state['content_target_iri'] = _content.part_iri(block_id, pid)
            _process_annotation(carrier, sem, state)
            state['content_target_iri'] = None


def _process_standalone_subject(token: dict, state: dict) -> None:
    m = STANDALONE_SUBJECT_REGEX.match(token['text'])
    if not m:
        return
    sem = parse_sem_cached('{=' + m.group(1) + '}')
    attrs_start = token['range'][0] + token['text'].find('{=')
    block_id = token.get('_blockId')
    if state.get('preserve_content') and block_id:
        state['content_target_iri'] = _content.block_iri(block_id)
    _process_annotation({
        'type':       'standalone',
        'text':       '',
        'range':      token['range'],
        'attrsRange': [attrs_start, attrs_start + (len(m.group(1)) if m.group(1) else 0)],
        'valueRange': None,
    }, sem, state)
    state['content_target_iri'] = None


def _process_token_with_block_tracking(token: dict, state: dict, extra_processors=()) -> None:
    block = _create_block_entry(token, state)
    state['current_block'] = block
    state['block_stack'].append(block['id'])

    for proc in extra_processors:
        proc(token, state)

    _process_token_annotations(token, state, token['type'])

    state['block_stack'].pop()
    state['current_block'] = (
        state['origin']['blocks'].get(state['block_stack'][-1])
        if state['block_stack'] else None
    )


_TOKEN_PROCESSORS = {
    'heading':   lambda t, s: _process_token_with_block_tracking(t, s),
    'code':      lambda t, s: _process_token_with_block_tracking(t, s),
    'blockquote':lambda t, s: _process_token_with_block_tracking(t, s),
    'list':      lambda t, s: _process_token_with_block_tracking(t, s),
    'para':      lambda t, s: _process_token_with_block_tracking(
        t, s, extra_processors=[_process_standalone_subject]),
    # 'blank', 'hr', and 'html' only emit structural quads when
    # preserve_content is set; their block-tracking pass is a no-op
    # semantically.
    'blank':     lambda t, s: _process_token_with_block_tracking(t, s)
                  if s.get('preserve_content') else None,
    'hr':        lambda t, s: _process_token_with_block_tracking(t, s)
                  if s.get('preserve_content') else None,
    'html':      lambda t, s: _process_token_with_block_tracking(t, s)
                  if s.get('preserve_content') else None,
    'table':     lambda t, s: _process_token_with_block_tracking(t, s)
                  if s.get('preserve_content') else None,
    'frontmatter': lambda t, s: _process_token_with_block_tracking(t, s)
                    if s.get('preserve_content') else None,
    'reflink':   lambda t, s: _process_token_with_block_tracking(t, s)
                  if s.get('preserve_content') else None,
}
