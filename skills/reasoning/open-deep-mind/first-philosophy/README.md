# First Philosophy Module / 第一哲学模块

Canonical method: [`METHOD.md`](METHOD.md)

This module asks a prior question before solution design:

> **What may legitimately count as a foundation for this inquiry?**

It is a core OpenDeepMind module. It is **independent of TRIZ** and must never load TRIZ.

## Activation

Use First Philosophy when definitions, ontology, evidence standards, causality, scope, values, ethics, or the problem frame itself are material. In high-impact or highly ambiguous work it normally precedes First Principles.

## Input contract

```text
Question:
Decision/deliverable:
Why it matters:
Known evidence:
Current framing:
Stakeholders:
Required confidence:
```

## Output contract — Foundation Charter

The module outputs:

```text
question + rival frames
definitions
ontology
epistemic status
logic / causality / explanation commitments
boundary / scale / time
values / duties / stakeholders
accepted / conditional / rejected foundations
blocking unknowns
```

Machine-readable schema: [`foundation-charter.schema.json`](foundation-charter.schema.json)  
Example: [`example-foundation-charter.json`](example-foundation-charter.json)

## Φ8 invariant

```text
Φ0 Suspend inherited frame
Φ1 Semantic audit
Φ2 Ontology map
Φ3 Epistemic audit
Φ4 Logical audit
Φ5 Causality and explanation audit
Φ6 Boundary, scale and time audit
Φ7 Value, ethics and praxis audit
```

`Φ0..Φ7` is exactly eight stages.

## Handoff

```text
First Philosophy
  -> Foundation Charter
  -> ../first-principles/METHOD.md
```

Only `accepted`, `accepted conditionally`, and `unresolved but non-blocking` foundations may be transferred. Blocking unknowns remain blockers.

## Forbidden coupling

- no TRIZ imports or TRIZ routing;
- no solution optimization before foundation qualification;
- no conversion of values into facts;
- no cross-scale claim without a bridge;
- no metaphysical certainty claim when only a working foundation is available.

## Validation

```bash
python open-deep-mind/first-philosophy/scripts/validate_module.py
```
