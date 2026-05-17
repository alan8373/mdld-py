from __future__ import annotations
import re
import random
import string
import warnings
from typing import Optional

from .constants import URL_REGEX, DEFAULT_CONTEXT

_VALID_URI_SCHEMES = re.compile(r'^(https?|ftp|mailto|tag|nih|urn|uuid|did|web|ipfs|ipns|data|file):')


# ---------------------------------------------------------------------------
# RDF/JS-compatible term classes
# ---------------------------------------------------------------------------

class Term:
    __slots__ = ('id', 'term_type', 'value')

    def __init__(self, id_: str) -> None:
        self.id = id_
        self.term_type = ''
        self.value = ''

    def equals(self, other: object) -> bool:
        return (other is not None
                and isinstance(other, Term)
                and self.term_type == other.term_type
                and self.value == other.value)

    def __eq__(self, other: object) -> bool:
        return self.equals(other)

    def __hash__(self) -> int:
        return hash((self.term_type, self.value))

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({self.value!r})'


class NamedNode(Term):
    __slots__ = ()

    def __init__(self, iri: str) -> None:
        super().__init__(iri)
        self.term_type = 'NamedNode'
        self.value = iri


_LITERAL_RE = re.compile(
    r'^"([^"\\]*(?:\\.[^"\\]*)*)"'   # "value"
    r'(?:\^\^([^"@\s]+))?'           # ^^datatype
    r'(?:@([^-\s]+)(?:--(.+))?)?$'   # @lang or @lang--dir
)


class Literal(Term):
    __slots__ = ('language', 'datatype')

    def __init__(self, id_: str) -> None:
        super().__init__(id_)
        self.term_type = 'Literal'
        self.language: str = ''
        self.datatype: Optional[NamedNode] = None

        m = _LITERAL_RE.match(id_)
        if m:
            self.value = m.group(1).replace('\\"', '"').replace('\\\\', '\\')
            lang = m.group(3)
            dt   = m.group(2)
            if lang:
                self.language = lang
                self.datatype = NamedNode('http://www.w3.org/1999/02/22-rdf-syntax-ns#langString')
            elif dt:
                self.datatype = NamedNode(dt)
            else:
                self.datatype = NamedNode('http://www.w3.org/2001/XMLSchema#string')
        else:
            self.value = id_.strip('"')
            self.datatype = NamedNode('http://www.w3.org/2001/XMLSchema#string')

    def equals(self, other: object) -> bool:
        if not isinstance(other, Literal):
            return False
        return (self.value == other.value
                and self.language == other.language
                and (self.datatype.value if self.datatype else None)
                    == (other.datatype.value if other.datatype else None))

    def __hash__(self) -> int:
        return hash((self.term_type, self.value, self.language,
                     self.datatype.value if self.datatype else None))


class BlankNode(Term):
    __slots__ = ()

    def __init__(self, name: Optional[str] = None) -> None:
        n = name or 'b' + ''.join(random.choices(string.ascii_lowercase + string.digits, k=9))
        super().__init__(n)
        self.term_type = 'BlankNode'
        self.value = self.id


class Variable(Term):
    __slots__ = ()

    def __init__(self, name: str) -> None:
        super().__init__(name)
        self.term_type = 'Variable'
        self.value = name


class DefaultGraph(Term):
    __slots__ = ()

    def __init__(self) -> None:
        super().__init__('')
        self.term_type = 'DefaultGraph'
        self.value = ''

    def equals(self, other: object) -> bool:
        return isinstance(other, DefaultGraph)


DEFAULTGRAPH = DefaultGraph()


