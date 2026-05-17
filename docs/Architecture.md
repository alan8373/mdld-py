# Architecture

`mdld_parse` is a single-pass, streaming-friendly parser/generator for MD-LD.
It mirrors the upstream JavaScript implementation closely; the design
principles below come from that project and apply equally to this port.

## Design principles

- **Streaming-first.** One pass over the input, O(n) in document size. No
  backtracking, no AST.
- **Deterministic.** Same input always produces the same quads, the same
  origin, and the same canonical generated text.
- **RDF/JS data model.** Terms (`NamedNode`, `Literal`, `BlankNode`,
  `Variable`, `DefaultGraph`) and `Quad` are shaped after RDF/JS so they
  bridge cleanly to other RDF tooling.
- **Origin tracking.** Every emitted quad indexes back to its source span
  with carrier type and polarity for round-trip and UI navigation.
- **Explicit semantics.** Nothing is inferred from structure or layout.
  Without an annotation there is no triple.
- **CommonMark fidelity.** Block boundaries come from `markdown-it-py`,
  the only runtime dependency. Lifting the previous "no dependencies"
  rule was the price of supporting `preserve_content=True` round-trip.

## Processing pipeline

The parser walks the input in five logical stages:

1. **Tokenisation.** Line-by-line scanning produces typed tokens
   (`prefix`, `heading`, `list`, `blockquote`, `code`, `para`).
2. **Context resolution.** Prefix declarations (`[name] <iri>`) update the
   active context immediately, supporting prefix folding.
3. **Subject tracking.** `{=IRI}` and `{=#fragment}` rewrite the current
   subject; `{=}` resets it.
4. **Annotation processing.** Each `{...}` is parsed once into a semantic
   block (subjects, predicates, types, datatype/language, polarity).
5. **Quad emission.** Predicates produce quads only when every required
   role (subject, predicate, and either an object IRI or a literal carrier)
   is present. Origin entries are recorded as quads are emitted.

A small post-pass enforces the hard invariant `quads ∩ remove = ∅` and
materialises elevated `rdf:Statement` patterns into the `statements` array.

## Token model

| Token | Trigger | Content |
| ----- | ------- | ------- |
| `prefix` | `[name] <iri>` | prefix mapping |
| `heading` | `# … {…}` | level + text + attrs |
| `list` | `- … {…}` / `1. … {…}` | text + attrs |
| `blockquote` | `> … {…}` | text + attrs |
| `code` | fenced block | language + body + attrs |
| `para` | inline-bearing line | inline carriers + attrs |

A token records its character `range`, attribute span, and (for paragraphs)
the inline carriers it contains. Inline carriers are extracted lazily; the
extractor checks emphasis, strong, code spans, links, images, and
angle-bracket URLs.

## Semantic blocks

A `{...}` payload is parsed into a struct shaped roughly like:

```python
{
    'subjects':   [...],    # =IRI / =#frag
    'objects':    [...],    # +IRI / +#frag
    'types':      [...],    # .Class
    'predicates': [...],    # p / ?p / !p (with polarity)
    'datatype':   '...',    # ^^iri
    'language':   '...',    # @lang
    'remove':     bool,     # leading `-` polarity
}
```

These structs are cached by source string so identical annotations parse once.

## Quad emission

The emitter applies these rules in order:

1. Resolve the subject for this annotation (`{=IRI}`, current subject,
   carrier URL, or skip).
2. For each predicate, route by form: `p` → S→L, `?p` → S→O, `!p` → O→S.
3. If polarity is negative, look up the live quad buffer; cancel if present,
   else add to the remove set.
4. On positive emission, insert into the buffer, append to the quads list,
   record an origin entry, and feed the elevated-statements detector.

Origin entries carry `blockId`, character `range`, `carrierType`, the active
context, the subject and predicate IRIs, the raw value text, and a polarity
sign — enough to support hover previews, click-to-source, and audit trails.

## Polarity and the remove set

Two collections coexist during parsing:

- `quad_buffer` — the current document's positive quads
- `remove_set` — external retractions (no matching positive seen yet)

When the parser meets `-p`, it consults the buffer:

| Case | Action |
| ---- | ------ |
| Matching positive in buffer | cancel both; emits nothing |
| No matching positive | add to remove set as external retract |

Final post-processing removes any quad whose key is in both sets. The result:
`quads` is the resolved graph state, `remove` is what the document wants to
take away from prior state. Merging consumes both arrays to compute a final
state across documents.

## Generation

`generate()` is the inverse pipeline:

1. Normalise quads (DataFactory.from_term, sort).
2. Group by subject; build a label lookup so headings can use `rdfs:label`.
3. Emit prefix declarations for context entries actually used (skipping
   built-ins).
4. Walk subjects in deterministic order — primary subject first if provided —
   and render each as a heading + literal-bearing carriers + object links.

The generator picks visual carrier styles from datatype: code spans for
numbers, bold for booleans, brackets for everything else, fenced blocks for
multiline. The result round-trips through `parse()` without loss.

## Performance

Parser cost is linear in input size; the dominant constants are regex scans
on each line and `dict`/`set` lookups for quad keys. Memory scales with quad
count plus origin index (~one small dict per quad). The generator is also
linear in quad count.

## Compatibility

The Python port targets CPython 3.10+. The terms expose attributes
(`term_type`, `value`, `language`, `datatype`) and equality semantics that
let them stand in for RDF/JS-style data model objects, and bridge to common
RDF Python libraries (`rdflib` etc.) is mechanical — see
[API.md](API.md#bridging-to-rdflib).
