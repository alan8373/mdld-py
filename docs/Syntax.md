# Syntax Reference

MD-LD adds semantics to CommonMark via `{...}` annotation blocks. This page
collects every form supported by the parser, with examples and the resulting
RDF.

## Quick reference

| Form | Meaning |
| ---- | ------- |
| `{=IRI}` | set current subject |
| `{=#frag}` | fragment subject relative to current base |
| `{=}` | semantic reset (clear subject, predicates, scopes) |
| `{+IRI}` | temporary object for `?p` / `!p` in this block |
| `{+#frag}` | temporary fragment object |
| `.Class` | type declaration → `S rdf:type Class` |
| `p` | literal predicate (S → L) |
| `?p` | object predicate (S → O) |
| `!p` | reverse predicate (O → S) |
| `^^IRI` | datatype on the literal |
| `@lang` | language tag on the literal |
| `-token` | retraction (`-p`, `-?p`, `-!p`, `-.Class`) |

Tokens inside `{...}` are unordered. Whitespace separates them.

---

## 1. Annotation basics

```md
# Apollo 11 {=wd:Q43653 .SpaceMission}
Launched in [1969] {launchYear ^^xsd:gYear} with crew {?crew .Person name}.
```

This sets `wd:Q43653` as subject, types it `:SpaceMission`, attaches a typed
year, and starts an object predicate that will scope to the following list.

---

## 2. Value carriers

`{...}` must immediately follow a value carrier — that carrier supplies the
literal `L`.

### Inline

| Carrier | Example |
| ------- | ------- |
| `[text] {...}` | `[Apollo 11] {label}` |
| `*text* {...}` / `_text_ {...}` | `*important* {emphasis}` |
| `**text** {...}` / `__text__ {...}` | `**warning** {alert}` |
| `` `text` {...} `` | `` `console.log` {code} `` |

### Block

| Carrier | Example |
| ------- | ------- |
| `# Heading {...}` | `# Apollo 11 {=ex:mission .Mission label}` |
| `- item {...}` | `- Neil Armstrong {=ex:armstrong .Person label}` |
| `> quote {...}` | `> One small step {comment}` |
| ` ```lang {...} ` | ` ```js {=ex:code .ex:SoftwareSourceCode} ` |

### Links and media

| Carrier | Captures | Notes |
| ------- | -------- | ----- |
| `<URL> {...}` | the URL | URL becomes the soft subject of the block |
| `[label](URL) {...}` | label + URL | label is `L`; URL is the soft object |
| `![alt](URL) {...}` | alt + URL | alt is `L`; URL is the soft object |

When both an explicit `{=IRI}`/`{+IRI}` and a link URL are present, the
explicit IRI wins:

| Predicate | Subject priority |
| --------- | ---------------- |
| Type (`.Class`) | `{=IRI}` > `{+IRI}` > URL > current subject |
| Literal (`p`) | `{=IRI}` > current subject; URL only if neither |
| Object (`?p`) | current subject → `{+IRI}` or URL |
| Reverse (`!p`) | `{+IRI}` or URL → current subject |

What **cannot** carry: bare paragraphs, plain URLs without `<...>`, anything
where the attachment is ambiguous. Ambiguous attachment emits no triple.

---

## 3. Subjects

```md
{=IRI}        # full IRI; persists until reset or replaced
{=#fragment}  # appends/replaces fragment of the current subject base
{=}           # semantic reset (subject and scopes cleared)
```

Examples:

```md
# Document {=ex:doc}
{=#summary}
[Content] {label}
```

emits `ex:doc#summary rdfs:label "Content"`.

### Soft objects (block-scoped)

```md
{+IRI}     # temporary object for ?p / !p in this annotation only
{+#frag}   # temporary fragment object
```

```md
[Walnuts] {+alice:walnut ?ingredient}
[Section] {+#part-1 ?hasPart name}
```

Soft IRIs do not change the current subject.

---

## 4. Types

```md
## Apollo 11 {=ex:apollo11 .ex:SpaceMission .ex:Event}
```

emits two `rdf:type` triples. Types may be retracted with `-.Class`.

---

## 5. Predicate forms

| Form | Edge | Example | Meaning |
| ---- | ---- | ------- | ------- |
| `p`  | S → L | `[Alice] {name}` | literal property |
| `?p` | S → O | `[NASA] {=ex:nasa ?ex:operator}` | object property |
| `!p` | O → S | `[Mission] {=ex:mission !hasPart}` | reverse object |

