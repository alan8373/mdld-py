"""Tests for the preserve_content parser flag and regenerate()."""
from __future__ import annotations

from mdld_parse import parse, regenerate
from mdld_parse.content import V, MDLD_NS

from .conftest import quad_key


CTX = {'ex': 'http://example.org/'}


def _semantic_keys(quads):
    """Quad keys for non-mdld-structural, non-rdf-star quads."""
    keys = []
    for q in quads:
        if q.subject.term_type == 'Quad':
            continue
        if q.subject.value.startswith(MDLD_NS):
            continue
        keys.append(quad_key(q))
    return sorted(keys)


def test_preserve_content_off_by_default():
    """Existing API: parse() returns only semantic quads."""
    source = "# Trip notes {=ex:trip-1 .ex:Trip}\n"
    parsed = parse({'text': source, 'context': CTX})
    for q in parsed['quads']:
        assert not q.subject.value.startswith(MDLD_NS), \
            f"unexpected structural quad emitted without flag: {q}"


def test_round_trip_heading_and_carrier():
    """A heading + paragraph with one inline carrier round-trips byte-faithfully
    on the second pass and produces the same semantic quads."""
    source = (
        "# Trip notes {=ex:trip-1 .ex:Trip}\n"
        "[Alice] {+ex:alice ?ex:companion} brought a kite.\n"
    )
    parsed = parse({'text': source, 'context': CTX, 'preserve_content': True})

    regen = regenerate(parsed['quads'])
    assert "# Trip notes {=ex:trip-1 .ex:Trip}" in regen
    assert "[Alice] {+ex:alice ?ex:companion} brought a kite." in regen

    # Re-parse and confirm semantic triples are identical
    re_parsed = parse({'text': regen, 'context': CTX})
    assert _semantic_keys(parsed['quads']) == _semantic_keys(re_parsed['quads'])


def test_structural_quads_present():
    source = "[Alice] {+ex:alice ?ex:companion} brought a kite.\n"
    parsed = parse({'text': source, 'context': CTX, 'preserve_content': True})
    quads = parsed['quads']

    # At least one Paragraph block, one CarrierPart, one TextPart
    have_paragraph    = any(q.predicate.value == V.order
                            and q.subject.value.startswith(MDLD_NS + "block/")
                            for q in quads)
    have_carrier_part = any(q.object.value == V.CarrierPart for q in quads)
    have_text_part    = any(q.object.value == V.TextPart for q in quads)
    assert have_paragraph
    assert have_carrier_part
    assert have_text_part


def test_block_annotation_spacing_round_trips():
    """Whitespace between a block's body and its `{...}` is preserved exactly."""
    for src in ('# H  {=ex:foo}\n',     # two spaces
                '# H {=ex:foo}\n',      # one space
                '# H{=ex:foo}\n',       # no space
                '# H   {=ex:foo}\n'):   # three spaces
        parsed = parse({'text': src, 'context': CTX, 'preserve_content': True})
        assert regenerate(parsed['quads']) == src, f'failed for {src!r}'


def test_blank_lines_round_trip():
    """Blank lines between blocks survive the round-trip byte-exactly."""
    source = (
        "# Trip notes {=ex:trip-1 .ex:Trip}\n"
        "\n"
        "[Alice] {+ex:alice ?ex:companion} brought a kite.\n"
        "\n"
        "We had a great time.\n"
    )
    parsed = parse({'text': source, 'context': CTX, 'preserve_content': True})
    assert regenerate(parsed['quads']) == source


def test_horizontal_rule_round_trips():
    src = "# Title\n\n---\n\nAfter the rule.\n"
    parsed = parse({'text': src, 'context': CTX, 'preserve_content': True})
    assert regenerate(parsed['quads']) == src


def test_html_block_round_trips():
    src = '# Title\n\n<div class="box">\n  hello\n</div>\n\nAfter html.\n'
    parsed = parse({'text': src, 'context': CTX, 'preserve_content': True})
    assert regenerate(parsed['quads']) == src


def test_indented_code_round_trips():
    src = "# Title\n\n    indented\n    code\n\nAfter code.\n"
    parsed = parse({'text': src, 'context': CTX, 'preserve_content': True})
    assert regenerate(parsed['quads']) == src


