# Changelog

This Python package implements the MD-LD format designed by
[@davay42](https://github.com/davay42); the [JavaScript reference
implementation](https://github.com/davay42/mdld-parse) is the companion
source for the syntax. The Python package uses its own version line,
starting at **0.1.0**.

## 0.1.0 — 2026-05-16

First PyPI release.

### Breaking (with backward compatibility)

- Unified named-parameter API for the core functions:
  - `parse({'text': ..., 'context': ..., 'dataFactory': ..., 'graph': ...})`
  - `generate({'quads': ..., 'context': ..., 'primary_subject': ...})`
  - `generate_node({'quads': ..., 'focus_iri': ..., 'context': ...})`
  - Legacy positional `parse(text, options)` still works.

### Added

- Composition via dict-spread: outputs of `parse()` line up with inputs of
  `generate()` / `generate_node()`, so `**`-spread does the right thing.
- `generate_node()` ships with a safety-first design: returns empty text on a
  missing IRI rather than falling back to the full graph.

## 0.8.0 — 2026-04-30

### Added

- Visual carrier styles in `generate()` keyed off datatype:
  - numbers (integer/decimal/float) render as code spans
  - dates and datetimes use bracketed literals
  - booleans render bold
  - other literals use bracketed text
  - multiline content uses `~~~` fenced blocks with explicit datatype
- Heading uses `rdfs:label` when present and the label triple is omitted from
  body literals to avoid duplication.
- Object links use `rdfs:label` when available instead of repeating IRIs.
- Robust quote escaping in the data factory for round-trip safety.

### Added (cont.)

- `generate_node(quads, focus_iri=...)` for safe node-centric MD-LD output.
  Shows every quad where the IRI appears in any position; returns empty if
  the IRI is missing from the graph.

## 0.7.0 — 2026-03-23

### Breaking

- Removed `apply_diff` and the entire applyDiff infrastructure.
- Simplified `locate(quad, origin)` — no more `(quad, origin, text, context)`.
- `generate()` now returns `{'text': ..., 'context': ...}` directly.
- Removed `parse_with_merge`; use `merge()` directly instead.

### Changed

- Origin tracking switched to a lean `quad_index` map; old `quadMap`
  structure is gone.
- ~500 lines of deprecated infrastructure removed; codebase is smaller and
  easier to maintain.
- Resolved circular dependency in the merge system.

### Added

- Comprehensive tests for the lean origin system.
- Better error handling and validation in origin tracking.

### Removed

- `applyDiff.js` and related infrastructure.
- 12 deprecated utility functions.
- Slot-management / vacant-slot tracking.
- Mutable origin infrastructure for automated text mutation.

## 0.6.2 — 2026-03-23

- Full MD-LD specification implementation.
- Comprehensive test suite (~98+ tests).
- Browser and Node.js compatibility.
- Documentation and examples.

## 0.5.2 — 2026-02-17

- IRI-over-URL resolution in `[link](url) {=iri}`.

## 0.4.1 — 2026-01-27

- Prefix folding.
- `<URL> {?prop}` syntax.

## 0.4.0 — 2026-01-26

- Many small improvements.

## 0.3.5 — 2026-01-24

- Removed the `schema` default vocabulary; `rdfs` becomes the meta vocabulary
  for ontology-agnostic authoring.

## 0.3.2 — 2026-01-20

- Settled prefix declaration syntax: `[ex] <http://example.org/>`.

## 0.3.0 — 2026-01-16

- Single-character syntax for predicates / objects / fragments.

## 0.2.x — 2026-01-12 to 2026-01-16

- Spec settled: lists become pure Markdown, predicate algebra closes,
  fragments and soft IRIs land, value carriers stabilise, round-trip and
  diff workflows enter the suite.

## 0.1.x — 2025-12-31

- Default context, inferred base IRI, no front-matter parsing.
- Code blocks and `rdfs:label` in headings.
- First clean lists.

## 0.0.1 — 2025-12-30

- Initial setup.

---

## Python port notes

- API names use snake_case where idiomatic (`primary_subject`, `focus_iri`).
- The merged result keeps `primarySubjects` (camelCase) to match the upstream
  array contract.
- `parse()` accepts both the dict-style call and the legacy positional form.
- `generate()` and `generate_node()` accept either a dict or explicit
  keyword arguments.
- Term/quad shapes are RDF/JS-compatible: every term has `term_type` and
  `value`; literals also have `language` and `datatype`. Bridge to `rdflib`
  is mechanical (see `docs/API.md`).
