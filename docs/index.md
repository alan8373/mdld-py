# Documentation

This is the documentation hub for the Python port of `mdld-parse`. The MD-LD
format itself — and most of the design language used here — comes from the
[upstream JavaScript project](https://github.com/davay42/mdld-parse). The
documents below adapt that material to the Python API surface.

## Core

- [Guide](Guide.md) — one-page mental model and patterns
- [Syntax](Syntax.md) — full syntax reference with examples
- [API](API.md) — `parse`, `generate`, `merge`, `locate`, `render`
- [Subject](Subject.md) — subject declarations and IRI strategies

## Features

- [Origin](origin.md) — lean source-map and `locate()`
- [Polarity](polarity.md) — diff authoring with `+` / `-`
- [Primary subject](primary-subject.md) — the document's central entity
- [Elevated statements](statements.md) — `rdf:Statement` pattern lifting

## Internals

- [Architecture](Architecture.md) — design principles and pipeline
- [Parser](Parser.md) — token model, semantic blocks, emit rules

## Applied

- [Use cases](Use-Cases.md) — patterns for journals, projects, papers, schemas

## Related

- [Examples](../examples/index.md) — runnable MD-LD documents
- [Specification](../spec/index.md) — formal spec and ABNF/EBNF grammars
- [Tests](../tests/) — pytest suite covering the Python port
