[mdld] <https://mdld.js.org/>
[xsd]  <http://www.w3.org/2001/XMLSchema#>
[@vocab] <http://www.w3.org/2000/01/rdf-schema#>
[my]   <tag:mdld@example.com,2026:>
[ex]   <my:example:>

# MD-LD documenting itself {=mdld:dogfood .Class label}

> A semantic annotation layer for CommonMark Markdown that creates RDF
> knowledge graphs from explicit `{...}` annotations. {comment}

## Default context {=mdld:default-context .Class label}

Built-in prefixes (always available):

- `@vocab` → `http://www.w3.org/2000/01/rdf-schema#` {+mdld:vocab ?member}
- `rdf`   → `http://www.w3.org/1999/02/22-rdf-syntax-ns#` {+mdld:rdf-prefix ?member}
- `rdfs`  → `http://www.w3.org/2000/01/rdf-schema#` {+mdld:rdfs-prefix ?member}
- `xsd`   → `http://www.w3.org/2001/XMLSchema#` {+mdld:xsd-prefix ?member}
- `sh`    → `http://www.w3.org/ns/shacl#` {+mdld:sh-prefix ?member}
- `prov`  → `http://www.w3.org/ns/prov#` {+mdld:prov-prefix ?member}

## Prefix folding {=mdld:prefix-folding .Container label}

Hierarchical namespaces:

- Base namespace `[my] <tag:mdld@example.com,2026:>` {+mdld:base ?member}
- Derived `[ex] <my:example:>` {+mdld:derived ?member}, resolves to
  `tag:mdld@example.com,2026:example:`.

Resolution rules:

- forward-reference only
- circular references stay literal
- later declarations override earlier ones

## Angle-bracket URLs {=mdld:angle-urls .Container label}

External resources as soft subjects:

- <https://www.w3.org/TR/rdf11-concepts/> {.Specification label}
- <https://github.com/davay42/mdld-parse> {?mdld:upstream .Repository label}
- <https://arxiv.org/abs/2301.07041>      {!mdld:cites .Paper label}

## Core principles {=mdld:principles .Container label}

- **Markdown-preserving** {+#markdown-preserving ?member label} — strip `{...}` → valid Markdown
- **Explicit only**       {+#explicit-only       ?member label} — no implicit semantics
- **Single-pass**         {+#single-pass         ?member label} — streaming-friendly
- **Deterministic**       {+#deterministic       ?member label} — same input → same output
- **Traceable**           {+#traceable           ?member label} — every fact traces to source

## Predicate forms {=mdld:predicates .Class label}

Three predicate directions:

- **Subject → Literal**: `[MD-LD] {label}` creates `mdld:doc rdfs:label "MD-LD"`.
- **Subject → Object**:  `[RDF](https://www.w3.org/RDF) {?mdld:seeAlso}` creates `mdld:doc rdfs:seeAlso <https://www.w3.org/RDF>`.
- **Object → Subject**:  `[Example] {!mdld:isDefinedBy}` flips the direction.

## Type declarations {=mdld:types .Container label}

- Single: [Single type] {+mdld:single ?member .Class label}
- Multiple: [Multiple types] {+mdld:multiple ?member .Class .mdld:Class1 label}

## Literals {=mdld:literals .Container label}

Typed:

[2026] {mdld:year ^^xsd:gYear}
[3.14] {mdld:pi   ^^xsd:decimal}
[true] {mdld:bool ^^xsd:boolean}

Language-tagged:

[Hello]   {mdld:greeting @en}
[Bonjour] {mdld:greeting @fr}
[Hola]    {mdld:greeting @es}

## Code blocks {=mdld:code-blocks .Container label}

```python {=mdld:python-example .Class text}
from mdld_parse import parse
result = parse({'text': '# Hi {=ex:hi label}\n'})
```

## Connected graph {=mdld:graph .Class label}

Every concept above is explicitly typed and related to the document subject,
so the graph mirrors the structure of the document. The document is both
specification and proof of concept.

> The graph is the document; the document is the graph. {comment}
