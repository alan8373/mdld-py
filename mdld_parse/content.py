"""Content-preserving MD-LD: structural vocabulary + RDF-star reification.

When `parse(text, preserve_content=True)` is called, the parser additionally
emits structural quads describing every block and its inline parts, plus
RDF-star quads linking each semantic triple to the block or part that
produced it. `regenerate(quads)` walks those structural quads to rebuild
the markdown document.

Status: behind a flag. Default behavior of `parse()` is unchanged.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Union

from .utils import DataFactory, Quad, hash_str
from .constants import STANDALONE_SUBJECT_REGEX


# ---------------------------------------------------------------------------
# Vocabulary
# ---------------------------------------------------------------------------

MDLD_NS  = "https://mdld.org/vocab#"
RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"


class V:
    """`mdld:` predicate and class IRIs. Namespaced for graph-view filtering."""

    Document       = MDLD_NS + "Document"
    Heading        = MDLD_NS + "Heading"
    Paragraph      = MDLD_NS + "Paragraph"
    ListItem       = MDLD_NS + "ListItem"
    Blockquote     = MDLD_NS + "Blockquote"
    CodeBlock      = MDLD_NS + "CodeBlock"
    BlankLine      = MDLD_NS + "BlankLine"
    HorizontalRule = MDLD_NS + "HorizontalRule"
    HtmlBlock      = MDLD_NS + "HtmlBlock"
    Table          = MDLD_NS + "Table"
    Frontmatter    = MDLD_NS + "Frontmatter"
    ReferenceLinkDefinition = MDLD_NS + "ReferenceLinkDefinition"
    PrefixDeclaration = MDLD_NS + "PrefixDeclaration"

    TextPart    = MDLD_NS + "TextPart"
    CarrierPart = MDLD_NS + "CarrierPart"

    hasBlock       = MDLD_NS + "hasBlock"
    order          = MDLD_NS + "order"
    level          = MDLD_NS + "level"
    language       = MDLD_NS + "language"
    parentBlock    = MDLD_NS + "parentBlock"

    hasPart        = MDLD_NS + "hasPart"
    partOrder      = MDLD_NS + "partOrder"
    text           = MDLD_NS + "text"
    carrierType    = MDLD_NS + "carrierType"
    carrierText    = MDLD_NS + "carrierText"
    carrierShape   = MDLD_NS + "carrierShape"
    carrierUrl     = MDLD_NS + "carrierUrl"

    annotationText = MDLD_NS + "annotationText"

    # Style discriminators for round-trip fidelity
    headingStyle      = MDLD_NS + "headingStyle"   # 'atx' | 'setext'
    setextMarker      = MDLD_NS + "setextMarker"   # '=' or '-'
    codeStyle         = MDLD_NS + "codeStyle"      # 'fenced' | 'indented'
    rawSource         = MDLD_NS + "rawSource"      # opaque source for HtmlBlock/HR
    listMarker        = MDLD_NS + "listMarker"     # '-', '*', '+', '1.', '23.'
    listIndent        = MDLD_NS + "listIndent"     # leading-space count
    listMarkerSpacing = MDLD_NS + "listMarkerSpacing"  # whitespace between marker and body

    annotates      = MDLD_NS + "annotates"


_TYPE_TO_CLASS = {
    'heading':    V.Heading,
    'para':       V.Paragraph,
    'list':       V.ListItem,
    'blockquote': V.Blockquote,
    'code':       V.CodeBlock,
    'blank':      V.BlankLine,
    'hr':         V.HorizontalRule,
    'html':       V.HtmlBlock,
    'table':      V.Table,
    'frontmatter':V.Frontmatter,
    'reflink':    V.ReferenceLinkDefinition,
    'prefix':     V.PrefixDeclaration,
}


def block_iri(block_id: str) -> str:
    return f"{MDLD_NS}block/{block_id}"


def part_iri(block_id: str, part_id: str) -> str:
    return f"{MDLD_NS}block/{block_id}/part/{part_id}"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class TextPart:
    iri:        str
    part_order: float
    text:       str

    def to_quads(self, parent_block_iri: str) -> list[Quad]:
        df = DataFactory
        s  = df.named_node(self.iri)
        return [
            df.quad(df.named_node(parent_block_iri),
                    df.named_node(V.hasPart), s),
            df.quad(s, df.named_node(RDF_TYPE), df.named_node(V.TextPart)),
            df.quad(s, df.named_node(V.partOrder), df.literal(self.part_order)),
            df.quad(s, df.named_node(V.text), df.literal(self.text)),
        ]


@dataclass
class CarrierPart:
    iri:             str
    part_order:      float
    carrier_type:    str
    carrier_text:    str
    carrier_shape:   str
    carrier_url:     Optional[str] = None
    annotation_text: Optional[str] = None

    def to_quads(self, parent_block_iri: str) -> list[Quad]:
        df = DataFactory
        s  = df.named_node(self.iri)
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


@dataclass
class BlockNode:
    iri:             str
    block_type:      str
    order:           float
    parts:           list[Part]    = field(default_factory=list)
    level:           Optional[int] = None
    language:        Optional[str] = None
    parent_iri:      Optional[str] = None
    annotation_text: Optional[str] = None
    heading_style:   Optional[str] = None   # 'atx' | 'setext'
    setext_marker:   Optional[str] = None   # '=' or '-'
    code_style:      Optional[str] = None   # 'fenced' | 'indented'
    raw_source:      Optional[str] = None   # for HtmlBlock / HorizontalRule
    list_marker:     Optional[str] = None   # '-', '*', '+', '1.', '23.'
    list_indent:     Optional[int] = None   # leading-space count
    list_marker_spacing: Optional[str] = None  # whitespace between marker and body

    def to_quads(self, doc_iri: Optional[str] = None) -> list[Quad]:
        df = DataFactory
        s  = df.named_node(self.iri)
        out: list[Quad] = [
            df.quad(s, df.named_node(RDF_TYPE),
                    df.named_node(_TYPE_TO_CLASS[self.block_type])),
            df.quad(s, df.named_node(V.order), df.literal(self.order)),
        ]
        if self.level is not None:
            out.append(df.quad(s, df.named_node(V.level),
                               df.literal(self.level)))
        if self.language:
            out.append(df.quad(s, df.named_node(V.language),
                               df.literal(self.language)))
        if self.parent_iri:
            out.append(df.quad(s, df.named_node(V.parentBlock),
                               df.named_node(self.parent_iri)))
        if self.annotation_text:
            out.append(df.quad(s, df.named_node(V.annotationText),
                               df.literal(self.annotation_text)))
        if self.heading_style:
            out.append(df.quad(s, df.named_node(V.headingStyle),
                               df.literal(self.heading_style)))
        if self.setext_marker:
            out.append(df.quad(s, df.named_node(V.setextMarker),
                               df.literal(self.setext_marker)))
        if self.code_style:
            out.append(df.quad(s, df.named_node(V.codeStyle),
                               df.literal(self.code_style)))
        if self.raw_source is not None:
            out.append(df.quad(s, df.named_node(V.rawSource),
                               df.literal(self.raw_source)))
        if self.list_marker is not None:
            out.append(df.quad(s, df.named_node(V.listMarker),
                               df.literal(self.list_marker)))
        if self.list_indent is not None:
            out.append(df.quad(s, df.named_node(V.listIndent),
                               df.literal(self.list_indent)))
        if self.list_marker_spacing is not None:
            out.append(df.quad(s, df.named_node(V.listMarkerSpacing),
                               df.literal(self.list_marker_spacing)))
        if doc_iri:
            out.append(df.quad(df.named_node(doc_iri),
                               df.named_node(V.hasBlock), s))
        for p in self.parts:
            out.extend(p.to_quads(self.iri))
        return out


# ---------------------------------------------------------------------------
# RDF-star reification
# ---------------------------------------------------------------------------

def annotate_triple(semantic_quad: Quad, target_iri: str) -> Quad:
    """Link a semantic triple to the block or part that produced it.

    The semantic_quad itself is the *subject* of the metadata triple —
    this is RDF-star (quoted triple as term). `Quad` already extends
    `Term` so no new term class is needed.
    """
    df = DataFactory
    return df.quad(semantic_quad,
                   df.named_node(V.annotates),
                   df.named_node(target_iri))


# ---------------------------------------------------------------------------
# Parser-side helper: build BlockNode + parts from a parser token
# ---------------------------------------------------------------------------

def part_id_for_carrier(block_id: str, carrier_range: list) -> str:
    return hash_str(f"{block_id}:c:{carrier_range[0]}:{carrier_range[1]}")


def part_id_for_text_gap(block_id: str, start: int, end: int) -> str:
    return hash_str(f"{block_id}:t:{start}:{end}")


def build_block_node(token: dict, block_id: str, order: int,
                     carriers: list, source_text: Optional[str] = None) -> BlockNode:
    """Decompose a parser token into a BlockNode with ordered parts.

    `carriers` is the list returned by mdld_parse.parse._get_carriers.
    Carrier ranges are absolute (token['range'][0] + relative); subtract
    `token['range'][0]` to get offsets within `token['text']`.

    `source_text`, when provided, is the original document text. It is
    used to recover the exact whitespace between a block body and its
    `{...}` annotation so round-trips are byte-faithful.
    """
    body  = token.get('text', '') or ''
    base  = token['range'][0] if token.get('range') else 0

    is_list = token['type'] == 'list'
    block = BlockNode(
        iri=block_iri(block_id),
        block_type=token['type'],
        order=float(order),
        level=token.get('depth'),
        language=token.get('lang'),
        heading_style=token.get('_heading_style'),
        setext_marker=token.get('_setext_marker'),
        code_style=token.get('_code_style'),
        list_marker=token.get('_listMarker') if is_list else None,
        list_indent=token.get('indent') if is_list else None,
        list_marker_spacing=token.get('_listMarkerSpacing') if is_list else None,
    )

    # Raw passthrough blocks: opaque source; no parts, no annotations.
    if token['type'] in ('hr', 'html', 'table', 'frontmatter', 'reflink', 'prefix'):
        block.raw_source = token.get('text', '')
        return block

    # Block-level annotation: heading attrs, list/blockquote attrs,
    # or a paragraph that's nothing but `{=...}`.
    if token.get('attrs'):
        # Preserve any whitespace between the body's value range and the
        # attrs's start so "# H  {=foo}" round-trips with two spaces.
        lead_ws = ''
        if source_text is not None:
            vr = token.get('valueRange')
            ar = token.get('attrsRange')
            if vr and ar and 0 <= vr[1] <= ar[0] <= len(source_text):
                lead_ws = source_text[vr[1]:ar[0]]
        block.annotation_text = lead_ws + token['attrs']
    elif (token['type'] == 'para'
          and STANDALONE_SUBJECT_REGEX.match(body)):
        block.annotation_text = body.strip()
        return block  # whole paragraph IS the annotation; no body parts

    # Walk carriers in order, emitting TextParts for the gaps.
    parts: list[Part] = []
    cursor = 0
    part_idx = 0

    for c in carriers:
        if not c.get('range'):
            continue
        rel_start = c['range'][0] - base
        rel_end   = c['range'][1] - base

        # Gap before this carrier
        if rel_start > cursor:
            gap = body[cursor:rel_start]
            if gap:
                pid = part_id_for_text_gap(block_id, cursor, rel_start)
                parts.append(TextPart(
                    iri=part_iri(block_id, pid),
                    part_order=float(part_idx),
                    text=gap,
                ))
                part_idx += 1

        # Carrier itself: shape ends where attrs start (if any)
        attrs_range = c.get('attrsRange')
        if attrs_range and c.get('attrs'):
            shape_end_rel = attrs_range[0] - base
            raw_shape   = body[rel_start:shape_end_rel]
            shape       = raw_shape.rstrip()
            # Push any inter-shape whitespace into ann so the round-trip
            # preserves "[Alice] {+...}" vs "[Alice]{+...}" exactly.
            trailing_ws = raw_shape[len(shape):]
            ann         = trailing_ws + body[shape_end_rel:rel_end]
        else:
            shape = body[rel_start:rel_end]
            ann   = None

        pid = part_id_for_carrier(block_id, c['range'])
        parts.append(CarrierPart(
            iri=part_iri(block_id, pid),
            part_order=float(part_idx),
            carrier_type=c.get('type', ''),
            carrier_text=c.get('text', ''),
            carrier_shape=shape,
            carrier_url=c.get('url') or None,
            annotation_text=ann,
        ))
        part_idx += 1
        cursor = rel_end

    # Trailing text gap
    if cursor < len(body):
        gap = body[cursor:]
        if gap:
            pid = part_id_for_text_gap(block_id, cursor, len(body))
            parts.append(TextPart(
                iri=part_iri(block_id, pid),
                part_order=float(part_idx),
                text=gap,
            ))

    block.parts = parts
    return block


# ---------------------------------------------------------------------------
# Generator: walk blocks in order, walk each block's parts in order
# ---------------------------------------------------------------------------

def regenerate(quads: list) -> str:
    """Reconstruct markdown from a quad set that includes mdld:* structure."""
    blocks: dict[str, dict]              = {}
    parts:  dict[str, dict]              = {}
    block_to_parts: dict[str, list[str]] = {}
    block_prefix = MDLD_NS + "block/"

    for q in quads:
        s = q.subject
        if s.term_type != 'NamedNode' or not s.value.startswith(block_prefix):
            continue
        p = q.predicate.value
        o = q.object

        if "/part/" in s.value:
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
        else:
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
            elif p == V.headingStyle:
                b['headingStyle'] = o.value
            elif p == V.setextMarker:
                b['setextMarker'] = o.value
            elif p == V.codeStyle:
                b['codeStyle'] = o.value
            elif p == V.rawSource:
                b['rawSource'] = o.value
            elif p == V.listMarker:
                b['listMarker'] = o.value
            elif p == V.listIndent:
                b['listIndent'] = int(o.value)
            elif p == V.listMarkerSpacing:
                b['listMarkerSpacing'] = o.value
            elif p == V.hasPart:
                block_to_parts.setdefault(s.value, []).append(o.value)

    blocks_ordered = sorted(blocks.items(),
                            key=lambda kv: kv[1].get('order', 0))

    lines: list[str] = []
    for bi, b in blocks_ordered:
        body = _render_parts(block_to_parts.get(bi, []), parts)
        block_ann = b.get('annotation')
        if block_ann:
            # block_ann includes any captured leading whitespace; just
            # concatenate so source spacing is preserved exactly.
            body = (body + block_ann) if body else block_ann.lstrip()

        kind = b.get('type', '')
        if kind == V.Heading:
            if b.get('headingStyle') == 'setext':
                marker = (b.get('setextMarker') or '=') * max(len(body), 1)
                lines.append(body)
                lines.append(marker)
            else:
                lines.append(('#' * (b.get('level') or 1)) + ' ' + body)
        elif kind == V.CodeBlock:
            if b.get('codeStyle') == 'indented':
                for cl in body.split('\n'):
                    lines.append('    ' + cl if cl else '')
            else:
                lang = b.get('language') or ''
                lines.append(f'```{lang}')
                lines.append(body)
                lines.append('```')
        elif kind == V.Blockquote:
            lines.append('> ' + body)
        elif kind == V.ListItem:
            indent  = b.get('listIndent') or 0
            marker  = b.get('listMarker') or '-'
            spacing = b.get('listMarkerSpacing') or ' '
            lines.append(' ' * indent + marker + spacing + body)
        elif kind == V.BlankLine:
            lines.append('')
        elif kind == V.HorizontalRule:
            lines.append(b.get('rawSource', '---'))
        elif kind == V.HtmlBlock:
            raw = b.get('rawSource', body)
            if raw.endswith('\n'):
                raw = raw[:-1]
            lines.append(raw)
        elif kind == V.Table:
            raw = b.get('rawSource', body)
            if raw.endswith('\n'):
                raw = raw[:-1]
            lines.append(raw)
        elif kind == V.Frontmatter:
            raw = b.get('rawSource', body)
            if raw.endswith('\n'):
                raw = raw[:-1]
            lines.append(raw)
        elif kind == V.ReferenceLinkDefinition:
            raw = b.get('rawSource', body)
            if raw.endswith('\n'):
                raw = raw[:-1]
            lines.append(raw)
        elif kind == V.PrefixDeclaration:
            raw = b.get('rawSource', body)
            if raw.endswith('\n'):
                raw = raw[:-1]
            lines.append(raw)
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
            out.append(shape + (ann if ann else ''))
    return ''.join(out)