class Quad(Term):
    __slots__ = ('subject', 'predicate', 'object', 'graph')

    def __init__(self, subject: Term, predicate: Term, object_: Term,
                 graph: Term = DEFAULTGRAPH) -> None:
        super().__init__(f'{subject.id}|{predicate.id}|{object_.id}|{graph.id}')
        self.term_type = 'Quad'
        self.subject   = subject
        self.predicate = predicate
        self.object    = object_
        self.graph     = graph

    def equals(self, other: object) -> bool:
        if not isinstance(other, Quad):
            return False
        return (self.subject.equals(other.subject)
                and self.predicate.equals(other.predicate)
                and self.object.equals(other.object)
                and self.graph.equals(other.graph))

    def __hash__(self) -> int:
        return hash(self.id)


# ---------------------------------------------------------------------------
# DataFactory
# ---------------------------------------------------------------------------

_XSD = {
    'boolean': 'http://www.w3.org/2001/XMLSchema#boolean',
    'integer': 'http://www.w3.org/2001/XMLSchema#integer',
    'double':  'http://www.w3.org/2001/XMLSchema#double',
    'string':  'http://www.w3.org/2001/XMLSchema#string',
}


class _DataFactory:
    def named_node(self, iri: str) -> NamedNode:
        return NamedNode(iri)

    def blank_node(self, name: Optional[str] = None) -> BlankNode:
        return BlankNode(name)

    def literal(self, value, language_or_datatype=None) -> Literal:
        sv = str(value)
        esc = sv.replace('\\', '\\\\').replace('"', '\\"')

        if isinstance(language_or_datatype, str):
            return Literal(f'"{esc}"@{language_or_datatype.lower()}')

        if language_or_datatype is not None and not isinstance(language_or_datatype, Term):
            # dict-like object with language/direction
            lang = language_or_datatype.get('language', '').lower()
            direction = language_or_datatype.get('direction', '')
            dir_str = f'--{direction.lower()}' if direction else ''
            return Literal(f'"{esc}"@{lang}{dir_str}')

        datatype = language_or_datatype.value if isinstance(language_or_datatype, Term) else ''
        if not datatype:
            if isinstance(value, bool):
                datatype = _XSD['boolean']
            elif isinstance(value, int):
                datatype = _XSD['integer']
            elif isinstance(value, float):
                import math
                datatype = _XSD['double']
                if not math.isfinite(value):
                    sv = 'INF' if value > 0 else '-INF'
                    esc = sv

        if not datatype or datatype == _XSD['string']:
            return Literal(f'"{esc}"')
        return Literal(f'"{esc}"^^{datatype}')

    def variable(self, name: str) -> Variable:
        return Variable(name)

    def default_graph(self) -> DefaultGraph:
        return DEFAULTGRAPH

    def quad(self, subject: Term, predicate: Term, object_: Term,
             graph: Optional[Term] = None) -> Quad:
        return Quad(subject, predicate, object_, graph or DEFAULTGRAPH)

    # alias
    triple = quad

    def from_term(self, term) -> Term:
        if isinstance(term, Term):
            return term
        tt = term.get('termType') if isinstance(term, dict) else getattr(term, 'term_type', getattr(term, 'termType', ''))
        val = term.get('value') if isinstance(term, dict) else getattr(term, 'value', '')
        if tt == 'NamedNode':
            return NamedNode(val)
        if tt == 'BlankNode':
            return BlankNode(val)
        if tt == 'Variable':
            return Variable(val)
        if tt == 'DefaultGraph':
            return DEFAULTGRAPH
        if tt == 'Literal':
            lang = (term.get('language') if isinstance(term, dict) else getattr(term, 'language', '')) or ''
            dt_raw = term.get('datatype') if isinstance(term, dict) else getattr(term, 'datatype', None)
            dt = (dt_raw.get('value') if isinstance(dt_raw, dict) else getattr(dt_raw, 'value', '')) if dt_raw else ''
            esc = str(val).replace('\\', '\\\\').replace('"', '\\"')
            if lang:
                return Literal(f'"{esc}"@{lang}')
            if dt:
                return Literal(f'"{esc}"^^{dt}')
            return Literal(f'"{esc}"')
        if tt == 'Quad':
            return self.from_quad(term)
        raise ValueError(f'Unexpected termType: {tt}')

    def from_quad(self, in_quad) -> Quad:
        if isinstance(in_quad, Quad):
            return in_quad
        get = (lambda k: in_quad.get(k)) if isinstance(in_quad, dict) else (lambda k: getattr(in_quad, k, None))
        g = get('graph') or DEFAULTGRAPH
        return Quad(
            self.from_term(get('subject')),
            self.from_term(get('predicate')),
            self.from_term(get('object')),
            self.from_term(g),
        )


