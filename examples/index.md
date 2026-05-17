# Examples

Runnable MD-LD documents that exercise the parser end-to-end. Each one is
plain CommonMark-with-annotations — pass any of them to `parse()` and you get
back the corresponding RDF graph.

## By category

### Quick start
- [minimal.md](minimal.md) — smallest possible document with a subject and
  one fact.

### Cookbook
- [Cookbook.md](Cookbook.md) — recipe with ingredients, equipment,
  nutritional facts, and related items.

### Few-shot grammar
- [few-shot.md](few-shot.md) — concise grammar reference plus worked
  examples (good prompt material for LLMs).

### Provenance & workflows
- [workflow.md](workflow.md) — a research workflow expressed with PROV-O
  activities and content-addressed entities.

### Self-describing
- [dogfood.md](dogfood.md) — MD-LD that documents MD-LD using MD-LD.

## Patterns demonstrated

- explicit annotations (`{...}` carries every fact)
- subject chaining via `{=IRI}` and `{+IRI}`
- prefix folding into hierarchical namespaces
- PROV-O integration for provenance
- SHACL constraints and shapes
- fragment subjects for document structure
- reverse relations with `!p`
- typed and language-tagged literals
- round-trip safety through `parse → generate`

## Running an example

```python
from pathlib import Path
from mdld_parse import parse, generate

src    = Path('examples/Cookbook.md').read_text()
parsed = parse({'text': src})

print(len(parsed['quads']), 'quads')
print(parsed['primary_subject'])

# Round-trip
canonical = generate(parsed)['text']
assert parse({'text': canonical})['quads']  # parses cleanly
```

> Use cases by domain — journals, projects, papers, schemas, products,
> workflows — live in [../docs/Use-Cases.md](../docs/Use-Cases.md).
