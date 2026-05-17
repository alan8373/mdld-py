# Polarity & retraction

MD-LD treats `+` and `-` as first-class polarity markers on predicates and
type declarations. With them you can author diffs directly in Markdown,
version documents, migrate types, and merge competing edits — all without
leaving the prose surface.

## Polarity tokens

| Form | Positive | Negative | Use |
| ---- | -------- | -------- | --- |
| literal predicate | `{p}` | `{-p}` | S → L |
| object predicate | `{?p}` | `{-?p}` | S → O |
| reverse predicate | `{!p}` | `{-!p}` | O → S |
| type declaration | `{.Class}` | `{-.Class}` | rdf:type |

Inside a single annotation block you can mix positives and negatives freely.

## Resolution rules

When the parser meets a negative token, it routes against the **live quad
buffer** for the current document:

| Case | Result |
| ---- | ------ |
| matching positive in buffer | cancel both — neither lands in `quads` |
| no matching positive | append to `remove` as an external retract |

Two collections come back from `parse()`:

- `quads` — the resolved positive graph state
- `remove` — external retractions targeting prior state

The hard invariant `quads ∩ remove = ∅` is enforced in a final post-pass.
Origin entries record the polarity sign (`'+'` or `'-'`) so retractions are
visible in audit trails.

## Examples

### Intra-document cancel

```md
[ex] <http://example.org/>

# Document {=ex:doc}
[Alice] {label}
[Alice] {-label}        # cancels the line above
[Bob]   {label}
```

```python
result = parse({'text': src})
[q.object.value for q in result['quads']]   # ['Bob']
result['remove']                            # []
```

### External retract

```md
[ex] <http://example.org/>

# Document {=ex:doc}
[Alice] {-label}        # no matching positive in this doc
[Bob]   {label}
```

`result['quads']` contains only Bob's label; `result['remove']` carries the
Alice retraction so a later `merge()` can apply it against an earlier
document.

### Mixed polarity in one block

```md
# Doc {=ex:doc -.ex:Draft .ex:Published -ex:version}
[2.0] {ex:version}
```

The block flips the type from `Draft` to `Published`, removes the prior
`ex:version` value, and adds the new one. All tokens within `{...}` are
unordered.

### Reverse-property retraction

`!p` retraction needs an explicit object so the parser knows which side to
flip:

```md
[ex] <http://example.org/>

# Family
Parent: [Alice] {=ex:alice .prov:Person label}
Child:  [Bob] {+ex:bob !ex:hasParent}

# Replacement
Child is not [Bob]   {+ex:bob   -!ex:hasParent},
it's        [Bryan] {+ex:bryan  !ex:hasParent}.
```

### Type migration

```md
[ex] <http://example.org/>

# Person {=ex:person -.ex:Employee .ex:Contractor}
[Alice] {-name}
[Alice] {fullName}
```

## Real workflows

### Document versioning

```python
v1 = """
[ex] <http://example.org/>
# Article {=ex:article .ex:Article}
[Alice] {author}
[Draft] {status}
"""

v2 = """
[ex] <http://example.org/>
# Article {=ex:article}
[Alice]    {-author}
[Bob]      {author}
[Draft]    {-status}
[Published]{status}
"""

merged = merge([v1, v2])
# author -> Bob, status -> Published, Article rdf:type preserved
```

### Collaborative edits

Two authors edit the same document in parallel; both diffs are merged in the
order received. External retractions in the later document cancel positives
from the earlier one.

### Configuration overlays

```python
dev  = "[ex] <http://example.org/>\n# Config {=ex:cfg}\n[debug]{flag}\n[localhost]{host}\n"
prod = "[ex] <http://example.org/>\n# Config {=ex:cfg}\n[debug]{-flag}\n[localhost]{-host}\n[prod.example.com]{host}\n"

config = merge([dev, prod])
```

### Cleanup

Use external retracts in a "cleanup" document to drop legacy or duplicate
triples without rewriting the originals.

## Tradeoffs and limits

- Cancellation matches **exact** subject-predicate-object triples. There is
  no pattern or wildcard form.
- The parser is forward-only: a retract must follow the positive it targets
  (within the same document), or it becomes an external retract.
- Reverse retractions need an explicit object — they cannot guess which O→S
  edge you meant.
- Subject (`{=IRI}`), soft-object (`{+IRI}`), datatype (`^^…`), and language
  (`@…`) tokens have **no polarity**. A leading `-` on those forms is
  invalid and is ignored with a warning.

## Inspecting polarity in origin

Polarity sticks with the origin entry, so audits stay honest:

```python
result = parse({'text': src})
for q in result['quads']:
    e = locate(q, result['origin'])
    print(e['polarity'], e['carrierType'], e['value'])
```
