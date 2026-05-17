# MD-LD One-Page Guide

> *Semantic Markdown — no guessing, no magic.*

Add `{...}` and you have an RDF graph. Strip `{...}` and you have plain
Markdown. Everything semantic is **explicit**, **local**, and **traceable**.

---

## 0. Mental model

MD-LD writes triples:

```
Subject ──predicate──▶ Object / Literal
```

At every annotation up to three things may be in scope:

| Symbol | Meaning |
| ------ | ------- |
| **S** | current subject (an IRI) |
| **O** | object IRI from a link, image, or `{+iri}` |
| **L** | literal text from the attached value carrier |

No subject → no triple. No carrier → no literal. No `{...}` → no semantics.

---

## 1. Start with a subject

A casual note becomes addressable as soon as you give it a subject.

```md
[alice] <tag:alice@example.com,2026:>

# Walnut Bread {=alice:walnut-bread .Recipe name}
```

Yields:

```turtle
<tag:alice@example.com,2026:walnut-bread>
  a schema:Recipe ;
  schema:name "Walnut Bread" .
```

Subjects are *chosen*, not inferred — that is the whole point.

### Prefix folding

Build hierarchical namespaces by composing previously declared prefixes:

```md
[my] <tag:mymail@domain.com,2026:>
[j]  <my:journal:>
[c]  <my:class:>
[p]  <my:property:>

# 2026-01-27 {=j:2026-01-27 .c:Event p:date ^^xsd:date}
```

`j:2026-01-27` resolves to
`tag:mymail@domain.com,2026:journal:2026-01-27`. Forward-reference only;
circular references stay literal.

---

## 2. Value carriers

Only these Markdown forms can carry a literal:

**Inline:** `[text]`, `*em*`, `**strong**`, `` `code` ``

**Block:** headings, list items, blockquotes, fenced code blocks

If `{...}` cannot attach unambiguously to a carrier, **nothing is emitted**.

---

## 3. The three predicates

| Form | Emits |
| ---- | ----- |
| `p`  | S → L |
| `?p` | S → O |
| `!p` | O → S |

There is nothing else. All three at once:

```md
[alice] <tag:alice@example.com,2026:>

# Walnut Bread {=alice:walnut-bread}

[Bread] {name}
[Walnut] {+alice:walnut ?hasIngredient}
[Recipe](https://en.wikipedia.org/wiki/Recipe) {!hasPart}
```

> Use plain URLs in Markdown links — never CURIEs. Browsers must be able to
> follow them.

---

## 4. Literals are local

Datatypes and languages are never inferred — say them yourself:

```md
[2024] {published ^^xsd:gYear}
[Delicious bread] {description @en}
```

---

## 5. Object IRIs

Objects come from links, images, or `{+iri}`:

```md
[Walnuts](tag:alice@example.com,2026:walnut) {?ingredient}
```

or, equivalently:

```md
[Walnuts] {+alice:walnut ?ingredient}
```

---

## 6. Lists are pure structure

Lists carry **no semantic scope**. Each item must be annotated explicitly:

```md
[alice] <tag:alice@example.com,2026:>

Ingredients: {=alice:recipe .Container}

- Walnuts {+alice:walnut ?member .alice:Ingredient name}
- Flour   {+alice:flour  ?member .alice:Ingredient name}
- Water   {+alice:water  ?member .alice:Ingredient name}
```

Use nested lists or separate sections when a single item needs more facts.

---

## 7. Fragments make sections addressable

```md
[alice] <tag:alice@example.com,2026:>

# Walnut Bread {=alice:walnut-bread}

## Instructions {=#steps .HowTo}

### Mixing {=#step-1 .HowToStep label}

> Mix ingredients {text}

### Baking {=#step-2 .HowToStep label}

> Bake for 45 minutes {text}
```

Fragments resolve relative to the *current subject base* and replace any prior
fragment.

---

## 8. Blockquotes for prose facts

```md
> A dense, rustic bread with toasted walnuts. {description}
```

---

## 9. Code blocks are first-class values

````md
```txt {=alice:walnut-bread#formula .Recipe text}
500g flour
300ml water
```
````

The whole code body becomes the literal; the language fence is preserved.

---

## 10. Reverse relations

```md
Used in: {!hasIngredient}

- Bread {=alice:bread}
```

Same triple as the forward form, written from the other side.

---

## 11. What MD-LD never does

- No implicit subjects, predicates, labels, or types
- No blank nodes
- No backtracking; the parser is single-pass
- No semantic propagation through list scope

Every triple is *authored*, not derived.

---

## 12. Calling it from Python

```python
from mdld_parse import parse, generate, locate

text = "[ex] <http://example.org/>\n\n# Hello {=ex:hello label}\n"

parsed = parse({'text': text})
print(parsed['quads'])             # list of Quad
print(parsed['primary_subject'])   # 'http://example.org/hello'

origin = parsed['origin']
for q in parsed['quads']:
    entry = locate(q, origin)
    print(entry['carrierType'], entry['range'], '→', entry['value'])

# Round-trip
mdld = generate(parsed)['text']
```

`parse()` and `generate()` accept dict inputs and return dicts whose keys line
up, so you can compose them with `**`-spread:

```python
canonical = generate({**parsed})
```

---

## One-line summary

> **MD-LD is RDF you can read, write, diff, query, and share — without ever
> leaving Markdown.**
