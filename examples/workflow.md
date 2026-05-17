[wf] <tag:mdld.workflow.example,2026:>

# Minimal research workflow {=wf:workflow .prov:Entity label}

This document records a self-contained research workflow that produced a
minimal SHACL validation model for MD-LD workspaces. Every step is a PROV-O
activity that consumes some entities and generates new ones.

## Research plan {=nih:sha-256-128;4889b626d88785b4eed19b2aa6e5ca24;8 .prov:Plan label}

```txt {prov:value}
Goal:
  Define a minimal SHACL validation model for MD-LD documents.

Steps:
  1. Identify the minimal semantic primitives of MD-LD.
  2. Map those primitives to PROV concepts.
  3. Determine invariants that validation must enforce.
  4. Encode invariants as SHACL shapes.
  5. Produce a minimal reusable SHACL schema.

Success criteria:
  - shapes validate core MD-LD constructs
  - shapes remain ontology-minimal
  - shapes rely only on RDF, PROV and SHACL
```

---

## Exploration activity {=wf:exploration .prov:Activity label}

Uses plan
[research plan] {+nih:sha-256-128;4889b626d88785b4eed19b2aa6e5ca24;8 ?prov:hadPlan}.

### Exploration notes {=nih:sha-256-128;aaa55e922921171296c05b322320bc7e;5 .prov:Entity ?prov:generated label}

```txt {prov:value}
Core MD-LD primitives:
  1. Entity
  2. Activity
  3. Plan
  4. Content-addressed value
  5. Location-based artifact
  6. Provenance links

Validation requirements:
  - entities with `ni` identifiers must match the content hash
  - prov:value must appear at most once per entity
  - prov:Activity must connect inputs and outputs
  - plans must exist when referenced
```

---

## Shape design activity {=wf:shapeDesign .prov:Activity label}

Uses plan
[research plan] {+nih:sha-256-128;4889b626d88785b4eed19b2aa6e5ca24;8 ?prov:hadPlan},
draws on the exploration step
[exploration phase] {+wf:exploration ?prov:wasInformedBy},
and uses
[exploration notes] {+nih:sha-256-128;aaa55e922921171296c05b322320bc7e;5 ?prov:used}.

### Draft shape model {=nih:sha-256-128;776aee4fd5e0fe3cf808e5895a12dfb2;9 .prov:Entity ?prov:generated label}

```txt {prov:value}
Validation concepts:
  - Entity integrity
  - Activity connectivity
  - Plan presence
  - Artifact content

Design principles:
  - validate graph structure
  - avoid imposing domain semantics
  - keep shapes minimal and composable
```

---

## Validation activity {=wf:shapeValidation .prov:Activity label}

Uses plan
[research plan] {+nih:sha-256-128;4889b626d88785b4eed19b2aa6e5ca24;8 ?prov:hadPlan},
draft shapes
[draft shapes] {+nih:sha-256-128;776aee4fd5e0fe3cf808e5895a12dfb2;9 ?prov:used},
and was informed by
[shape design] {+wf:shapeDesign ?prov:wasInformedBy}.

[./shapes.ttl] {+nih:sha-256-128;4594cd6cd9079dad278ba99078437888;4 prov:atLocation .prov:Entity ?prov:generated label}

---

## Provenance summary

```
plan → exploration → exploration notes
plan + exploration → shape design → draft shapes
plan + draft shapes → validation → final SHACL schema
```

Every artifact is content-addressed (`ni:` URIs), so the workflow and its
outputs are reproducible and verifiable.
