# Specification

The MD-LD format itself is specified by the upstream project. This directory
mirrors the relevant material so the Python port stays self-contained.

- [Spec.md](Spec.md) — full specification
- [Spec-compact.md](Spec-compact.md) — terse spec for quick lookup
- [grammar/mdld.ebnf](grammar/mdld.ebnf) — W3C/ISO 14977 EBNF grammar
- [grammar/mdld.abnf](grammar/mdld.abnf) — RFC 5234 ABNF grammar

## Format overview

MD-LD = CommonMark Markdown + explicit `{...}` annotations producing RDF.

- **Subjects** declared with `{=IRI}`, fragments with `{=#frag}`, reset with `{=}`
- **Predicates** in three forms: `p`, `?p`, `!p`
- **Types** with `.Class`
- **Polarity** with `+` (default) and `-` for retraction
- **Origin** tracking on every emitted quad
- **Streaming** parser; single pass; no inference

See [../docs/Architecture.md](../docs/Architecture.md) for design rationale
and [../docs/Parser.md](../docs/Parser.md) for the implementation tour.

## Conformance

A conformant MD-LD parser:

1. Implements predicate routing per §8 of the spec.
2. Emits quads only from explicit `{...}` blocks.
3. Parses in a single forward pass without backtracking.
4. Produces deterministic output for the same input.
5. Tracks origin for every emitted quad.
6. Supports `p`, `?p`, `!p` and `+/-` polarity for all of them.
7. Returns `primary_subject` from `parse()` and `primarySubjects` from
   `merge()`.

The Python port covers all of these; the test suite (`pytest tests/`) walks
the spec scenarios end-to-end.

## Tests as a living spec

The pytest suite in `../tests/` doubles as an executable specification. Each
test is a small MD-LD document and the quads / origin entries it must
produce. Run them with:

```bash
pytest tests/
```
