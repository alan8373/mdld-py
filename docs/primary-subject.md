# Primary subject

The **primary subject** is the document's central entity. It is a small,
deterministic feature with outsized usefulness for identification, merge
tracking, and round-trip generation.

## Selection rules

1. The first non-fragment subject declaration (`{=IRI}`) becomes the primary
   subject.
2. Fragment declarations (`{=#frag}`) never qualify — they describe
   sub-entities of an existing subject.
3. Once detected, the primary subject is **locked**: a `{=}` reset clears the
   current subject for further annotations but does not change the primary
   subject of the document.
4. If a document has no full-IRI subject declaration, the primary subject is
   `None`.

## Examples

```md
[ex] <http://example.org/>

# Document {=ex:doc .ex:Article label}
[Alice] {ex:author}
```

`primary_subject == 'http://example.org/doc'`

A leading fragment does not qualify:

```md
[ex] <http://example.org/>

# Document {=ex:doc}
{=#summary}
[Content] {label}
```

still has `primary_subject == 'http://example.org/doc'` — the fragment
`#summary` is a sub-subject.

A reset does not unset the primary:

```md
[ex] <http://example.org/>

# First {=ex:first}
[Value] {label}

# Reset {=}

# Second {=ex:second}
[Value] {label}
```

`primary_subject == 'http://example.org/first'`.

## API

`parse()` returns it directly:

```python
parse({'text': src})['primary_subject']   # str | None
```

`merge()` returns the ordered list of primary subjects across the merged
documents:

```python
merge([doc_a, doc_b, doc_c])['primarySubjects']
# ['http://...', 'http://...', 'http://...']
```

`generate()` accepts a `primary_subject` so the round-tripped output places
that subject first — the easiest way to keep generation deterministic when a
document describes more than one entity:

```python
parsed = parse({'text': src})
out    = generate({**parsed})    # uses parsed['primary_subject'] automatically
```

If you do not pass it, `generate()` falls back to the first subject in the
quads.

## Use cases

- **Document identification.** "What does this MD-LD file describe?" → its
  primary subject.
- **UI navigation.** A graph explorer can default to focusing on the primary
  subject when opening a document.
- **Merge tracking.** `merge()` exposes the primary subject of each input so
  you can show users which entities were involved.
- **Query optimisation.** Use the primary subject as the default scope when
  building SPARQL queries against a document.

## Conformance

A conformant MD-LD parser must:

1. Track the first non-fragment subject declaration as the primary subject.
2. Return `primary_subject` in `parse()` results (or `None` if none).
3. Return `primarySubjects` in `merge()` results, ordered by merge.
4. Keep the primary subject locked once detected; `{=}` resets do not clear
   it.
