# First Principles Module / 第一性原理模块

Canonical method: [`METHOD.md`](METHOD.md)

This module decomposes a problem to explicit, task-relative foundations and reconstructs models, alternatives, tests, and decisions from them.

It is a core OpenDeepMind module. It may receive a Foundation Charter from First Philosophy. It must **not automatically load TRIZ**.

## Activation

Use for design, diagnosis, mechanism analysis, architecture, cost, optimization, quantitative modeling, from-scratch reconstruction, or any task where assumptions and derivation must be explicit.

## Input contract

```text
Question:
Outcome:
Boundary / scale / time:
Known observations:
Constraints:
Values/objectives:
Optional Foundation Charter:
Required confidence:
```

## Output contract

```text
requirement verdict
D/O/L/C/A/E/V/U proposition ledger
dependency decomposition
accepted foundations
model contract
structurally distinct alternatives
derivation trace
rival model / falsifiers / stress tests
decision record
```

Schemas:

- [`model-contract.schema.json`](model-contract.schema.json)
- [`decision-record.schema.json`](decision-record.schema.json)

Fixtures:

- [`example-model-contract.json`](example-model-contract.json)
- [`example-decision-record.json`](example-decision-record.json)

## P9 invariant

```text
P1 Delete, modify, or justify requirement
P2 Define outcome and boundary
P3 Expose assumptions and proposition types
P4 Decompose to irreducibles
P5 Qualify foundations
P6 Build the model
P7 Reconstruct alternatives
P8 Derive, trace, falsify, and stress-test
P9 Decide, act, monitor, and update
```

Exactly nine stages: `P1..P9`.

## Handoffs

```text
First Philosophy -> Foundation Charter -> First Principles
First Principles -> First Philosophy repair when foundations break
First Principles -> TRIZ only after explicit user activation
TRIZ concepts -> First Principles validation
```

The canonical method body contains no TRIZ procedure; optional TRIZ routing is owned by the root router and the isolated TRIZ subsystem.

## Validation

```bash
python open-deep-mind/first-principles/scripts/validate_module.py
```
