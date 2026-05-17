# Python API Reference

Everything below comes from `mdld_parse`. The package mirrors the upstream
JavaScript API but uses Python idioms — `snake_case` keys, plain `dict`
returns, and dataclass-shaped term/quad objects.

```python
from mdld_parse import (
    parse, generate, generate_node, merge, locate, render,
    DEFAULT_CONTEXT, DataFactory,
    NamedNode, Literal, BlankNode, Variable, DefaultGraph, Quad, Term,
    expand_iri, shorten_iri, parse_semantic_block,
    hash_str, quad_index_key, quad_to_key_for_origin, create_literal,
    extract_local_name,
)
```

The dict-spread composition pattern works because `parse()` returns a dict
whose keys (`quads`, `context`, `primary_subject`) are exactly what
`generate()` and `generate_node()` accept.

---

## `parse(text_or_dict, options=None, **kwargs)`

Parse MD-LD source and return quads with origin tracking.

**Inputs.** Either:

```python
parse({'text': src, 'context': {...}, 'graph': 'http://g/', 'dataFactory': DF})
```

or the legacy positional form:

```python
parse(src, {'context': {...}})
```

`dataFactory` and `data_factory` are accepted; `graph` may be `None` (default
graph) or an IRI.

**Returns** a dict:

| Key | Description |
| --- | ----------- |
| `quads` | `list[Quad]` — final resolved graph state |
| `remove` | `list[Quad]` — external retractions |
| `statements` | `list[Quad]` — elevated SPO from `rdf:Statement` patterns |
| `origin` | `dict` with `quad_index`, `blocks`, `document_structure` |
| `context` | final prefix mapping (default ∪ user) |
| `primary_subject` | first non-fragment `{=IRI}`, or `None` |

```python
result = parse({'text': src, 'context': {'ex': 'http://example.org/'}})

for q in result['quads']:
    print(q.subject.value, q.predicate.value, q.object.value)

print(result['primary_subject'])
```

The `Quad` objects are RDF/JS-shaped: `q.subject`, `q.predicate`, `q.object`,
`q.graph`. Each term has `term_type` (`'NamedNode'`, `'Literal'`,
`'BlankNode'`, `'Variable'`, `'DefaultGraph'`) and `value`. Literals also
carry `language` and `datatype`.

---

## `generate(quads_or_dict, *, context=None, primary_subject=None)`

Convert quads back to deterministic MD-LD.

```python
result = generate({'quads': result['quads'],
                   'context': result['context'],
                   'primary_subject': result['primary_subject']})
print(result['text'])
```

Or, equivalently, using dict-spread:

```python
result = generate(parse({'text': src}))
```

**Returns** `{'text': str, 'context': dict}`. The output is round-trip safe —
`parse(generate(parsed)['text'])` yields the same quads — and applies visual
carrier styles by datatype (code spans for numbers, bold for booleans,
brackets for plain text, fenced blocks for multiline). When an entity has
`rdfs:label`, the heading uses the label; the label triple is omitted from
body literals so it is not duplicated.

If `primary_subject` is omitted, the first subject in the quads is used.

---

## `generate_node(quads_or_dict, *, focus_iri=None, context=None)`

Render every quad in which `focus_iri` appears as subject, predicate, object,
type, or datatype. Useful for node-centric views in graph explorers.

```python
node = generate_node({'quads': result['quads']},
                     focus_iri='http://example.org/alice',
                     context=result['context'])
print(node['text'])
```

**Safety-first behaviour:** if `focus_iri` is `None`, missing from the graph,
or `quads` is empty, the function returns `{'text': '', 'context': ...}`. It
*never* falls back to printing the full graph — this prevents accidental
megabyte-sized outputs when a caller (or LLM) passes a misspelled IRI.

`focusIRI` is accepted as an alias.

---

## `merge(docs, options=None)`

Merge multiple MD-LD documents with diff-polarity resolution.

```python
merged = merge([doc_a_text, doc_b_text, parse({'text': doc_c})],
               {'context': {'ex': 'http://example.org/'}})
```

`docs` may mix raw strings and existing parse-result dicts.

**Returns** a dict:

| Key | Description |
| --- | ----------- |
| `quads` | merged graph state (positives that survived retraction) |
| `remove` | external retractions still pending |
| `statements` | elevated SPO across all documents |
| `origin` | `{'documents': [...], 'quad_index': {...}}` with per-quad `documentIndex` and polarity |
| `context` | accumulated context (default ∪ option ∪ per-doc) |
| `primarySubjects` | list of primary subjects in merge order |

