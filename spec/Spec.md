# MD-LD specification

**Markdown-Linked Data** — a deterministic, streaming-friendly semantic
annotation layer for CommonMark Markdown that emits RDF quads only from
explicit `{...}` annotations.

This document is a Python-port adaptation of the upstream specification at
<https://github.com/davay42/mdld-parse>. Substance is unchanged; surface
language and code samples are written for Python.

---

## 1. Guarantees

A conformant MD-LD processor must hold these guarantees:

1. **Markdown stays valid.** Removing all `{...}` blocks yields plain Markdown.
2. **No hidden meanings.** Nothing is inferred from layout or structure.
3. **Every fact comes from `{...}`.** All triples originate in an annotation.
4. **One-pass processing.** The grammar admits a single forward scan.
5. **No blank nodes.** Every entity has an IRI.
6. **No guessing.** No inference, no heuristics.
7. **Traceable.** Every emitted quad maps back to a source span.

These guarantees together make MD-LD deterministic.

## 2. Graph model

MD-LD writes triples — *Subject → Predicate → Object* — over two kinds of
nodes:

- **IRIs** — globally unique identifiers; can appear as subjects or objects.
- **Literals** — data values (text, numbers, dates, …); appear only as
  objects.

Every fact connects exactly two nodes via a predicate. The result is a
directed labeled multigraph.

## 3. Annotation context (S, O, L)

When the parser meets `{...}`, it knows about up to three things:

- **S** — the current subject IRI, set by `{=IRI}` or `{=#fragment}`.
- **O** — an object IRI from a link, image, or `{+IRI}` in this annotation.
- **L** — a literal value drawn from the attached value carrier.

A predicate emits a triple only when the roles it requires are present.

## 4. Value carriers

`{...}` attaches to exactly one value carrier — the carrier supplies `L`.

### Inline

| Markdown | Captures |
| -------- | -------- |
| `[text] {...}` | bracketed text |
| `*text* {...}` / `_text_ {...}` | emphasis |
| `**text** {...}` / `__text__ {...}` | strong |
| `` `text` {...} `` / `` ``text`` {...} `` | code span |

### Block

