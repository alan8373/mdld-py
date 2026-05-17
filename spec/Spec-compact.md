# MD-LD spec (compact)

A condensed quick-reference for the [full spec](Spec.md).

## Guarantees

1. Markdown-preserving — strip `{...}` → valid Markdown
2. No implicit semantics — everything explicit
3. Origin only from `{...}` — every quad has a source span
4. Single-pass — no backtracking
5. No blank nodes — every node is an IRI
6. Deterministic — same input, same output
7. Traceable — quads map to source

## Graph model

`Subject → Predicate → Object`. IRIs may be subjects or objects; literals are
objects only.

## At any annotation

- **S** — current subject (IRI)
- **O** — object IRI (link/image/`{+iri}`)
- **L** — literal (from value carrier)

## Value carriers

Inline: `[…]`, `*…*`, `_…_`, `**…**`, `__…__`, `` `…` ``

Block: `# heading`, `- item`, `> quote`, fenced code

Links/media: `<url>`, `[label](url)`, `![alt](url)`

`{...}` attaches to the nearest carrier or stands alone (current subject /
following list).

## Subjects

```
{=IRI}        # set subject
{=#fragment}  # fragment of current subject
{=}           # reset
{+IRI}        # soft object (this block only)
{+#fragment}  # soft fragment object
```

## Primary subject

First non-fragment `{=IRI}` becomes primary. Locked once detected. `parse()`
returns `primary_subject`; `merge()` returns ordered `primarySubjects`;
`generate()` accepts `primary_subject` for round-trip.

## Types

```
.Class    # rdf:type Class
-.Class   # remove rdf:type
```

## Predicates

| Form | Edge | Polarity |
| ---- | ---- | -------- |
| `p`  | S → L | `-p` retracts |
| `?p` | S → O | `-?p` retracts |
| `!p` | O → S | `-!p` retracts |

Cancel against live buffer when the negative matches an existing positive;
otherwise add to `result['remove']`. Invariant: `quads ∩ remove = ∅`.

## Literals

Always from the attached carrier. Annotate with `^^IRI` or `@lang`
(mutually exclusive). Common datatypes: `xsd:string`, `xsd:integer`,
`xsd:decimal`, `xsd:boolean`, `xsd:date`, `xsd:dateTime`, `xsd:gYear`.

## Objects

From links, images, or `{+IRI}` / `{=IRI}` in the same annotation.

## Lists

Pure structure — no propagation. Each item annotates itself. Use `+IRI` to
chain repeated `?p`. Ordered semantic lists need explicit `rdf:List` chains.

## Reverse

`!p` flips direction; same triple, written from the other end.

## Code blocks

`{...}` on the opening fence; body becomes literal.

## Context

Default: `@vocab`, `rdf`, `rdfs`, `xsd`, `sh`, `prov`.

```
[name] <iri>     # add prefix
[@vocab] <iri>   # change default vocabulary
```

Prefix folding: `[j] <my:journal:>` builds hierarchical namespaces by
referencing previously declared prefixes (forward-reference only).

## Forbidden

- implicit labels / types / subjects
- structural inference
- blank nodes
- key=value attributes
- predicate guessing
- multi-pass parsing
- CURIEs inside Markdown link URLs
- semantic list propagation

## Python API

```python
from mdld_parse import parse, generate, generate_node, merge, locate, render
```

| Call | Returns |
| ---- | ------- |
| `parse({'text': src})` | `{quads, remove, statements, origin, context, primary_subject}` |
| `generate({'quads': qs, 'context': ctx, 'primary_subject': ps})` | `{text, context}` |
| `generate_node({'quads': qs}, focus_iri='...')` | `{text, context}` |
| `merge([d1, d2, ...], opts)` | `{quads, remove, statements, origin, context, primarySubjects}` |
| `locate(q, origin)` | origin entry or `None` |
| `render(src, opts)` | `{html, context, metadata}` |
