# From a heading to a global IRI

A short narrative — borrowed from upstream — that walks one user from "this is
just a Markdown list" to "this is a queryable knowledge graph aligned to
Wikidata", changing only what is necessary at each step.

## 1. Plain Markdown

```md
# Highest Buildings

- Burj Khalifa — ~830 m
- Shanghai Tower — ~630 m
```

Just text. No subject, no triples.

## 2. Acknowledge the list as a thing

Mint a personal IRI space using a `tag:` URI (RFC 4151) and give the heading
an explicit subject:

```md
[alice] <tag:alice@example.com,2026:>

# Highest Buildings {=alice:hb .Container label}
```

Now RDF exists:

```turtle
<tag:alice@example.com,2026:hb> a rdfs:Container ;
    rdfs:label "Highest Buildings" .
```

Three rules to remember:

- A subject without predicates emits nothing.
- A predicate without a subject emits nothing.
- Nothing is ever guessed.

## 3. Make items addressable

Each building gets its own subject:

```md
[alice] <tag:alice@example.com,2026:>

## Burj Khalifa {=alice:burj-khalifa label}

[828] {alice:height ^^xsd:integer}

## Shanghai Tower {=alice:shanghai-tower label}

[632] {alice:height ^^xsd:integer}
```

Now the data is explicit, stable, and SPARQL-queryable.

## 4. Reduce repetition with fragments

Fragments belong to the current subject base — perfect for sub-entities:

```md
[alice] <tag:alice@example.com,2026:>

# Highest Buildings {=alice:hb .Container label}

## Burj Khalifa {=#burj-khalifa label}

[828] {alice:height ^^xsd:integer}

## Shanghai Tower {=#shanghai-tower label}

[632] {alice:height ^^xsd:integer}
```

`#burj-khalifa` and `#shanghai-tower` resolve to the document IRI plus
fragment.

## 5. Validate facts and add types

```md
**Burj Khalifa** {=#burj-khalifa .alice:Skyscraper label} —
[828] {alice:height ^^xsd:integer} m, located in [Dubai] {alice:location}.

**Shanghai Tower** {=#shanghai-tower .alice:Skyscraper label} —
[632] {alice:height ^^xsd:integer} m, located in [Shanghai] {alice:location}.
```

## 6. Switch to a globally unique base

Change exactly one line:

```md
[alice] <tag:alice@example.com,2026:>
```

becomes

```md
[alice] <https://alice-blog.example.com/hb/>
```

All subjects are now globally addressable IRIs without rewriting the
document. This is *IRI alignment*, not migration.

## 7. Align with public datasets

Want to align Burj Khalifa with Wikidata? Be explicit, not destructive:

```md
### Burj Khalifa {=wd:Q134164 .alice:Skyscraper label !rdfs:seeAlso}
```

emits

```turtle
wd:Q134164 a alice:Skyscraper ;
    rdfs:label "Burj Khalifa" ;
    rdfs:seeAlso <tag:alice@example.com,2026:hb#burj-khalifa> .
```

Agents can enrich Alice's data without overwriting her intent.

## 8. The point

- Markdown stays Markdown.
- Semantics are opt-in.
- Every triple is *authored*.
- Subjects are *chosen*, not inferred.
- Alignment is explicit, reversible, and local.

MD-LD does not turn notes into data. It lets people decide when text becomes
knowledge.
