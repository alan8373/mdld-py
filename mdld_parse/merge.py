"""merge: combine multiple MD-LD documents with diff-polarity resolution."""
from __future__ import annotations
from .parse import parse
from .utils import quad_to_key_for_origin
from .constants import DEFAULT_CONTEXT


def _quad_key(quad) -> str:
    return quad_to_key_for_origin(quad)


def _normalize_input(inp, options: dict, doc_context: dict):
    """Return a ParseResult dict for *inp* (string or existing ParseResult)."""
    if isinstance(inp, str):
        ctx = {**doc_context, **(options.get('context') or {})}
        return parse(inp, {'context': ctx})
    # Already a ParseResult dict
    return inp


def merge(docs, options=None) -> dict:
    """Merge a list of MD-LD documents (strings or ParseResults).

    Returns a dict with quads, remove, statements, origin, context, primarySubjects.
    """
    if options is None:
        options = {}

    session_buffer: dict = {}
    session_remove: set = set()
    all_documents: list = []
    quad_index: dict = {}
    all_statements: list = []
    accumulated_context: dict = {}
    primary_subjects: list = []

    for i, inp in enumerate(docs):
        doc_context = {**DEFAULT_CONTEXT, **(options.get('context') or {})}
        doc = _normalize_input(inp, options, doc_context)

        # Accumulate context
        for prefix, ns in (doc.get('context') or {}).items():
            if prefix not in accumulated_context and prefix not in DEFAULT_CONTEXT:
                accumulated_context[prefix] = ns

        all_documents.append({
            'index': i,
            'input': 'string' if isinstance(inp, str) else 'ParseResult',
            'origin': doc.get('origin'),
            'context': doc.get('context'),
            'statementsCount': len(doc.get('statements') or []),
        })

        if doc.get('statements'):
            all_statements.extend(doc['statements'])

        ps = doc.get('primary_subject') or doc.get('primarySubject')
        if ps:
            primary_subjects.append(ps)

        for quad in (doc.get('quads') or []):
            key = _quad_key(quad)
            session_buffer[key] = quad
            existing = (doc.get('origin') or {}).get('quad_index', {}).get(key)
            quad_index[key] = {**(existing or {}), 'documentIndex': i, 'polarity': '+'}

        for quad in (doc.get('remove') or []):
            key = _quad_key(quad)
            if key in session_buffer:
                del session_buffer[key]
            else:
                session_remove.add(quad)
            existing = (doc.get('origin') or {}).get('quad_index', {}).get(key)
            quad_index[key] = {**(existing or {}), 'documentIndex': i, 'polarity': '-'}

    final_quads = list(session_buffer.values())
    final_remove = list(session_remove)

    # Hard invariant: quads ∩ remove = ∅
    quad_keys = {_quad_key(q) for q in final_quads}
    final_quads  = [q for q in final_quads  if _quad_key(q) not in {_quad_key(r) for r in final_remove}]
    final_remove = [q for q in final_remove if _quad_key(q) not in quad_keys]

    final_context = {
        **DEFAULT_CONTEXT,
        **(options.get('context') or {}),
        **accumulated_context,
    }

    return {
        'quads':           final_quads,
        'remove':          final_remove,
        'statements':      all_statements,
        'origin':          {'documents': all_documents, 'quad_index': quad_index},
        'context':         final_context,
        'primarySubjects': primary_subjects,
    }