| Markdown | Captures |
| -------- | -------- |
| `# Heading {...}` | heading text |
| `- item {...}` / `1. item {...}` | list-item text |
| `> quote {...}` | quote text |
| ` ```lang {...} ` (or `~~~lang {...}`) | code-block body |

### Links and media

| Markdown | Captures | Notes |
| -------- | -------- | ----- |
| `<URL> {...}` | URL | URL becomes a soft subject |
| `[label](URL) {...}` | label + URL | label is `L`, URL is the soft object |
| `![alt](URL) {...}` | alt + URL | alt is `L`, URL is the soft object |

When both an explicit IRI (`{=IRI}` or `{+IRI}`) and a link URL appear, the
explicit IRI wins. URLs become navigational only.

What cannot carry: bare paragraphs, plain URLs without `<...>`, anything
ambiguous. Ambiguous attachment emits no triple.

## 5. Attachment rules

`{...}` attaches by:

1. **Nearest preceding inline carrier** on the same line, otherwise
2. **The block carrier** containing it, otherwise
3. **Stand-alone** — applies to the current subject or to the following
   list block when that list immediately follows.

If attachment is ambiguous, no triple is emitted.

## 6. Subjects

| Form | Effect |
| ---- | ------ |
| `{=IRI}` | set the current subject to `IRI` |
| `{=#fragment}` | set subject to `currentSubjectBase#fragment` (requires existing subject) |
| `{=}` | semantic reset — clear subject and active scopes |
| `{+IRI}` | temporary object IRI for `?p` / `!p` in this block only |
| `{+#fragment}` | temporary fragment object |

The subject persists until replaced or reset.

### Primary subject

The first non-fragment subject declaration becomes the document's primary
subject. Once detected, the primary subject is locked: a `{=}` reset clears
the current subject for further annotations but does not change the primary
subject. If there is no full-IRI subject declaration, the primary subject is
`None`.

`parse()` returns it as `primary_subject`; `merge()` returns ordered
`primarySubjects` across input documents; `generate()` accepts a
`primary_subject` so that round-tripped output places it first.

## 7. Types

```
.Class
```

Emits `S rdf:type Class`. Multiple type tokens are allowed in the same
annotation. `-.Class` retracts.

## 8. Predicates

Three forms — and only three:

| Form | Edge | Use |
| ---- | ---- | --- |
| `p`  | S → L | literal property |
| `?p` | S → O | object property |
| `!p` | O → S | reverse object property |

A predicate emits a quad only when every required role is present and
type-valid. Missing pieces silently skip.

### 8.1 Polarity (retraction)

Prefix `-` to any predicate or type token:

| Form | Effect |
| ---- | ------ |
| `-p` | remove S → L |
| `-?p` | remove S → O |
| `-!p` | remove O → S |
| `-.Class` | remove `rdf:type` |

Routing against the live quad buffer:

- if the corresponding positive exists, **cancel** (neither side appears in
  the result)
- otherwise, the negative is recorded as an **external retract** in
  `result['remove']`

`parse()` returns `{quads, remove, ...}`; the hard invariant `quads ∩ remove
= ∅` is enforced after the main pass.

Subject (`{=IRI}`), soft-object (`{+IRI}`), datatype (`^^…`) and language
(`@…`) tokens have no polarity; a leading `-` on those forms is invalid and
is ignored with a warning.

## 9. Literals

Literals come only from the attached value carrier.

```
[2024] {published ^^xsd:gYear}     # typed literal
[Hello] {greeting @en}             # language-tagged literal
```

Datatype (`^^IRI`) and language (`@lang`) are mutually exclusive and never
inferred.

## 10. Object resources

Available from:

- link URLs `[label](URL)`
- image URLs `![alt](URL)`
- explicit IRIs `{+IRI}` or `{=IRI}` inside the annotation

The same annotation can attach further facts (label, type, …) to the object.

## 11. Lists

Lists are **pure Markdown structure** with no semantic scope. Each item must
annotate itself; nothing propagates from list to item. `+IRI` on each item
maintains subject chaining for repeated object properties.

For ordered semantic lists (e.g. SHACL `sh:in`), construct `rdf:List` chains
explicitly with `rdf:first` / `rdf:rest` / `rdf:nil`.

## 12. Reverse relationships

`!p` flips edge direction without changing meaning. The "object" of the
relationship plays the subject role of the emitted triple; the current
subject becomes the object.

## 13. Code blocks

Place `{...}` on the opening fence; the body becomes the literal `L`. The
body is not parsed as MD-LD.

## 14. Semantic reset

`{=}` clears:

- the current subject
- active predicates
- list scopes and reverse predicates
- any pending annotation context

The primary subject is **not** cleared.

## 15. Context and prefixes

### Default context

```python
{
    '@vocab': 'http://www.w3.org/2000/01/rdf-schema#',
    'rdf':    'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
    'rdfs':   'http://www.w3.org/2000/01/rdf-schema#',
    'xsd':    'http://www.w3.org/2001/XMLSchema#',
    'sh':     'http://www.w3.org/ns/shacl#',
    'prov':   'http://www.w3.org/ns/prov#',
}
```

### Prefix declarations

```
[name] <iri>
```

apply forward from the line of declaration. Later declarations override
earlier ones.

### Prefix folding

A prefix may reference a previously declared prefix. The reference is
expanded immediately, forward-only. Circular references stay literal.

```
[my]     <tag:mymail@domain.com,2026:>
[j]      <my:journal:>
[org]    <https://org.example.com/>
[person] <org:person/>
[emp]    <person:employee/>
```

`emp:harry` resolves to `https://org.example.com/person/employee/harry`.

### Vocabulary

`[@vocab] <iri>` redefines the default vocabulary used to expand
unprefixed predicate names.

## 16. Forbidden constructs

To preserve determinism and streaming friendliness, MD-LD forbids:

- implicit labels, types, or subjects
- structural inference (lists, headings, indentation)
- blank nodes
- key=value attribute syntax
- predicate guessing
- multi-pass / backtracking parsing
- CURIEs inside Markdown link URLs
- semantic propagation through list scope

## 17. Conformance

A conformant MD-LD processor must:

1. Follow predicate routing rules in §8.
2. Emit quads only from explicit `{...}` blocks.
3. Implement single-pass streaming parsing.
4. Produce deterministic output.
5. Maintain traceable origins for every emitted quad.
6. Support all three predicate forms with polarity.
7. Return `primary_subject` (parse) and `primarySubjects` (merge).
8. Round-trip through MD → RDF → MD without loss.

## 18. Python API surface (this port)

| Function | Purpose |
| -------- | ------- |
| `parse({'text': src, ...})` | text → quads + origin |
| `generate({...})` | quads → deterministic MD-LD |
| `generate_node({...}, focus_iri=...)` | quads → MD-LD around one IRI |
| `merge([doc, ...], options)` | combine documents with diff polarity |
| `locate(quad, origin)` | quad → source-map entry |
| `render(text, options)` | MD-LD → HTML + RDFa |

See [../docs/API.md](../docs/API.md) for full signatures and examples.