def test_comprehensive_document_round_trips():
    """A document exercising every supported block type round-trips
    byte-for-byte."""
    src = (
        "---\n"
        "title: Comprehensive demo\n"
        "date: 2026-05-03\n"
        "---\n"
        "\n"
        "[ex] <http://example.org/>\n"
        "[homepage]: https://example.com\n"
        "\n"
        "# Trip Notes {=ex:trip-1 .ex:Trip}\n"
        "\n"
        "A paragraph with [Alice] {+ex:alice ?ex:companion} and details.\n"
        "\n"
        "## Itinerary {=#schedule}\n"
        "\n"
        "| Day | Activity |\n"
        "| --- | -------- |\n"
        "| Mon | Hike     |\n"
        "\n"
        "- item 1 {ex:p}\n"
        "\n"
        "- item 2 {ex:p}\n"
        "\n"
        "> Quoted text {ex:q}\n"
        ">\n"
        "> Second paragraph in quote {ex:q}\n"
        "\n"
        "Setext-style heading\n"
        "====================\n"
        "\n"
        "---\n"
        "\n"
        '<div class="note">\n'
        "  HTML block content\n"
        "</div>\n"
        "\n"
        "    indented code line 1\n"
        "    indented code line 2\n"
        "\n"
        "```python\n"
        "fenced code\n"
        "```\n"
        "\n"
        "See [homepage] for more.\n"
    )
    parsed = parse({'text': src, 'preserve_content': True})
    assert regenerate(parsed['quads']) == src


def test_list_marker_indent_spacing_round_trip():
    """Bullet flavor (`-`/`*`/`+`), ordered numbering, nested indent, and
    marker-body spacing are all preserved on round-trip."""
    cases = [
        # marker variants
        "- a\n- b\n- c\n",
        "* a\n* b\n",
        "+ a\n+ b\n",
        # tight vs loose
        "- a\n\n- b\n\n- c\n",
        # ordered lists with arbitrary start values
        "1. one\n2. two\n3. three\n",
        "5. fifth\n6. sixth\n",
        # mixed markers in one document
        "- bullet\n* asterisk\n+ plus\n",
        # nested via indent
        "- outer\n  - inner\n  - inner2\n- outer2\n",
        # extra space between marker and body
        "-  two-space\n-   three-space\n",
    ]
    for src in cases:
        parsed = parse({'text': src, 'context': CTX, 'preserve_content': True})
        assert regenerate(parsed['quads']) == src, f'failed for {src!r}'


def test_nested_blank_lines_round_trip():
    """Blanks within lists and blockquotes survive the round-trip."""
    cases = [
        # blank between list items
        "- item 1\n- item 2\n\n- item 3\n",
        # blank-in-quote (line is just `>`)
        "> Line 1\n>\n> Line 2\n",
        # list with annotations and a blank
        "- item 1 {ex:p}\n\n- item 2 {ex:p}\n",
    ]
    for src in cases:
        parsed = parse({'text': src, 'context': CTX, 'preserve_content': True})
        assert regenerate(parsed['quads']) == src, f'failed for {src!r}'


def test_reference_link_definitions_round_trip():
    src = (
        "[homepage]: https://example.com\n"
        "[docs]: https://docs.example.com 'Documentation'\n"
        "\n"
        "See [homepage] and [docs] for more.\n"
    )
    parsed = parse({'text': src, 'context': CTX, 'preserve_content': True})
    assert regenerate(parsed['quads']) == src


def test_frontmatter_round_trips():
    src = (
        "---\n"
        "title: Hello\n"
        "date: 2026-05-03\n"
        "tags: [demo, mdld]\n"
        "---\n"
        "\n"
        "# Body\n"
        "\n"
        "Content.\n"
    )
    parsed = parse({'text': src, 'context': CTX, 'preserve_content': True})
    assert regenerate(parsed['quads']) == src


def test_table_round_trips():
    src = (
        "# Roster {=ex:doc}\n"
        "\n"
        "| Name | Role |\n"
        "| ---- | ---- |\n"
        "| Alice | Author |\n"
        "| Bob | Editor |\n"
        "\n"
        "End.\n"
    )
    parsed = parse({'text': src, 'context': CTX, 'preserve_content': True})
    assert regenerate(parsed['quads']) == src


def test_setext_headings_round_trip():
    for src in ("Setext H1\n=========\n\nbody.\n",
                "Setext H2\n---------\n\nbody.\n"):
        parsed = parse({'text': src, 'context': CTX, 'preserve_content': True})
        assert regenerate(parsed['quads']) == src, f'failed for {src!r}'


def test_rdf_star_annotates_link():
    """Every semantic data quad should be linked via mdld:annotates to a
    block or part."""
    source = "# Trip notes {=ex:trip-1 .ex:Trip}\n"
    parsed = parse({'text': source, 'context': CTX, 'preserve_content': True})

    star_links = [q for q in parsed['quads']
                  if q.subject.term_type == 'Quad'
                  and q.predicate.value == V.annotates]

    assert len(star_links) >= 1
    target = star_links[0].object.value
    assert target.startswith(MDLD_NS + "block/")

    # The linked triple should be the rdf:type assertion from the heading
    quoted = star_links[0].subject
    assert quoted.subject.value == "http://example.org/trip-1"
    assert quoted.predicate.value == \
        "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
    assert quoted.object.value == "http://example.org/Trip"
