# Parser internals

This document describes the implementation behind `mdld_parse.parse`. It is
useful when extending the parser, debugging odd outputs, or comparing the
Python port against the upstream JavaScript reference.

## State

The parser keeps a single mutable state dict for the whole pass:

```python
state = {
    'ctx':                  {...},   # active prefix context
    'df':                   DataFactory,
    'graph':                NamedNode | DefaultGraph,
    'quads':                [],      # final resolved positives
    'quad_buffer':          {},      # key -> Quad (live state for cancel)
    'remove_set':           set(),   # external retractions
    'origin': {
        'quad_index':         {},    # key -> origin entry
        'blocks':             {},    # blockId -> block metadata
        'document_structure': [],
    },
    'current_subject':      None,
    'primary_subject':      None,
    'statements':           [],
    'statement_candidates': {},      # incomplete rdf:Statement patterns
    'current_block':        None,
    'block_stack':          [],
}
```

| Field | Lifetime |
| ----- | -------- |
| `ctx` | persists across the document; updated per prefix |
| `quads` | accumulates final positives |
| `quad_buffer` | mutated on cancel during single pass |
| `remove_set` | accumulates external retracts |
| `origin` | grows monotonically with each emission |
| `current_subject` | tracks `{=IRI}` / `{=}` / `{=#frag}` |
| `primary_subject` | locked once on first non-fragment subject |
| `statements` | elevated `rdf:Statement` SPO triples |
| `statement_candidates` | cleared as patterns complete |

## Token types

| Type | Source pattern | Notes |
| ---- | -------------- | ----- |
| `prefix` | `[name] <iri>` | declared inline; resolved immediately |
| `heading` | ATX heading with optional attrs | level captured for nesting |
| `list` | unordered or ordered list item | indentation tracked |
| `blockquote` | `> …` line | optional attrs |
| `code` | fenced block (``` ``` or `~~~`) | language + body |
| `para` | line with inline carriers | extracts inline spans lazily |

A token records its absolute character `range`, the attribute span, and the
clean text of the carrier.

## Semantic-block parsing

`parse_semantic_block(text)` (re-exported from `utils`) turns a `{...}`
payload into a struct of subjects, objects, types, predicates,
datatype/language modifiers, and polarity. Results are cached by source
string so repeated annotations parse only once.

Token forms inside `{...}`:

| Form | Meaning |
| ---- | ------- |
| `=IRI` | full subject |
| `=#frag` | fragment subject |
| `+IRI` | soft object |
| `+#frag` | soft fragment object |
| `.Class` | type declaration |
| `IRI` | literal predicate |
| `?IRI` | object predicate |
| `!IRI` | reverse predicate |
| `^^IRI` | datatype |
| `@lang` | language tag |
| `-…` | polarity prefix on any of the above |

Token order is **semantically unordered** within a single annotation.

## Carrier extraction

For paragraph-typed tokens the parser scans inline value carriers in priority
order:

1. emphasis / strong (`*`, `_`, `**`, `__`)
2. code spans (`` `` `` first, then single backtick)
3. link / image (`[…](…)`, `![…](…)`)
4. angle-bracket URL (`<URL>`)
5. plain bracketed span (`[…]`)

Each carrier produces:

```python
{
    'type': 'link' | 'emphasis' | 'code' | 'bracket' | 'url' | 'image',
    'text': '...',           # the literal value L
    'attrs': '{...}',        # raw payload
    'attrsRange': (start, end),
    'valueRange': (start, end),
    'range': (start, end),
    'pos': end_position,     # cursor for next scan
    'url': '...',            # only for link/image/url carriers
}
```

If multiple `{...}` blocks are present, each attaches to the nearest
preceding carrier. If attachment is ambiguous, the parser emits nothing for
that block.

## Emit pipeline

For each predicate in the annotation:

1. **Resolve subject** — explicit `{=IRI}` wins, then current subject, then
   carrier URL (for `?p` / `!p`).
2. **Resolve object** — `{+IRI}` / `{+#frag}` wins, then carrier URL, then
   carrier text as literal (for `p`).
3. **Skip if incomplete** — missing pieces emit nothing.
4. **Polarity check** — for `-…`:
   - if the corresponding positive exists in `quad_buffer`, cancel
     (delete from buffer + quads + origin index)
   - else add to `remove_set`
5. **Emit** — for positives:
   - construct `Quad(s, p, o, graph)` via `DataFactory`
   - insert into `quad_buffer` keyed by `quad_index_key`
   - append to `quads`
   - record an origin entry
   - feed the statement-pattern detector

## Origin entries

```python
{
    'blockId':     str,
    'range':       {'start': int, 'end': int},
    'carrierType': str,        # 'heading' | 'list' | 'blockquote' | 'code' | 'span'
    'subject':     str,
    'predicate':   str,
    'context':     dict,
    'value':       str,
    'polarity':    '+' | '-',
}
```

The `quad_index` maps `quad_index_key(s, p, o)` to one of these — `locate()`
is a constant-time lookup over that map.

## Elevated statements

The single-pass detector watches for the `rdf:Statement` pattern. When the
parser emits any of:

- `S rdf:type rdf:Statement`
- `S rdf:subject X`
- `S rdf:predicate Y`
- `S rdf:object Z`

it records partial state per `S` in `statement_candidates`. Once all three of
`rdf:subject`, `rdf:predicate`, `rdf:object` have been seen for a typed
`rdf:Statement`, the detector materialises a single elevated SPO quad
`(X, Y, Z)` into `statements` and discards the candidate. No second pass is
required.

## Hard invariants

After the main loop the parser enforces:

1. `quads ∩ remove_set = ∅` — any triple in both is removed from `remove_set`.
2. `primary_subject` is locked: `{=}` resets do not clear it.
3. Every emitted quad has an entry in `origin.quad_index`.

## Extensibility

The pipeline is open at three points:

- **Token processors** — `_TOKEN_PROCESSORS` is a dict from token type to a
  function `(token, state) -> None`. Adding a new token type is a matter of
  inserting an entry.
- **Carrier extractors** — extending the inline carriers means adding a
  pattern to `CARRIER_PATTERN_ARRAY` and an extractor that returns the
  carrier struct above.
- **Semantic tokens** — `parse_semantic_block` can grow new sigils without
  changing emission, provided the emitter understands the new tokens.

## Errors

The parser favours graceful degradation:

- unknown prefixes → annotation skipped
- malformed IRIs → annotation skipped
- unbalanced braces inside `{...}` → annotation skipped
- ambiguous attachment → no triple emitted

Hard errors are reserved for things that prevent forward progress entirely
(e.g. an unterminated code fence that swallows the rest of the document).
