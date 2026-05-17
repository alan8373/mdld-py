# MD-LD few-shot reference

## Mental model

Annotations generate RDF triples. Free-form prose outside `{...}` is ignored
by the graph. Subject context persists until the next `{=IRI}` declaration or
explicit `{=}` reset.

## Strict grammar

```
Prefixes:
[my]     <tag:myemail@example.com,2026:>
[folded] <my:folded:>

Subjects:
=IRI         # full IRI; persists
=#fragment   # relative to current subject; replaces current fragment

Predicates:
p            # literal property
?p           # object property
!p           # reverse property

Objects:
+iri         # temporary object for ?/! predicates
+#fragment   # temporary fragment object

Classes:
.Class       # S rdf:type Class

Inline value carriers:
[value]        # link/bracket span
**value**      # strong
*value*        # emphasis
`value`        # code
[label](url)   # link with URL
![alt](url)    # image with URL

Block value carriers:
# heading
- list item
> blockquote
```fenced``` code block

Modifiers:
^^datatypeIRI  # typed literal
@lang          # language-tagged literal
```

## Rules

- `{=IRI}` sets the current subject.
- `{+IRI}` introduces an object node without changing the subject.
- `?p` is forward; `!p` is inverse.
- Literals come **only** from value carriers — never from raw text.

## Invariants

- Every triple comes from an annotation.
- Every literal comes from a value carrier.
- `{=}` resets the current subject and scopes.
- Lists do not propagate semantics; each item is annotated explicitly.
- Never invent predicates or prefixes.
- No blank nodes — every node is an IRI.
- Avoid `example.org`. Prefer `tag:myemail@example.com,2026:` (RFC 4151).

## Default context

`rdf`, `rdfs`, `xsd`, `sh`, `prov` are always available. `@vocab` defaults to
`rdfs:`.

## Examples

### 0. Alice knows Bob

Plain text:

> Alice knows Bob.

MD-LD:

```md
[my]   <tag:alice@example.com,2026:>
[foaf] <http://xmlns.com/foaf/0.1/>

[Alice] {=my:alice} knows [Bob] {+my:bob ?foaf:knows}.
```

Expected RDF (Turtle):

```turtle
@prefix my:   <tag:alice@example.com,2026:> .
@prefix foaf: <http://xmlns.com/foaf/0.1/> .

my:alice foaf:knows my:bob .
```

### 1. A journal entry

Plain text:

> Today was a good day. I was happy and the weather was sunny. I went to
> Central Park and met Sam.

MD-LD:

```md
[my] <tag:alice@example.com,2026:>
[j]  <my:journal:>

# 2026-02-27 {=j:2026-02-27 .j:Record j:date ^^xsd:date}

## A nice day in the park {label}

Mood [happy] {j:mood} with energy [8] {j:energyLevel ^^xsd:integer}.
Visited [Central Park] {+my:central-park ?my:location .my:Place label @en}.
Weather: [Sunny] {my:weather}.
Met [Sam] {+my:sam .my:Person ?j:met}.
```

### 2. Project tasks

Plain text:

> Project Alpha has three tasks: design schema (done), implement parser
> (done), write documentation (in progress, including an API reference).

MD-LD:

```md
[ex] <http://example.org/>

# Project Alpha {=ex:ProjectAlpha .ex:Project label}

Project includes tasks:

- Design schema      {+#task1 ?ex:hasTask .ex:Task label}
- Implement parser   {+#task2 ?ex:hasTask .ex:Task label}
- Write documentation {=#task3 ?ex:hasTask .ex:Task label}

  with subtask:

  - API reference    {+#subtask3a ?ex:subTask .ex:Task label}

# Status

**Design schema** {=#task1} is [ready]    {?ex:status +ex:done},
**Implement parser** {=#task2} is [done]   {?ex:status +ex:done},
**Documentation** {=#task3} is [in process] {?ex:status +ex:in-process},
the **API reference** {=#subtask3a} is still [to do] {?ex:status +ex:todo}.
```

### 3. A reified observation

Plain text:

> A lab observation: the calibration bot updated the spectrometer firmware,
> recorded by Dr. Lena Ortiz with confidence 0.97.

MD-LD:

```md
[lab] <tag:lab@example.com,2026:>

# Lab journal

## System update {=lab:obs1 .rdf:Statement .prov:Entity}

[The calibration bot]     {+lab:calibBot       ?rdf:subject}
[updated]                 {+lab:performedUpdate ?rdf:predicate}
[the spectrometer firmware]{+lab:spectrometerFW ?rdf:object}.
Confidence [0.97]         {lab:confidence ^^xsd:decimal}.

## Verification {=lab:act1 .prov:Activity}

[Dr. Lena Ortiz] {+lab:lenaOrtiz .prov:Agent ?prov:wasAssociatedWith}
finished at [2026-02-18T06:42:00Z] {prov:endedAtTime ^^xsd:dateTime}.
```

### 4. SHACL shape

Plain text:

> A product must have exactly one label and a price ≥ 0.01.

MD-LD:

```md
[ex] <http://example.org/>

The **Product Validation Shape** {=ex:ProductValidationShape .sh:NodeShape label}
targets [Products] {+ex:Product ?sh:targetClass} for validation.

**Product Name Rule** {=ex:#productName .sh:PropertyShape ?sh:property}
requires the [label] {+rdfs:label ?sh:path} property to have exactly
[1] {sh:minCount sh:maxCount ^^xsd:integer} value.

> Product must have exactly one label. {sh:message}

{=ex:ProductValidationShape}

**Product Price Rule** {=ex:#productPrice .sh:PropertyShape ?sh:property}
requires the [price] {+ex:price ?sh:path} property to be at least
[0.01] {sh:minInclusive ^^xsd:decimal}.

> Product price must be positive. {sh:message}
```

## Invalid vs valid

Invalid: `{ex:energy "8"^^xsd:integer}` — literals do not live inside `{...}`.

Valid: `[8] {ex:energy ^^xsd:integer}` — the value comes from the carrier.

## Pattern summary

```
Literal:   [value] {predicate}
Object:    [value] {+IRI ?predicate}
Statement: {=stmt .rdf:Statement}
           [A] {+S ?rdf:subject} [B] {+P ?rdf:predicate} [C] {+O ?rdf:object}
Activity:  {=act .prov:Activity}
           [Agent] {+A .prov:Agent ?prov:wasAssociatedWith}
           [time]  {prov:endedAtTime ^^xsd:dateTime}
```
