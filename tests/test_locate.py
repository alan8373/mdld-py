"""Locate tests, transliterated from tests/locate.tests.js."""
from __future__ import annotations
from textwrap import dedent

from mdld_parse import parse, locate, generate, DataFactory


def test_basic_quad_location_with_origin():
    mdld = dedent("""\
        [ex] <http://example.org/>

        # Article {=ex:article .ex:Article}

        > Alice Smith {author}
        > 2024-01-01 {datePublished}""")
    result = parse({'text': mdld})
    author_q = next(q for q in result['quads']
                    if q.subject.value == 'http://example.org/article'
                    and q.predicate.value == 'http://www.w3.org/2000/01/rdf-schema#author')
    location = locate(author_q, result['origin'])
    assert location is not None
    assert location['carrierType'] == 'blockquote'
    assert isinstance(location['blockId'], str)
    assert location['subject'] == 'http://example.org/article'
    assert location['value'] == 'Alice Smith'
    assert location['polarity'] == '+'


def test_auto_origin_locate_for_known_quad():
    mdld = dedent("""\
        [ex] <http://example.org/>

        # Person {=ex:alice .ex:Person}

        > Alice Smith {name}
        > 25 {age ^^xsd:integer}""")
    result = parse({'text': mdld})
    name_q = next(q for q in result['quads']
                  if q.predicate.value == 'http://www.w3.org/2000/01/rdf-schema#name')
    location = locate(name_q, result['origin'])
    assert location['carrierType'] == 'blockquote'
    assert location['value'] == 'Alice Smith'
    assert location['polarity'] == '+'


def test_type_annotation_in_heading():
    mdld = dedent("""\
        [ex] <http://example.org/>

        # Document {=ex:doc .ex:Document label}""")
    result = parse({'text': mdld})
    type_q = next(q for q in result['quads']
                  if q.predicate.value == 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type')
    location = locate(type_q, result['origin'])
    assert location['carrierType'] == 'heading'
    assert location['value'] == 'Document'
    assert location['polarity'] == '+'


def test_object_reference_in_blockquote():
    mdld = dedent("""\
        [ex] <http://example.org/>

        # Article {=ex:article .ex:Article}

        > alice {+ex:alice ?author}""")
    result = parse({'text': mdld})
    obj_q = next(q for q in result['quads']
                 if q.predicate.value == 'http://www.w3.org/2000/01/rdf-schema#author')
    location = locate(obj_q, result['origin'])
    assert location['carrierType'] == 'blockquote'
    assert location['value'] == 'alice'
    assert location['polarity'] == '+'


def test_literal_with_datatype():
    mdld = dedent("""\
        [ex] <http://example.org/>

        # Person {=ex:person .ex:Person}

        > 25 {age ^^xsd:integer}""")
    result = parse({'text': mdld})
    age_q = next(q for q in result['quads']
                 if q.predicate.value == 'http://www.w3.org/2000/01/rdf-schema#age')
    location = locate(age_q, result['origin'])
    assert location['carrierType'] == 'blockquote'
    assert location['value'] == '25'
    assert location['polarity'] == '+'


def test_non_existent_quad_returns_none():
    mdld = dedent("""\
        [ex] <http://example.org/>

        # Article {=ex:article .ex:Article}

        > Alice Smith {author}""")
    result = parse({'text': mdld})
    fake = DataFactory.quad(
        DataFactory.named_node('http://example.org/nonexistent'),
        DataFactory.named_node('http://schema.org/fake'),
        DataFactory.literal('fake'),
    )
    assert locate(fake, result['origin']) is None


def test_quad_in_generated_mdld():
    quads = [
        DataFactory.quad(
            DataFactory.named_node('http://example.org/project'),
            DataFactory.named_node('http://www.w3.org/1999/02/22-rdf-syntax-ns#type'),
            DataFactory.named_node('http://example.org/Project')),
        DataFactory.quad(
            DataFactory.named_node('http://example.org/project'),
            DataFactory.named_node('http://www.w3.org/2000/01/rdf-schema#label'),
            DataFactory.literal('Web Application')),
    ]
    gen = generate(quads=quads, context={'ex': 'http://example.org/'})
    result = parse({'text': gen['text']})
    label_q = next(q for q in result['quads']
                   if q.predicate.value == 'http://www.w3.org/2000/01/rdf-schema#label')
    location = locate(label_q, result['origin'])
    assert location is not None
    assert location['carrierType'] == 'heading'
    assert location['value'] == 'Web Application'


def test_complex_few_shot_example():
    mdld = dedent("""\
        [ex] <http://example.org/>

        # Project Alpha {=ex:ProjectAlpha .ex:Project}

        [Design schema] {label}""")
    result = parse({'text': mdld})
    label_q = next(q for q in result['quads']
                   if q.subject.value == 'http://example.org/ProjectAlpha'
                   and q.predicate.value == 'http://www.w3.org/2000/01/rdf-schema#label')
    location = locate(label_q, result['origin'])
    assert location is not None
    assert location['carrierType'] == 'span'
    assert location['value'] == 'Design schema'


def test_multiple_parameter_patterns():
    mdld = dedent("""\
        [ex] <http://example.org/>

        # Test {=ex:test .ex:Test}

        > value {property} """)
    result = parse({'text': mdld})
    quad = result['quads'][0]
    assert locate(quad, result['origin']) is not None
    assert locate(quad) is None


def test_range_precision():
    mdld = dedent("""\
        [ex] <http://example.org/>

        # Article {=ex:article .ex:Article}

        [Alice Smith] {author}""")
    result = parse({'text': mdld})
    author_q = next(q for q in result['quads']
                    if q.subject.value == 'http://example.org/article'
                    and q.predicate.value == 'http://www.w3.org/2000/01/rdf-schema#author')
    location = locate(author_q, result['origin'])
    rng = location['range']
    start = rng['start'] if isinstance(rng, dict) else rng[0]
    end   = rng['end']   if isinstance(rng, dict) else rng[1]
    assert start >= 0
    assert end <= len(mdld)
    assert start < end
    assert location['value'] == 'Alice Smith'