A predicate emits a triple only when every required slot (S, P, and either O
or L) is present. Missing pieces silently skip — never guess.

### Diff polarity (retraction)

Prefix `-` to retract:

| Token | Effect |
| ----- | ------ |
| `-p` | remove S → L |
| `-?p` | remove S → O |
| `-!p` | remove O → S |
| `-.Class` | remove `rdf:type` |

If the matching positive triple exists in the current document buffer, the
negative *cancels* it. Otherwise it lands in `result['remove']` as an external
retract that future merges can apply against prior state. The hard invariant
`quads ∩ remove = ∅` is enforced.

See [polarity.md](polarity.md) for full diff workflows.

---

## 6. Literals

Literals come **only** from the attached value carrier:

```md
[2024] {published ^^xsd:gYear}
[Hello] {greeting @en}
[Bonjour] {greeting @fr}
```

Common datatypes: `xsd:string` (default), `xsd:integer`, `xsd:decimal`,
`xsd:boolean`, `xsd:date`, `xsd:dateTime`, `xsd:gYear`. Datatype and language
are mutually exclusive.

---

## 7. Object resources

Objects appear from links, images, or explicit IRIs:

```md
## References {=ex:refs}

[Alice] {=ex:alice ?author label}
[W3C RDF](https://www.w3.org/RDF) {?references label}
![Image](https://example.com/i.png) {?image label}
```

Each `?p` connects the current subject to the resource; the same annotation
can attach further facts (label, type) to that resource.

---

## 8. Lists

Lists are **pure Markdown**. They have no semantic scope; each item annotates
itself or it emits nothing:

```md
[@vocab] <http://www.w3.org/2000/01/rdf-schema#>

## Recipe {=ex:recipe .Container}

Ingredients:

- **Flour** {+ex:flour ?member .Ingredient label}
- **Water** {+ex:water ?member .Ingredient label}
```

Use `+IRI` to chain repeated object properties without rebinding the subject.
Nested lists do not inherit semantics; if a list item needs more facts, use a
nested list of explicit annotations or break out into a section with its own
subject.

For ordered semantic lists (e.g. SHACL `sh:in`), construct `rdf:List` chains
explicitly with `rdf:first` / `rdf:rest` / `rdf:nil`.

---

## 9. Reverse relationships

`!p` flips direction without changing meaning:

```md
# Chapter 1 {=book:ch1}
Is part of [The Book] {=book:book !hasPart}.
```

emits `book:book schema:hasPart book:ch1`.

---

## 10. Code blocks

Place `{...}` on the opening fence; the body becomes the literal:

````md
```js {=ex:hello .SoftwareSourceCode text}
console.log("hi")
```
````

The body is not parsed as MD-LD — it is captured verbatim as a literal.

---

## 11. Blockquotes

```md
> MD-LD bridges Markdown and RDF. {comment}
```

emits `S rdfs:comment "MD-LD bridges Markdown and RDF."`.

---

## 12. Context and prefixes

```md
[ex]      <http://example.org/>
[foaf]    <http://xmlns.com/foaf/0.1/>
[@vocab]  <http://schema.org/>
```

Built-in default context (always available):

```python
{
    '@vocab': 'http://www.w3.org/2000/01/rdf-schema#',
    'rdf':    'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
    'rdfs':   'http://www.w3.org/2000/01/rdf-schema#',
    'xsd':    'http://www.w3.org/2001/XMLSchema#',
    'sh':     'http://www.w3.org/ns/shacl#',
    'prov':   'http://www.w3.org/ns/prov#',
}
```

Prefix folding builds namespace hierarchies by composing prefixes already in
scope:

```md
[my] <tag:mymail@domain.com,2026:>
[j]  <my:journal:>
[org]    <https://org.example.com/>
[person] <org:person/>
[emp]    <person:employee/>
[dev]    <emp:developer/>
```

`dev:john` resolves to
`https://org.example.com/person/employee/developer/john`. References resolve
at declaration time, forward-only; circular references stay literal; later
declarations override earlier ones.

---

## 13. Forbidden constructs

To stay deterministic and streaming-friendly, MD-LD forbids:

- Implicit labels, types, or subjects
- Blank nodes
- Structural inference (lists, headings, indentation)
- key=value attribute syntax
- Predicate guessing
- Multi-pass / backtracking parsing
- CURIEs inside Markdown link URLs
- Semantic propagation through list scope

If you need any of these behaviours, layer them in your application — never in
the syntax.
