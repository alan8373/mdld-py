"""Origin-lean tests, transliterated from tests/origin-lean.tests.js."""
from __future__ import annotations
from textwrap import dedent

from mdld_parse import parse, locate


def test_origin_only_quad_index_present():
    mdld = dedent("""\
        [ex] <http://example.org/>

        # Article {=ex:article .ex:Article}

        > Alice Smith {author}
        > 2024-01-01 {datePublished}""")
    result = parse({'text': mdld})
    origin = result['origin']
    assert isinstance(origin['quad_index'], dict)
    # Lean origin: no extra structures expected
    assert 'quadMap' not in origin
    assert 'entries' not in origin


def test_origin_entry_structure_matches_spec():
    mdld = dedent("""\
        [ex] <http://example.org/>

        # Person {=ex:alice .ex:Person}

        > Alice Smith {name}""")
    result = parse({'text': mdld})
    name_q = next(q for q in result['quads']
                  if q.predicate.value == 'http://www.w3.org/2000/01/rdf-schema#name')
    loc = locate(name_q, result['origin'])
    assert loc['predicate'] == 'http://www.w3.org/2000/01/rdf-schema#name'

    assert isinstance(loc['blockId'], str)
    rng = loc['range']
    assert isinstance(rng, dict)
    assert isinstance(rng['start'], int)
    assert isinstance(rng['end'], int)
    assert isinstance(loc['carrierType'], str)
    assert isinstance(loc['subject'], str)
    assert isinstance(loc['predicate'], str)
    assert loc['polarity'] == '+'
    assert isinstance(loc['context'], dict)
    assert isinstance(loc['value'], str)


def test_multiple_quads_share_block_id():
    mdld = dedent("""\
        [ex] <http://example.org/>

        # Article {=ex:article .ex:Article .ex:PublishedContent}

        [Alice Smith] {author datePublished}""")
    result = parse({'text': mdld})
    author_q = next(q for q in result['quads']
                    if q.predicate.value == 'http://www.w3.org/2000/01/rdf-schema#author')
    date_q = next(q for q in result['quads']
                  if q.predicate.value == 'http://www.w3.org/2000/01/rdf-schema#datePublished')
    a_loc = locate(author_q, result['origin'])
    d_loc = locate(date_q, result['origin'])
    assert a_loc['blockId'] == d_loc['blockId']
    assert a_loc['carrierType'] == 'span'
    assert d_loc['carrierType'] == 'span'


def test_different_carrier_types():
    mdld = dedent("""\
        [ex] <http://example.org/>

        # Document {=ex:doc .ex:Document}

        [Design spec] {label}
        > alice {+ex:alice ?author}""")
    result = parse({'text': mdld})
    type_q = next(q for q in result['quads']
                  if q.predicate.value == 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type')
    label_q = next(q for q in result['quads']
                   if q.predicate.value == 'http://www.w3.org/2000/01/rdf-schema#label')
    author_q = next(q for q in result['quads']
                    if q.predicate.value == 'http://www.w3.org/2000/01/rdf-schema#author')
    assert locate(type_q, result['origin'])['carrierType'] == 'heading'
    assert locate(label_q, result['origin'])['carrierType'] == 'span'
    assert locate(author_q, result['origin'])['carrierType'] == 'blockquote'


def test_origin_range_precision():
    mdld = dedent("""\
        [ex] <http://example.org/>

        # Article {=ex:article .ex:Article}

        > Alice Smith {author}""")
    result = parse({'text': mdld})
    author_q = next(q for q in result['quads']
                    if q.predicate.value == 'http://www.w3.org/2000/01/rdf-schema#author')
    loc = locate(author_q, result['origin'])
    rng = loc['range']
    start = rng['start']; end = rng['end']
    assert start >= 0
    assert end <= len(mdld)
    assert start < end
    assert 'Alice Smith' in mdld[start:end]


def test_origin_context_inheritance():
    mdld = dedent("""\
        [ex] <http://example.org/>

        # Article {=ex:article .ex:Article}

        > Alice Smith {author}""")
    result = parse({'text': mdld})
    author_q = next(q for q in result['quads']
                    if q.predicate.value == 'http://www.w3.org/2000/01/rdf-schema#author')
    loc = locate(author_q, result['origin'])
    assert loc['context']['ex'] == 'http://example.org/'


def test_origin_value_field_content():
    mdld = dedent("""\
        [ex] <http://example.org/>

        # Person {=ex:person .ex:Person}

        > Alice Smith {name}
        > 25 {age ^^xsd:integer}
        > alice {+ex:alice ?knows}""")
    result = parse({'text': mdld})
    name_q = next(q for q in result['quads']
                  if q.predicate.value == 'http://www.w3.org/2000/01/rdf-schema#name')
    age_q = next(q for q in result['quads']
                 if q.predicate.value == 'http://www.w3.org/2000/01/rdf-schema#age')
    knows_q = next(q for q in result['quads']
                   if q.predicate.value == 'http://www.w3.org/2000/01/rdf-schema#knows')
    assert locate(name_q, result['origin'])['value'] == 'Alice Smith'
    assert locate(age_q, result['origin'])['value'] == '25'
    assert locate(knows_q, result['origin'])['value'] == 'alice'