The hard invariant `quads ∩ remove = ∅` is maintained; an external retract in
a later document cancels a positive emitted by an earlier document.

---

## `locate(quad, origin)`

Look up the source-map entry for a quad.

```python
for q in result['quads']:
    entry = locate(q, result['origin'])
    if entry:
        print(entry['carrierType'], entry['range'], '→', entry['value'])
```

**Returns** the origin entry or `None`. Each entry contains:

| Field | Meaning |
| ----- | ------- |
| `blockId` | identifier of the containing block |
| `range` | `{'start': int, 'end': int}` character span in the source |
| `carrierType` | e.g. `'heading'`, `'list'`, `'blockquote'`, `'span'`, `'code'` |
| `subject` | subject IRI |
| `predicate` | predicate IRI |
| `context` | active prefix context at parse time |
| `value` | raw carrier text |
| `polarity` | `'+'` for assertion, `'-'` for retraction |

Use it for click-to-source navigation, hover previews, audit trails, or
precise error reporting. See [origin.md](origin.md) for patterns.

---

## `render(text, options=None)`

Parse MD-LD and emit HTML annotated with RDFa.

```python
out = render(src, {'context': {'ex': 'http://example.org/'},
                   'baseIRI': 'http://example.org/'})
print(out['html'])
```

**Returns** `{'html', 'context', 'metadata'}` where `metadata` reports
`blockCount`, `quadCount`, and `renderedRDFaCount`. Pass `'strict': True` to
also receive `quadMap` and `validation` (`allQuadsRendered`, `orphanedQuads`).

---

## Composition patterns

```python
from mdld_parse import parse, generate, generate_node

# 1. parse → generate (semantic extraction / canonicalisation)
canonical = generate({**parse({'text': src, 'context': ctx})})

# 2. generate → parse (normalise external RDF into MD-LD form)
normalised = parse({**generate({'quads': external_quads, 'context': ctx})})

# 3. parse → generate_node (focus on one IRI)
view = generate_node({**parse({'text': src})},
                     focus_iri='http://example.org/alice')
```

`parse` and `generate` agree on `quads`, `context`, and `primary_subject`, so
plain `**`-spread is enough; no key renaming required.

---

## Utilities

| Symbol | Purpose |
| ------ | ------- |
| `DEFAULT_CONTEXT` | built-in prefixes (`rdf`, `rdfs`, `xsd`, `sh`, `prov`, `@vocab`) |
| `DataFactory` | RDF/JS-style factory: `named_node`, `literal`, `blank_node`, `default_graph`, `quad`, `from_term` |
| `expand_iri(iri, context)` | CURIE / fragment expansion against a context |
| `shorten_iri(iri, context)` | inverse of `expand_iri` |
| `parse_semantic_block(text)` | parse a `{...}` payload into its tokens |
| `hash_str(s)` | stable identifier hashing used by the parser |
| `quad_index_key(s, p, o)` | the `subject|predicate|object` index key |
| `quad_to_key_for_origin(quad)` | same key, computed from a `Quad` |
| `create_literal(value, datatype=None, language=None)` | term constructor |
| `extract_local_name(iri, context=None)` | local fragment of an IRI for display |

---

## Bridging to `rdflib`

The terms produced by `mdld_parse` are not `rdflib` objects, but converting is
trivial:

```python
from rdflib import Graph, URIRef, Literal as RLiteral, BNode
from mdld_parse import parse

result = parse({'text': src})
g = Graph()
for q in result['quads']:
    s = URIRef(q.subject.value) if q.subject.term_type == 'NamedNode' else BNode(q.subject.value)
    p = URIRef(q.predicate.value)
    if q.object.term_type == 'Literal':
        o = RLiteral(q.object.value,
                     lang=q.object.language or None,
                     datatype=URIRef(q.object.datatype.value) if q.object.datatype else None)
    elif q.object.term_type == 'NamedNode':
        o = URIRef(q.object.value)
    else:
        o = BNode(q.object.value)
    g.add((s, p, o))

print(g.serialize(format='turtle'))
```

---

## Errors and edge cases

- Malformed annotations are skipped, not raised — MD-LD is forgiving by
  design. Unknown prefixes, malformed IRIs, and unbalanced braces all degrade
  silently to "no triple emitted" so a partial document still parses.
- `generate()` is round-trip safe but only over data MD-LD can express
  (no blank nodes, no rdf:List literal sugar, etc.).
- `merge()` enforces `quads ∩ remove = ∅`. If the same triple ends up on both
  sides, the positive wins and the retraction is dropped.
