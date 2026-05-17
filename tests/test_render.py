"""Render tests, transliterated from tests/render.tests.js."""
from __future__ import annotations
from textwrap import dedent

from mdld_parse import render


def _assert_valid_html(html: str) -> None:
    assert html.startswith('<div'), 'Should start with div wrapper'
    assert html.endswith('</div>'), 'Should end with div wrapper'
    assert ('<div prefix="' in html) or ('<div vocab="' in html)


def _assert_valid_rdfa(html: str) -> None:
    assert ('prefix="' in html) or ('vocab="' in html)
    assert '{' not in html
    assert '}' not in html


def test_context_declarations_with_valid_structure():
    md = dedent("""\
        [ex] <http://example.org/>
        [@vocab] <http://schema.org/>

        # Test {=ex:test .Thing}""")
    result = render(md)
    _assert_valid_html(result['html'])
    _assert_valid_rdfa(result['html'])
    assert 'prefix="rdf: http://www.w3.org/1999/02/22-rdf-syntax-ns#' in result['html']
    assert 'ex: http://example.org/' in result['html']
    assert 'vocab="http://schema.org/"' in result['html']
    assert '<h1 about="ex:test" typeof="Thing">' in result['html']
    assert '</h1>' in result['html']
    assert '>Test</h1>' in result['html']


def test_basic_subject_and_type_with_valid_html():
    md = dedent("""\
        [ex] <tag:me@example.org,2026:>
        # Document {=ex:doc .Document}""")
    result = render(md)
    _assert_valid_html(result['html'])
    _assert_valid_rdfa(result['html'])
    assert '<h1 about="ex:doc" typeof="Document">' in result['html']
    assert '>Document</h1>' in result['html']
    assert '{=ex:doc' not in result['html']
    assert '.Document' not in result['html']


def test_multiple_semantic_blocks_with_proper_nesting():
    md = dedent("""\
        [ex] <http://example.org/>

        # Document {=ex:doc .Article}

        # Section 1 {=ex:section1 .Section}

        # Section 2 {=ex:section2 .Section}""")
    result = render(md)
    _assert_valid_html(result['html'])
    _assert_valid_rdfa(result['html'])
    assert '<h1 about="ex:doc" typeof="Article">' in result['html']
    assert '<h1 about="ex:section1" typeof="Section">' in result['html']
    assert '<h1 about="ex:section2" typeof="Section">' in result['html']
    assert result['html'].count('<h1') == result['html'].count('</h1>')


def test_rdfa_context_completeness():
    md = dedent("""\
        [ex] <http://example.org/>
        # Test {=ex:test .Thing}""")
    result = render(md)
    for prefix in ('rdf:', 'rdfs:', 'xsd:'):
        assert prefix in result['html']
    assert 'prefix="' in result['html']
    assert 'http://www.w3.org/1999/02/22-rdf-syntax-ns#' in result['html']
    assert 'http://www.w3.org/2000/01/rdf-schema#' in result['html']
    assert 'http://www.w3.org/2001/XMLSchema#' in result['html']
    assert 'vocab="http://www.w3.org/2000/01/rdf-schema#"' in result['html']


def test_html_attribute_quoting_and_escaping():
    md = dedent("""\
        [ex] <http://example.org/>

        # "Special & Chars" {=ex:test .Thing}""")
    result = render(md)
    assert '&quot;' in result['html']
    assert '"Special & Chars"' not in result['html']
    assert 'about="ex:test"' in result['html']
    assert 'typeof="Thing"' in result['html']
    assert 'about=ex:test' not in result['html']
    assert 'typeof=Thing' not in result['html']


def test_complete_html_structure_validation():
    md = dedent("""\
        [schema] <http://schema.org/>

        # Article {=schema:article .Article}

        # Review {=schema:review .Review}""")
    result = render(md)
    _assert_valid_html(result['html'])
    _assert_valid_rdfa(result['html'])
    assert result['html'].count('<div') == result['html'].count('</div>')
    assert result['html'].count('<h1') == result['html'].count('</h1>')
    assert 'about="schema:article"' in result['html']
    assert 'typeof="Article"' in result['html']
    assert 'about="schema:review"' in result['html']
    assert 'typeof="Review"' in result['html']
    assert 'schema: http://schema.org/' in result['html']
