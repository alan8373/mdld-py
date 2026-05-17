# Use cases

MD-LD shines wherever you already write Markdown but want some of it to be
queryable. A short tour of patterns from the upstream project, lightly
adapted.

## Personal knowledge management

### Journal entries

```md
[alice] <tag:alice@example.com,2026:>

# Meeting Notes {=alice:meeting-2026-01-15 .alice:Meeting label}

Attendees:

- **Alice** {+alice:alice ?alice:attendee .alice:Person label}
- **Bob**   {+alice:bob   ?alice:attendee .alice:Person label}

Action items:

- **Review proposal** {+alice:task-1 ?alice:actionItem .alice:Task label}
```

The same Markdown reads naturally to humans and yields a clean RDF graph
linking the meeting, its attendees, and its action items.

### Project tracking

```md
[my] <tag:myproject@example.com,2026:>

# Project Alpha {=my:proj-alpha .my:Project label}

Team:

- **Alice** {+my:alice ?my:teamMember .my:Person label}
- **Bob**   {+my:bob   ?my:teamMember .my:Person label}

Tasks:

- **Design schema**     {+my:t1 ?my:hasTask .my:Task label}
- **Implement parser**  {+my:t2 ?my:hasTask .my:Task label}
```

Use polarity to track status changes (`{-status}`, `{status}`) and
fragments for sub-tasks.

## Developer documentation

### Endpoints

```md
[api] <https://api.example.com/>

# GET /users/:id {=api:users-show .api:Endpoint label}

Method: [GET] {api:method}
Path:   [/users/:id] {api:path}

```bash {=api:users-show#example .api:CodeExample api:code}
curl https://api.example.com/users/123
```
```

Code blocks are first-class value carriers, so executable examples ship as
typed RDF resources alongside the prose.

### Schema docs (SHACL)

```md
[schema] <https://schema.example.com/>

# User shape {=schema:user .sh:NodeShape label}

## Required {=schema:user-name .sh:PropertyShape ?sh:property}
[name] {+schema:name ?sh:path}
[1]    {sh:minCount ^^xsd:integer}
[1]    {sh:maxCount ^^xsd:integer}

> User must have exactly one name. {sh:message}
```

The schema document and the constraints it documents share a vocabulary —
SHACL itself can validate it.

## Academic research

```md
[alice] <tag:alice@example.com,2026:>

# Paper {=alice:paper-mdld .alice:ScholarlyArticle label}

[Semantic Markdown] {label}
[Alice Johnson] {=alice:alice ?alice:author .prov:Person label}
[2026]          {alice:datePublished ^^xsd:gYear}

> A study on semantic annotation in Markdown. {comment @en}
```

Pair this with PROV-O to record citations, derivations, and authorship
chains.

## Content management

### Blog post

```md
[blog] <https://myblog.example.com/>

# Understanding MD-LD {=blog:post-mdld .blog:Post label}

## Introduction {=#intro .blog:Section label}
[MD-LD] {label} embeds RDF directly in Markdown without breaking it.

## Conclusion {=#conclusion .blog:Section label}
[Get started] {label} with the quick guide.

## Metadata {=#meta .blog:Section}
[Published]    {blog:status}
[2026-01-15]   {blog:datePublished ^^xsd:date}
[5 min]        {blog:readingTime}
```

Search engines and feed readers see structured data immediately; the prose
stays human.

### Product catalog

```md
[products] <https://products.example.com/>

# Smart Watch {=products:watch-200 .products:Product label}

## Specs {=#specs .products:Section}
[1.2" OLED]    {products:screenSize}
[Touchscreen]  {products:interface}
[48 hours]     {products:batteryLife}
[Water resistant] {products:feature}

## Compatibility {=#compat .products:Section}
[iOS]     {+products:ios     ?products:compatibleWith .products:Platform label}
[Android] {+products:android ?products:compatibleWith .products:Platform label}

## Pricing {=#pricing .products:Section}
[299.00] {products:price ^^xsd:decimal}
[USD]    {products:currency}
[Available] {products:availability}
```

## Data integration

### Database documentation

```md
[db] <https://db.example.com/>

# User table {=db:users .db:Table label}

## Schema {=#schema .db:Section}

### id {=db:users.id .db:Column label}
[integer]        {db:type}
[primary key]    {db:constraint}
[auto increment] {db:constraint}

### email {=db:users.email .db:Column label}
[string]  {db:type}
[unique]  {db:constraint}
```

## Workflow automation

### Process model

```md
[process] <https://company.example.com/processes/>

# Invoice processing {=process:invoice .process:Workflow label}

Steps:

- **Data entry**   {+process:p-entry    ?process:step .process:Step label}
- **Approval**     {+process:p-approval ?process:step .process:Step label}
- **Payment**      {+process:p-payment  ?process:step .process:Step label}

Integrations:

- **Accounting** {+process:accounting ?process:integratesWith .process:System label}
- **CRM**        {+process:crm        ?process:integratesWith .process:System label}
```

## Cross-cutting tips

- **Start with the prefix block.** `[ex] <http://...>` lines first, then
  content.
- **Pick a base IRI early.** A `tag:` URI keeps things personal until you are
  ready to publish; switch to `https://...` later by changing one line.
- **Use fragments for structure.** They keep namespaces flat and let you
  rename a section without breaking links.
- **Use polarity for change.** Versioning, type migration, environment
  overlays, cleanup — all expressible as diffs.
- **Validate generated triples.** Round-trip through `parse → generate →
  parse` in CI to catch regressions.
- **Watch performance.** Parsing is linear; generation is linear; both are
  cheap. The expensive step is whatever you do with the resulting graph.