DataFactory = _DataFactory()


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def hash_str(s: str) -> str:
    """DJB2 hash, 32-bit signed overflow, hex string (max 12 chars)."""
    h = 5381
    for c in s:
        h = ((h << 5) + h + ord(c)) & 0xFFFFFFFF
    if h >= 0x80000000:
        h -= 0x100000000
    return format(abs(h), 'x')[:12]


_iri_cache: dict[str, str] = {}


def expand_iri(term, ctx: dict[str, str]) -> Optional[str]:
    if term is None:
        return None
    raw = term if isinstance(term, str) else getattr(term, 'value', str(term))
    t = raw.strip()
    vocab = ctx.get('@vocab', '')
    prefix_str = ','.join(f'{k}:{v}' for k, v in sorted(ctx.items()) if k != '@vocab')
    cache_key = f'{t}\x00{vocab}\x00{prefix_str}'
    if cache_key in _iri_cache:
        return _iri_cache[cache_key]

    if URL_REGEX.match(t):
        result = t
    elif ':' in t:
        colon = t.index(':')
        prefix, ref = t[:colon], t[colon + 1:]
        if prefix and prefix not in ctx and prefix != '@vocab':
            warnings.warn(f'Undefined prefix "{prefix}" in IRI "{t}" - treating as literal')
        result = ctx[prefix] + ref if prefix in ctx else t
    else:
        result = vocab + t

    _iri_cache[cache_key] = result
    return result


def shorten_iri(iri: str, ctx: dict[str, str]) -> str:
    if not iri or not _VALID_URI_SCHEMES.match(iri):
        return iri
    vocab = ctx.get('@vocab', '')
    if vocab and iri.startswith(vocab):
        return iri[len(vocab):]
    best_prefix, best_ns = '', ''
    for prefix, ns in ctx.items():
        if prefix != '@vocab' and iri.startswith(ns) and len(ns) > len(best_ns):
            best_prefix, best_ns = prefix, ns
    if best_prefix:
        return best_prefix + ':' + iri[len(best_ns):]
    return iri


# Token-pattern table for parse_semantic_block (order matters for prefix matching)
_TOKEN_PATTERNS = [
    ('=#',  'fragment',     None,  lambda t: t[2:]),
    ('+#',  'softFragment', None,  lambda t: t[2:]),
    ('^^',  'datatype',     None,  lambda t: t[2:]),
    ('+',   'object',       None,  lambda t: t[1:]),
    ('@',   'language',     None,  lambda t: t[1:]),
    ('.',   'type',         None,  lambda t: t[1:]),
    ('!',   'property',     '!',   lambda t: t[1:]),
    ('?',   'property',     '?',   lambda t: t[1:]),
]


