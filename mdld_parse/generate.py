"""generate: convert RDF quads back into MD-LD text (round-trip safe)."""
from __future__ import annotations
from typing import Optional

from .constants import DEFAULT_CONTEXT
from .utils import DataFactory, shorten_iri, NamedNode
from .shared import (
    is_literal, is_named_node, is_rdf_type,
    collect_used_prefixes, generate_prefix_declaration,
    generate_literal_text, generate_object_text,
    sort_quads_by_predicate, filter_quads_by_type,
)


_RDFS_LABEL = 'http://www.w3.org/2000/01/rdf-schema#label'


def extract_local_name(iri: str, ctx: Optional[dict] = None) -> str:
    if not iri:
        return iri
    ctx = ctx or {}
    for _prefix, ns in ctx.items():
        if iri.startswith(ns) or iri.startswith(ns[:-1]):
            return iri[len(ns):]
    for sep in ('#', '/', ':'):
        idx = iri.rfind(sep)
        if idx != -1 and idx < len(iri) - 1:
            return iri[idx + 1:]
    return iri


def _normalize_and_sort(quads: list) -> list:
    norm = []
    for q in quads:
        norm.append({
            'subject':   DataFactory.from_term(q.subject if hasattr(q, 'subject') else q['subject']),
            'predicate': DataFactory.from_term(q.predicate if hasattr(q, 'predicate') else q['predicate']),
            'object':    DataFactory.from_term(q.object if hasattr(q, 'object') else q['object']),
        })

    def key(q):
        return (q['subject'].value, q['predicate'].value, q['object'].value)

    return sorted(norm, key=key)


def _group_by_subject(quads: list) -> dict:
    groups: dict = {}
    for q in quads:
        groups.setdefault(q['subject'].value, []).append(_DictQuad(q))
    return groups


def _group_by_node(quads: list) -> dict:
    groups: dict = {}
    rdf_type = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'

    def ensure(k):
        return groups.setdefault(k, [])

    for q in quads:
        s = q['subject']
        p = q['predicate']
        o = q['object']
        wrapped = _DictQuad(q)

        ensure(s.value).append(wrapped)
        if o.term_type == 'NamedNode':
            ensure(o.value).append(wrapped)
        ensure(p.value).append(wrapped)
        if p.value == rdf_type and o.term_type == 'NamedNode':
            ensure(o.value).append(wrapped)
        if o.term_type == 'Literal' and o.datatype:
            ensure(o.datatype.value).append(wrapped)
    return groups


class _DictQuad:
    """Lightweight wrapper that exposes .subject, .predicate, .object accessors."""
    __slots__ = ('subject', 'predicate', 'object')

    def __init__(self, q):
        if isinstance(q, dict):
            self.subject   = q['subject']
            self.predicate = q['predicate']
            self.object    = q['object']
        else:
            self.subject   = q.subject
            self.predicate = q.predicate
            self.object    = q.object


def _build_label_lookup(subject_groups: dict) -> dict:
    lookup: dict = {}
    for quads in subject_groups.values():
        for q in quads:
            if q.predicate.value == _RDFS_LABEL and q.object.term_type == 'Literal':
                lookup[q.subject.value] = q.object.value
    return lookup


def _build_deterministic_mdld(subject_groups: dict, context: dict,
                               primary_subject: Optional[str] = None) -> dict:
    text = ''
    used_prefixes = collect_used_prefixes(subject_groups, context)
    label_lookup  = _build_label_lookup(subject_groups)

    for prefix, ns in sorted(context.items()):
        if (prefix != '@vocab' and not prefix.startswith('@')
                and prefix not in DEFAULT_CONTEXT and prefix in used_prefixes):
            text += generate_prefix_declaration(prefix, ns)

    if context:
        text += '\n'

    sorted_subjects = sorted(subject_groups.keys())
    if primary_subject:
        ordered = [primary_subject] + [s for s in sorted_subjects if s != primary_subject]
    else:
        ordered = sorted_subjects

    for subject_iri in ordered:
        subject_quads = subject_groups.get(subject_iri)
        if not subject_quads:
            continue

        short_subject = shorten_iri(subject_iri, context)
        bucket = filter_quads_by_type(subject_quads)
        types     = bucket['types']
        literals  = bucket['literals']
        objects   = bucket['objects']

        has_label = subject_iri in label_lookup
        display = label_lookup[subject_iri] if has_label else extract_local_name(subject_iri, context)

        annotations = ' '.join(sorted('.' + shorten_iri(t.object.value, context)
                                      for t in types)) if types else ''
        if has_label:
            annotations = (annotations + ' ' if annotations else '') + 'label'
        annot_str = ' ' + annotations if annotations else ''
        text += f'# {display} {{={short_subject}{annot_str}}}\n\n'

        heading_label = label_lookup.get(subject_iri) if has_label else None
        for q in sort_quads_by_predicate(literals):
            if q.predicate.value == _RDFS_LABEL and q.object.value == heading_label:
                continue
            text += generate_literal_text(q, context)

        for q in sort_quads_by_predicate(objects):
            text += generate_object_text(q, context, label_lookup)

        text += '\n'

    return {'text': text}


def generate(quads=None, *, context=None, primary_subject=None,
             primarySubject=None, **kwargs) -> dict:
    """Convert RDF quads into MD-LD text.

    Accepts either a list of quads as first arg, or a dict-style call::

        generate({'quads': ..., 'context': ..., 'primary_subject': ...})
    """
    if isinstance(quads, dict):
        d = quads
        quads = d.get('quads')
        context = context if context is not None else d.get('context')
        primary_subject = (
            primary_subject
            or d.get('primary_subject')
            or d.get('primarySubject')
        )
    primary_subject = primary_subject or primarySubject

    full_context = {**DEFAULT_CONTEXT, **(context or {})}
    norm_quads   = _normalize_and_sort(quads or [])
    subject_groups = _group_by_subject(norm_quads)

    effective_primary = primary_subject
    if not effective_primary and norm_quads:
        effective_primary = norm_quads[0]['subject'].value

    result = _build_deterministic_mdld(subject_groups, full_context, effective_primary)
    return {'text': result['text'], 'context': full_context}


def generate_node(quads=None, *, focus_iri=None, focusIRI=None, context=None, **kwargs) -> dict:
    """Generate node-centric MDLD showing every quad where *focus_iri* appears."""
    if isinstance(quads, dict):
        d = quads
        quads     = d.get('quads')
        focus_iri = focus_iri or d.get('focus_iri') or d.get('focusIRI')
        context   = context if context is not None else d.get('context')
    focus_iri = focus_iri or focusIRI

    if not quads or not focus_iri:
        return {'text': '', 'context': {**DEFAULT_CONTEXT, **(context or {})}}

    full_context = {**DEFAULT_CONTEXT, **(context or {})}
    norm_quads   = _normalize_and_sort(quads)
    node_groups  = _group_by_node(norm_quads)

    if focus_iri not in node_groups:
        return {'text': '', 'context': full_context}

    result = _build_deterministic_mdld(node_groups, full_context, focus_iri)
    return {'text': result['text'], 'context': full_context}
