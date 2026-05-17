"""Elevated rdf:Statement tests, transliterated from elevated-statements.tests.js."""
from __future__ import annotations
from textwrap import dedent

from mdld_parse import parse


def test_basic_pattern_with_iris():
    md = dedent("""\
        [ex] <http://example.org/>

        ## Elevated statement {=ex:stmt1 .rdf:Statement}
        **Alice** {+ex:alice ?rdf:subject} *knows* {+ex:knows ?rdf:predicate} **Bob** {+ex:bob ?rdf:object}

        **Alice** {=ex:alice} knows **Bob** {?ex:knows +ex:bob}
        """)
    result = parse({'text': md})
    assert len(result['statements']) == 1
    elevated = result['statements'][0]
    assert elevated.subject.value == 'http://example.org/alice'
    assert elevated.predicate.value == 'http://example.org/knows'
    assert elevated.object.value == 'http://example.org/bob'

    statement_quads = [q for q in result['quads']
                       if q.subject.value == 'http://example.org/stmt1'
                       and q.predicate.value == 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type']
    assert len(statement_quads) == 1


def test_datatypes_and_language_tags_in_statements():
    md = dedent("""\
        [ex] <http://example.org/>

        ## Statement with integer datatype {=ex:stmt2 .rdf:Statement}
        **Alice** {+ex:alice ?rdf:subject} *has age* {+ex:hasAge ?rdf:predicate} **25** {rdf:object ^^xsd:integer}

        ## Statement with language tag {=ex:stmt3 .rdf:Statement}
        **Alice** {+ex:alice ?rdf:subject} *has name* {+ex:hasName ?rdf:predicate} **Alice** {rdf:object @en}
        """)
    result = parse({'text': md})
    assert len(result['statements']) == 2

    age_stmt = next(q for q in result['statements'] if q.predicate.value.endswith('hasAge'))
    assert age_stmt.object.datatype.value == 'http://www.w3.org/2001/XMLSchema#integer'
    assert age_stmt.object.value == '25'

    name_stmt = next(q for q in result['statements'] if q.predicate.value.endswith('hasName'))
    assert name_stmt.object.language == 'en'
    assert name_stmt.object.value == 'Alice'


def test_multiple_and_incomplete_patterns():
    md = dedent("""\
        [ex] <http://example.org/>

        ## Complete statement 1 {=ex:stmt1 .rdf:Statement}
        **Alice** {+ex:alice ?rdf:subject} *knows* {+ex:knows ?rdf:predicate} **Bob** {+ex:bob ?rdf:object}

        ## Complete statement 2 {=ex:stmt2 .rdf:Statement}
        **Charlie** {+ex:charlie ?rdf:subject} *works with* {+ex:works-with ?rdf:predicate} **David** {+ex:david ?rdf:object}

        ## Incomplete statement {=ex:incomplete .rdf:Statement}
        **Eve** {+ex:eve ?rdf:subject} *has age* {+ex:hasAge ?rdf:predicate}
        """)
    result = parse({'text': md})
    assert len(result['statements']) == 2
    objects = [q.object.value for q in result['statements']]
    assert 'http://example.org/bob' in objects
    assert 'http://example.org/david' in objects


def test_real_world_tag_uris_and_foaf():
    md = dedent("""\
        [my] <tag:alice@example.com,2026:>
        [foaf] <http://xmlns.com/foaf/0.1/>

        My name is **Alice** {=my:Alice .foaf:Person foaf:name}.

        Today I have learned that my colleague name is [Clair] {=my:Claire .foaf:Person foaf:name}

        ## I know Claire's name {=my:claire-name .rdf:Statement}
        [My colleague] {+my:Claire ?rdf:subject} [name] {+foaf:name ?rdf:predicate} is [Clair] {rdf:object}.

        {=}

        ## We've talked! {=my:claire-first-talk .rdf:Statement}
        Today [I] {+my:Alice ?rdf:subject} came to office a bit earlier and [talked for some time] {+foaf:knows ?rdf:predicate} with [Claire] {+my:Claire ?rdf:object}.

        Now **I** {=my:Alice} know **Claire** {+my:Claire ?foaf:knows}.
        """)
    result = parse({'text': md})
    assert len(result['statements']) == 2

    tag_iris = [s for s in result['statements'] if s.subject.value.startswith('tag:')]
    assert len(tag_iris) == 2
    predicates = [q.predicate.value for q in result['statements']]
    assert 'http://xmlns.com/foaf/0.1/name' in predicates
    assert 'http://xmlns.com/foaf/0.1/knows' in predicates
