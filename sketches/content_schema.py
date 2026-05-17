"""
Sketch: content-preserving MD-LD via an `mdld:` structural vocabulary,
RDF-star reification (RDF 1.2 quoted triples), and an ordered-parts
decomposition of each block.

A block (heading, paragraph, etc.) decomposes into a sequence of parts.
Each part is one of:

  * mdld:TextPart    — opaque markdown prose
  * mdld:CarrierPart — an inline value carrier (link, emphasis, code,
                       angle-URL) optionally bearing an annotation

The parts model replaces an earlier `mdld:rawMarkdown` + character-offset
approach. Reorders, inserts, and edits become local operations on parts;
the regenerator concatenates parts in `mdld:partOrder`. No offset arithmetic.

`mdld:partOrder` is decimal so the UI can insert between parts without
renumbering (the Notion/Jira trick: insert with order = midpoint of
neighbors).

Reification: a semantic triple T gets metadata by using T itself as the
subject of another quad. `Quad` already extends `Term`
(mdld_parse/utils.py:129), so quoted-triple subjects work natively.

    << <ex:trip-1> ex:companion <ex:alice> >>
        mdld:annotates <mdld:block/p1/part/a> .

Block-level annotations (a heading's `{=...}`, etc.) attach to the block
itself rather than to a part, so `mdld:annotates` can target either.

Status: design sketch. Not wired into mdld_parse yet — the demo at the
bottom hand-builds one heading + one paragraph end-to-end.

Run:
    PYTHONPATH=. .venv/bin/python sketches/content_schema.py
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Union

from mdld_parse.utils import DataFactory, Quad
from mdld_parse import parse


# ---------------------------------------------------------------------------
# Content vocabulary
# ---------------------------------------------------------------------------

MDLD_NS  = "https://mdld.org/vocab#"
RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"


class V:
    """`mdld:` predicate and class IRIs. Namespaced so graph views can filter."""

    # Block classes
    Document   = MDLD_NS + "Document"
    Heading    = MDLD_NS + "Heading"
    Paragraph  = MDLD_NS + "Paragraph"
    ListItem   = MDLD_NS + "ListItem"
    Blockquote = MDLD_NS + "Blockquote"
    CodeBlock  = MDLD_NS + "CodeBlock"
    Blank      = MDLD_NS + "BlankLine"

    # Part classes
    TextPart    = MDLD_NS + "TextPart"
    CarrierPart = MDLD_NS + "CarrierPart"

    # Block predicates
    hasBlock       = MDLD_NS + "hasBlock"
    order          = MDLD_NS + "order"
    level          = MDLD_NS + "level"           # heading depth
    language       = MDLD_NS + "language"        # code fence language
    parentBlock    = MDLD_NS + "parentBlock"     # nesting
    primarySubject = MDLD_NS + "primarySubject"

    # Part predicates
    hasPart        = MDLD_NS + "hasPart"
    partOrder      = MDLD_NS + "partOrder"       # decimal, supports midpoint insert
    text           = MDLD_NS + "text"            # TextPart payload
    carrierType    = MDLD_NS + "carrierType"     # 'link' | 'emphasis' | 'code' | 'angle'
    carrierText    = MDLD_NS + "carrierText"     # text inside [..], `..`, *..*
    carrierShape   = MDLD_NS + "carrierShape"    # surface form: "[Alice]" or "*Alice*"
    carrierUrl     = MDLD_NS + "carrierUrl"      # link/image destination

    # Annotation surface form — lives on whichever node bears the {...}:
    # block-level on a BlockNode, inline on a CarrierPart
    annotationText = MDLD_NS + "annotationText"

    # Reification — subject is a quoted triple (RDF-star)
    annotates      = MDLD_NS + "annotates"       # quoted triple → block | part


_TYPE_TO_CLASS = {
    'heading':    V.Heading,
    'para':       V.Paragraph,
    'list':       V.ListItem,
    'blockquote': V.Blockquote,
    'code':       V.CodeBlock,
    'blank':      V.Blank,
}


def block_iri(block_id: str) -> str:
    return f"{MDLD_NS}block/{block_id}"


def part_iri(block_id: str, part_id: str) -> str:
    return f"{MDLD_NS}block/{block_id}/part/{part_id}"


# ---------------------------------------------------------------------------
# Parts
# ---------------------------------------------------------------------------

@dataclass
class TextPart:
    """Opaque markdown prose between carriers (or a whole un-annotated block)."""
    iri:        str
    part_order: float
    text:       str

    def to_quads(self, parent_block_iri: str) -> list[Quad]:
        df = DataFactory
        s = df.named_node(self.iri)
        return [
            df.quad(df.named_node(parent_block_iri),
                    df.named_node(V.hasPart), s),
            df.quad(s, df.named_node(RDF_TYPE), df.named_node(V.TextPart)),
            df.quad(s, df.named_node(V.partOrder), df.literal(self.part_order)),
            df.quad(s, df.named_node(V.text), df.literal(self.text)),
        ]


@dataclass
class CarrierPart:
    """An inline carrier: link, emphasis, code span, etc., optionally annotated."""
    iri:             str
    part_order:      float
    carrier_type:    str
    carrier_text:    str
    carrier_shape:   str                       # markdown surface form, e.g. "[Alice]"
    carrier_url:     Optional[str] = None
    annotation_text: Optional[str] = None      # the literal "{...}" if present

    def to_quads(self, parent_block_iri: str) -> list[Quad]:
        df = DataFactory
        s = df.named_node(self.iri)
        out = [
            df.quad(df.named_node(parent_block_iri),
                    df.named_node(V.hasPart), s),
            df.quad(s, df.named_node(RDF_TYPE), df.named_node(V.CarrierPart)),
            df.quad(s, df.named_node(V.partOrder), df.literal(self.part_order)),
            df.quad(s, df.named_node(V.carrierType), df.literal(self.carrier_type)),
            df.quad(s, df.named_node(V.carrierText), df.literal(self.carrier_text)),
            df.quad(s, df.named_node(V.carrierShape), df.literal(self.carrier_shape)),
        ]
        if self.carrier_url:
            out.append(df.quad(s, df.named_node(V.carrierUrl),
                               df.named_node(self.carrier_url)))
        if self.annotation_text:
            out.append(df.quad(s, df.named_node(V.annotationText),
                               df.literal(self.annotation_text)))
        return out


Part = Union[TextPart, CarrierPart]


# ---------------------------------------------------------------------------
# BlockNode
# ---------------------------------------------------------------------------

@dataclass
class BlockNode:
    """One structural unit of a source document, addressable by IRI.

    Holds an ordered list of `parts`. The block itself stores no inline
    prose; all body content lives in TextPart / CarrierPart nodes. A block
    may carry its own `annotation_text` for block-level `{...}` (e.g. on
    headings).
    """
    iri:             str
    block_type:      str
    order:           float
    parts:           list[Part]    = field(default_factory=list)
    level:           Optional[int] = None
    language:        Optional[str] = None
    parent_iri:      Optional[str] = None
    annotation_text: Optional[str] = None

    def to_quads(self, doc_iri: Optional[str] = None) -> list[Quad]:
        df = DataFactory
        s  = df.named_node(self.iri)
        out: list[Quad] = [
            df.quad(s, df.named_node(RDF_TYPE),
                    df.named_node(_TYPE_TO_CLASS[self.block_type])),
            df.quad(s, df.named_node(V.order), df.literal(self.order)),
        ]
        if self.level is not None:
            out.append(df.quad(s, df.named_node(V.level), df.literal(self.level)))
        if self.language:
            out.append(df.quad(s, df.named_node(V.language),
                               df.literal(self.language)))
        if self.parent_iri:
            out.append(df.quad(s, df.named_node(V.parentBlock),
                               df.named_node(self.parent_iri)))
        if self.annotation_text:
            out.append(df.quad(s, df.named_node(V.annotationText),
                               df.literal(self.annotation_text)))
        if doc_iri:
            out.append(df.quad(df.named_node(doc_iri),
                               df.named_node(V.hasBlock), s))
        for p in self.parts:
            out.extend(p.to_quads(self.iri))
        return out


# ---------------------------------------------------------------------------
# RDF-star reification — link a semantic triple to the block or part it came from
# ---------------------------------------------------------------------------

def annotate_triple(semantic_quad: Quad, target_iri: str) -> Quad:
    """Link a semantic triple to the block or part that produced it.

    `target_iri` is either a block IRI (block-level annotation) or a
    part IRI (inline carrier annotation). The quoted triple sits as the
    subject — `Quad` already extends `Term` so this is RDF-star natively.
    """
    df = DataFactory
    return df.quad(semantic_quad,
                   df.named_node(V.annotates),
                   df.named_node(target_iri))


# ---------------------------------------------------------------------------
# Where this would hook into the existing parser
# ---------------------------------------------------------------------------
#
# In mdld_parse/parse.py, gated behind state.get('preserve_content'):
#
# 1. `_extract_inline_carriers` already produces a list of carriers with
#    text + range + url + attrs. The plaintext gaps between carriers
#    become TextParts; carriers become CarrierParts. No coordinate
#    translation — the parts list IS the order.
#
# 2. `_create_block_entry` builds a BlockNode (with parts) and appends
#    `node.to_quads()` to state['quads']. Part IDs hash on
#    (block_id, carrier.range) so they're stable across reparses.
#
# 3. `_emit_quad`, after appending a semantic quad, also appends
#    `annotate_triple(quad, target_iri)` — target = part IRI for inline
#    annotations, block IRI for block-level annotations.


# ---------------------------------------------------------------------------
# Generator: walk blocks in order, walk each block's parts in order
# ---------------------------------------------------------------------------

def regenerate(quads: list) -> str:
    blocks: dict[str, dict]                = {}
    parts:  dict[str, dict]                = {}
    block_to_parts: dict[str, list[str]]   = {}

    block_prefix = MDLD_NS + "block/"

    for q in quads:
        s = q.subject
        p = q.predicate.value
        o = q.object

        # Block-level structural triples (block IRI without "/part/")
        if (s.term_type == 'NamedNode'
                and s.value.startswith(block_prefix)
                and "/part/" not in s.value):
            b = blocks.setdefault(s.value, {})
            if p == RDF_TYPE and o.value.startswith(MDLD_NS):
                b['type'] = o.value
            elif p == V.order:
                b['order'] = float(o.value)
            elif p == V.level:
                b['level'] = int(o.value)
            elif p == V.language:
                b['language'] = o.value
            elif p == V.annotationText:
                b['annotation'] = o.value
            elif p == V.hasPart:
                block_to_parts.setdefault(s.value, []).append(o.value)
            continue

        # Part-level structural triples
        if (s.term_type == 'NamedNode'
                and s.value.startswith(block_prefix)
                and "/part/" in s.value):
            pt = parts.setdefault(s.value, {})
            if p == RDF_TYPE and o.value.startswith(MDLD_NS):
                pt['type'] = o.value
            elif p == V.partOrder:
                pt['order'] = float(o.value)
            elif p == V.text:
                pt['text'] = o.value
            elif p == V.carrierShape:
                pt['carrierShape'] = o.value
            elif p == V.annotationText:
                pt['annotation'] = o.value
            continue

    blocks_ordered = sorted(blocks.items(),
                            key=lambda kv: kv[1].get('order', 0))

    lines: list[str] = []
    for bi, b in blocks_ordered:
        body = _render_parts(block_to_parts.get(bi, []), parts)
        block_ann = b.get('annotation')
        if block_ann:
            body = f'{body} {block_ann}'

        kind = b.get('type', '')
        if kind == V.Heading:
            lines.append(('#' * (b.get('level') or 1)) + ' ' + body)
        elif kind == V.CodeBlock:
            lang = b.get('language') or ''
            lines.append(f'```{lang}')
            lines.append(body)
            lines.append('```')
        elif kind == V.Blockquote:
            lines.append('> ' + body)
        elif kind == V.ListItem:
            lines.append('- ' + body)
        elif kind == V.Blank:
            lines.append('')
        else:
            lines.append(body)

    return '\n'.join(lines) + '\n'


def _render_parts(part_iris: list[str], parts: dict[str, dict]) -> str:
    items = [parts.get(piri, {}) for piri in part_iris]
    items.sort(key=lambda pt: pt.get('order', 0))
    out: list[str] = []
    for pt in items:
        if pt.get('type') == V.TextPart:
            out.append(pt.get('text', ''))
        elif pt.get('type') == V.CarrierPart:
            shape = pt.get('carrierShape', '')
            ann   = pt.get('annotation')
            out.append(shape + (' ' + ann if ann else ''))
    return ''.join(out)


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    df  = DataFactory
    ctx = {'ex': 'http://example.org/'}

    # Heading: "# Trip notes {=ex:trip-1 .ex:Trip}"
    # — body text in one TextPart, block-level annotation on the BlockNode.
    heading = BlockNode(
        iri=block_iri("h1"),
        block_type='heading',
        order=0,
        level=1,
        annotation_text='{=ex:trip-1 .ex:Trip}',
        parts=[
            TextPart(
                iri=part_iri("h1", "a"),
                part_order=0,
                text="Trip notes",
            ),
        ],
    )

    # Paragraph: "[Alice] {+ex:alice ?ex:companion} brought a kite."
    # — one annotated CarrierPart followed by a TextPart.
    para = BlockNode(
        iri=block_iri("p1"),
        block_type='para',
        order=1,
        parts=[
            CarrierPart(
                iri=part_iri("p1", "a"),
                part_order=0,
                carrier_type='link',
                carrier_text='Alice',
                carrier_shape='[Alice]',
                annotation_text='{+ex:alice ?ex:companion}',
            ),
            TextPart(
                iri=part_iri("p1", "b"),
                part_order=1,
                text=' brought a kite.',
            ),
        ],
    )

    quads: list[Quad] = []
    quads += heading.to_quads(doc_iri="http://example.org/doc")
    quads += para.to_quads(doc_iri="http://example.org/doc")

    # Heading's annotation produces: <ex:trip-1> rdf:type <ex:Trip>
    type_quad = df.quad(
        df.named_node("http://example.org/trip-1"),
        df.named_node(RDF_TYPE),
        df.named_node("http://example.org/Trip"),
    )
    quads.append(type_quad)
    quads.append(annotate_triple(type_quad, heading.iri))   # block-level link

    # Paragraph carrier annotation produces: <ex:trip-1> ex:companion <ex:alice>
    companion = df.quad(
        df.named_node("http://example.org/trip-1"),
        df.named_node("http://example.org/companion"),
        df.named_node("http://example.org/alice"),
    )
    quads.append(companion)
    quads.append(annotate_triple(companion, part_iri("p1", "a")))   # part-level link

    n_total  = len(quads)
    n_star   = sum(1 for q in quads if q.subject.term_type == 'Quad')
    n_struct = sum(1 for q in quads
                   if q.subject.term_type == 'NamedNode'
                   and q.subject.value.startswith(MDLD_NS))
    n_doc    = sum(1 for q in quads
                   if q.subject.term_type == 'NamedNode'
                   and q.subject.value == "http://example.org/doc")
    n_data   = n_total - n_star - n_struct - n_doc

    print(f'quad set: {n_total} total')
    print(f'  block + part structural: {n_struct}')
    print(f'  doc → block (hasBlock):  {n_doc}')
    print(f'  semantic data:           {n_data}')
    print(f'  rdf-star (annotates):    {n_star}')
    print()
    print('--- regenerated markdown ---')
    regen = regenerate(quads)
    print(regen)

    print('--- re-parsed semantic quads ---')
    re_parsed = parse({'text': regen, 'context': ctx})
    for q in re_parsed['quads']:
        print(f'  {q.subject.value} {q.predicate.value} {q.object.value}')


if __name__ == '__main__':
    _demo()
