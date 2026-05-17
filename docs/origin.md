# Origin tracking

Every quad emitted by `parse()` carries a back-pointer into the source text.
That back-pointer powers click-to-source UIs, hover previews, audit reports,
and precise error messages — without any second pass over the document.

## Shape

`result['origin']` is a plain dict:

```python
{
    'quad_index':         {key: entry, ...},
    'blocks':             {block_id: {...}, ...},
    'document_structure': [...],
}
```

`locate(quad, origin)` looks a quad up in `quad_index` (constant time) and
returns its entry, or `None`:

```python
{
    'blockId':     '4ac750c12',
    'range':       {'start': 33, 'end': 53},
    'carrierType': 'blockquote',          # heading | list | blockquote | span | code
    'subject':     'http://example.org/alice',
    'predicate':   'http://www.w3.org/2000/01/rdf-schema#label',
    'context':     {'ex': 'http://example.org/'},
    'value':       'Alice Smith',
    'polarity':    '+',                    # '+' for assertion, '-' for retraction
}
```

`quad_index_key` and `quad_to_key_for_origin` (in `mdld_parse.utils`) build
the same `subject|predicate|object` key the parser uses internally — handy
when you want to walk the index yourself.

## Why a separate "lean" origin

`origin` is read-only and immutable after parsing. It stores only the metadata
that downstream tooling actually needs:

- O(1) lookup from quad → source span
- minimal memory overhead (~one small dict per quad)
- no shared mutable state between parses

The single-pass parser fills the index as it emits quads. Nothing else writes
to it.

## Common patterns

### Click-to-source

```python
def show_quad(quad, origin, source):
    entry = locate(quad, origin)
    if entry is None:
        return None
    start, end = entry['range']['start'], entry['range']['end']
    return {
        'snippet': source[start:end],
        'block':   entry['blockId'],
        'kind':    entry['carrierType'],
    }
```

### All quads from a single block

```python
quads_in_block = [
    q for q in result['quads']
    if (e := locate(q, result['origin'])) and e['blockId'] == target_block_id
]
```

### Audit report

```python
from collections import Counter

origin = result['origin']
report = {
    'total':      len(result['quads']),
    'by_carrier': Counter(),
    'by_block':   Counter(),
    'polarity':   Counter(),
}
for q in result['quads']:
    e = locate(q, origin)
    if e:
        report['by_carrier'][e['carrierType']] += 1
        report['by_block'][e['blockId']] += 1
        report['polarity'][e['polarity']] += 1
```

### Error reporting

```python
def validate(quads, origin, rules, source):
    errors = []
    for q in quads:
        for rule in rules:
            if not rule.check(q):
                e = locate(q, origin) or {}
                errors.append({
                    'rule':     rule.name,
                    'message':  rule.message,
                    'quad':     q,
                    'snippet':  source[e['range']['start']:e['range']['end']]
                                if e else None,
                    'block':    e.get('blockId'),
                })
    return errors
```

### Multi-document provenance

`merge()` extends every origin entry with `documentIndex` and a polarity flag,
so you can ask "which document contributed this quad?":

```python
merged = merge([doc_a, doc_b, doc_c])
for q in merged['quads']:
    e = locate(q, merged['origin'])
    print(e['documentIndex'], e['polarity'], q.subject.value)
```

## Best practices

- **Cache lookups in tight loops.** `locate()` is fast, but if you iterate the
  graph hundreds of times, memoise on `quad_to_key_for_origin(q)`.
- **Always handle `None`.** Origin entries exist for emitted quads; if you
  pass a quad you constructed yourself, `locate()` returns `None`.
- **Treat origin as read-only.** Mutating entries breaks the invariant the
  parser relies on for round-trip safety.