def parse_semantic_block(raw) -> dict:
    try:
        src = str(raw or '').strip()
        cleaned = src
        if cleaned.startswith('{'):
            cleaned = cleaned[1:]
        if cleaned.endswith('}'):
            cleaned = cleaned[:-1]
        cleaned = cleaned.strip()

        empty = {'subject': None, 'object': None, 'types': [], 'predicates': [],
                 'datatype': None, 'language': None, 'entries': []}
        if not cleaned:
            return empty

        result: dict = {'subject': None, 'object': None, 'types': [], 'predicates': [],
                        'datatype': None, 'language': None, 'entries': []}

        for m in re.finditer(r'\S+', cleaned):
            raw_tok = m.group(0)
            rel_start = 1 + m.start()
            rel_end   = rel_start + len(raw_tok)
            entry_idx = len(result['entries'])

            remove = False
            token = raw_tok
            if token.startswith('-') and len(token) > 1:
                remove = True
                token  = token[1:]

            # subject reset
            if token == '=':
                result['subject'] = 'RESET'
                result['entries'].append({
                    'kind': 'subjectReset',
                    'relRange': {'start': rel_start, 'end': rel_end},
                    'raw': raw_tok,
                })
                continue

            # subject declaration (not fragment)
            if token.startswith('=') and not token.startswith('=#'):
                iri = token[1:]
                result['subject'] = iri
                result['entries'].append({
                    'kind': 'subject', 'iri': iri,
                    'relRange': {'start': rel_start, 'end': rel_end},
                    'raw': raw_tok,
                })
                continue

            # pattern-based tokens
            processed = False
            for pattern, kind, form, extractor in _TOKEN_PATTERNS:
                if token.startswith(pattern):
                    extracted = extractor(token)
                    entry: dict = {'kind': kind,
                                   'relRange': {'start': rel_start, 'end': rel_end},
                                   'raw': raw_tok}

                    if kind == 'fragment':
                        result['subject'] = f'=#{extracted}'
                        entry['fragment'] = extracted
                    elif kind == 'softFragment':
                        result['object'] = f'#{extracted}'
                        entry['fragment'] = extracted
                    elif kind == 'object':
                        result['object'] = extracted
                        entry['iri'] = extracted
                    elif kind == 'datatype':
                        if not result['language']:
                            result['datatype'] = extracted
                        entry['datatype'] = extracted
                    elif kind == 'language':
                        result['language'] = extracted
                        result['datatype'] = None
                        entry['language'] = extracted
                    elif kind == 'type':
                        result['types'].append({'iri': extracted, 'entryIndex': entry_idx, 'remove': remove})
                        entry['iri'] = extracted
                        entry['remove'] = remove
                    elif kind == 'property':
                        result['predicates'].append({'iri': extracted, 'form': form, 'entryIndex': entry_idx, 'remove': remove})
                        entry['iri'] = extracted
                        entry['form'] = form
                        entry['remove'] = remove

                    result['entries'].append(entry)
                    processed = True
                    break

            if not processed:
                result['predicates'].append({'iri': token, 'form': '', 'entryIndex': entry_idx, 'remove': remove})
                result['entries'].append({
                    'kind': 'property', 'iri': token, 'form': '',
                    'relRange': {'start': rel_start, 'end': rel_end},
                    'raw': raw_tok, 'remove': remove,
                })

        return result
    except Exception as e:
        warnings.warn(f'Error parsing semantic block {raw!r}: {e}')
        return {'subject': None, 'object': None, 'types': [], 'predicates': [],
                'datatype': None, 'language': None, 'entries': []}


def quad_index_key(subject: Term, predicate: Term, object_: Term) -> str:
    """Stable key for a quad (subject, predicate, object) triple."""
    dt   = (object_.datatype.value if object_.datatype else '') if object_.term_type == 'Literal' else ''
    lang = (object_.language or '') if object_.term_type == 'Literal' else ''
    return f'{subject.value}\x00{predicate.value}\x00{object_.value}\x00{dt}\x00{lang}'


def quad_to_key_for_origin(q) -> Optional[str]:
    return quad_index_key(q.subject, q.predicate, q.object) if q else None


def create_literal(value: str, datatype: Optional[str], language: Optional[str],
                   context: dict, df: _DataFactory) -> Literal:
    if datatype:
        return df.literal(value, df.named_node(expand_iri(datatype, context)))
    if language:
        return df.literal(value, language)
    return df.literal(value)
