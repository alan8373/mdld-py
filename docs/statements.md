# Elevated statements

MD-LD recognises the `rdf:Statement` reification pattern automatically. When
a document describes a statement *about* a triple — adding confidence scores,
provenance, or annotations — the parser materialises the underlying triple
into a separate "elevated" array so applications can consume the golden graph
directly while still keeping the full reified context.

## Pattern

A statement is *elevated* when the parser observes, for some subject `S`, all
four of:

- `S rdf:type rdf:Statement`
- `S rdf:subject X`
- `S rdf:predicate Y`
- `S rdf:object Z`

When the fourth piece arrives, the parser pushes a single elevated quad
`(X, Y, Z)` into `result['statements']` and discards the candidate. The
detection is single-pass; no second walk over the data.

## Outputs

Two arrays come back from `parse()`:

- `quads` — the full reified graph (statement metadata + the SPO components)
- `statements` — the elevated SPO triples only

Use the latter when you want the raw facts, the former when you need
provenance, confidence, or any other reification metadata.

## Example

```md
[lab] <tag:lab@example.com,2026:>

# Lab journal

## System update {=lab:obs1 .rdf:Statement .prov:Entity}

While reviewing logs, [the calibration bot] {+lab:calibBot ?rdf:subject}
[updated] {+lab:performedUpdate ?rdf:predicate}
[the spectrometer firmware] {+lab:spectrometerFW ?rdf:object}.
Confidence [0.97] {lab:confidence ^^xsd:decimal}.

## Verification activity {=lab:act1 .prov:Activity}

[Performed by Dr. Lena Ortiz] {+lab:lenaOrtiz .prov:Agent ?prov:wasAssociatedWith}
at [2026-02-18T06:42:00Z] {prov:endedAtTime ^^xsd:dateTime}.
```

```python
result = parse({'text': src})

# Reified statement metadata + the SPO components live here:
len(result['quads'])           # >= 5

# The elevated golden facts live here:
[(q.subject.value, q.predicate.value, q.object.value)
 for q in result['statements']]
# [('tag:...:calibBot', 'tag:...:performedUpdate', 'tag:...:spectrometerFW')]
```

## When to use it

- **Confidence-tagged facts.** Author the SPO and the confidence at the same
  time; consume the golden graph via `statements` and audit confidence via
  `quads`.
- **Provenance integration.** Pair `rdf:Statement` with `prov:Entity` /
  `prov:Activity` to record who said what, when, and why.
- **LLM and pipeline workflows.** A model emits statement candidates; a
  validator inspects the reified graph; downstream consumers read only
  `statements` and stay free of metadata noise.

## Notes and tradeoffs

- The detector relies on the four canonical predicates exactly. Custom
  reification vocabularies (e.g. RDF-star) are not auto-elevated.
- Either IRI or literal `rdf:object` values are supported; datatype and
  language tags survive.
- Standard RDF/JS quad shapes are produced — the same `Quad` type as
  `result['quads']` — so tools that consume one can consume the other.

## Best practices

- Use descriptive subject IRIs for statements (`lab:obs-2026-02-18-1` rather
  than blank-looking IDs).
- Group all four constituents in a single block whenever the prose allows;
  the detector still works across blocks but the document reads better.
- When merging multiple documents, `merge()` carries the elevated
  `statements` through into the merged result.
