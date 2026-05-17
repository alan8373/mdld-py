# mdld-parse (Python)

**Markdown-Linked Data (MD-LD)** — a deterministic, streaming-friendly RDF
authoring format that extends CommonMark with explicit `{...}` annotations.

A Python implementation of the MD-LD format. The format itself was
designed by [@davay42](https://github.com/davay42), whose JavaScript
[`davay42/mdld-parse`](https://github.com/davay42/mdld-parse) is the
companion reference for the syntax.

---

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

```python
from mdld_parse import parse

text = """
[ex] <http://example.org/>

# Document {=ex:doc .ex:Article label}

[Alice] {?ex:author =ex:alice .prov:Person ex:firstName label}
[Smith] {ex:lastName}
"""

result = parse({'text': text})

for q in result['quads']:
    print(q.subject.value, q.predicate.value, q.object.value)
```

The `quads` list contains RDF/JS-shaped `Quad` objects (Python dataclasses
exposing `subject`, `predicate`, `object`, `graph`); `result['origin']` carries
the lean source map; `result['primary_subject']` names the document's central
entity.

---

## What MD-LD is

MD-LD is RDF you can read, write, diff, and share without leaving Markdown.
You add semantics by attaching `{...}` annotations to value carriers (links,
emphasis, headings, list items, code blocks, blockquotes). Strip the
annotations and you are left with normal Markdown.

Three things may be in scope at any annotation:

| Symbol | Meaning |
| ------ | ------- |
| **S** | current subject (an IRI) |
| **O** | object IRI (from a link, image, or `{+iri}`) |
| **L** | literal text from the attached value carrier |

No subject, no triple. No `{...}`, no semantics. Nothing is inferred.

### Core features

- **Prefix folding** — build hierarchical namespaces by composing prefixes
- **Subject declarations** — `{=IRI}` and `{=#fragment}` set context
- **Soft objects** — `{+IRI}`, `{+#fragment}` declare temporary objects
- **Three predicate forms** — `p` (S→L), `?p` (S→O), `!p` (O→S)
- **Type declarations** — `.Class` emits `rdf:type`
- **Datatypes & languages** — `^^xsd:date`, `@en`
- **Polarity** — `+`/`-` prefixes for diff authoring and retraction
- **Origin tracking** — every quad indexed back to its source span
- **Elevated statements** — automatic `rdf:Statement` pattern detection
- **Round-trip safe** — `parse` ↔ `generate` preserves data and primary subject

---

## Documentation

- **[docs/index.md](docs/index.md)** — documentation hub
- **[docs/Guide.md](docs/Guide.md)** — one-page mental model and patterns
- **[docs/Syntax.md](docs/Syntax.md)** — full syntax reference
- **[docs/API.md](docs/API.md)** — Python API reference
- **[docs/Architecture.md](docs/Architecture.md)** — design and pipeline
- **[docs/Parser.md](docs/Parser.md)** — parser internals
- **[docs/Subject.md](docs/Subject.md)** — subject declaration walkthrough
- **[docs/origin.md](docs/origin.md)** — lean origin / `locate()` system
- **[docs/polarity.md](docs/polarity.md)** — diff authoring and retraction
- **[docs/primary-subject.md](docs/primary-subject.md)** — primary-subject rules
- **[docs/statements.md](docs/statements.md)** — elevated `rdf:Statement` extraction
- **[docs/Use-Cases.md](docs/Use-Cases.md)** — domain-specific patterns
- **[examples/index.md](examples/index.md)** — runnable example documents
- **[spec/index.md](spec/index.md)** — formal specification and grammars
- **[CHANGELOG.md](CHANGELOG.md)** — version history

---

## A taste of the format

```markdown
[my] <tag:alice@example.com,2026:>

# 2026-02-27 {=my:journal-2026-02-27 .my:Event my:date ^^xsd:date}

## A nice day in the park {label}

Mood: [Happy] {my:mood}, energy [8] {my:energyLevel ^^xsd:integer}.
Met [Sam] {+my:sam .my:Person ?my:attendee} at
[Central Park] {+my:central-park ?my:location .my:Place label @en}.
The weather was [Sunny] {my:weather}.
```

After parsing, the document is a queryable graph keyed by
`tag:alice@example.com,2026:journal-2026-02-27` with the relevant relationships
to `my:sam`, `my:central-park`, and the typed/tagged literals.

---

## Public API

All functions live at the package root and accept dict-style inputs that
compose by spreading:

```python
from mdld_parse import parse, generate, generate_node, merge, locate, render
```

| Function | Purpose | Returns |
| -------- | ------- | ------- |
| `parse(text \| {'text': ..., 'context': ...})` | text → quads + origin | `{'quads', 'remove', 'statements', 'origin', 'context', 'primary_subject'}` |
| `generate(quads \| {'quads': ..., 'context': ..., 'primary_subject': ...})` | quads → deterministic MD-LD | `{'text', 'context'}` |
| `generate_node(..., focus_iri=...)` | quads → MD-LD centered on one IRI | `{'text', 'context'}` |
| `merge([doc1, doc2, ...], options)` | merge documents with diff polarity | `{'quads', 'remove', 'statements', 'origin', 'context', 'primarySubjects'}` |
| `locate(quad, origin)` | quad → source-map entry | `{'blockId', 'range', 'carrierType', ...}` or `None` |
| `render(text, options)` | MD-LD → HTML + RDFa | `{'html', 'context', 'metadata'}` |

The dict-spread pattern composes naturally:

```python
parsed = parse({'text': text, 'context': {'ex': 'http://example.org/'}})
canonical = generate(parsed)                       # parse → generate
node_view = generate_node(parsed, focus_iri='http://example.org/alice')
```

`parse()` also accepts the legacy positional form `parse(text, options)`; both
calls return identical results.

For the full reference, see [docs/API.md](docs/API.md).

---

## Compatibility with RDF tooling

The Python `Quad` / `NamedNode` / `Literal` / `BlankNode` / `Variable` /
`DefaultGraph` types in `mdld_parse.utils` mirror the RDF/JS data model:
each term has a `term_type` and `value`, literals carry `language` and
`datatype`, and `Quad` exposes `subject`, `predicate`, `object`, `graph`. They
serialize cleanly into common Python RDF stacks (e.g. `rdflib`) — see
[docs/API.md](docs/API.md) for an `rdflib` bridge example.

---

## Project layout

```
mdld_parse/        Python package (parse, generate, merge, locate, render)
tests/             pytest suite covering the MD-LD format
docs/              guides, syntax, architecture, parser internals
examples/          MD-LD example documents (language-agnostic)
spec/              formal specification + ABNF / EBNF grammars
```

Tests run with `pytest` from the project root.

---

## Credits

The MD-LD format was designed by [@davay42](https://github.com/davay42); the
[JavaScript reference implementation](https://github.com/davay42/mdld-parse)
is the companion source for the syntax. This package is an independent
Python implementation of the format. See [CHANGELOG.md](CHANGELOG.md) for
the version history.
