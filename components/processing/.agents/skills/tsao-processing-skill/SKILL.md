---
name: tsao-processing-skill
description: Use for TSAO-PROCESSING-SKILL process packages, polymer/process calculations, component balances, status aggregation, engineering/HSE evidence, numerical stability, or public-distribution governance. Activate on attempts to publish controlled registry content so distribution is blocked. Do not use for generic chemical-engineering explanation, unrelated coding, or prose-only editing.
license: Apache-2.0
compatibility: Windows and Linux Skill suite. Public distribution remains blocked while controlled classification lacks an authorized owner decision.
metadata:
  author: "SUNHAOJUN22"
  version: "16.0.0"
  repository: "TSAO-PROCESSING-SKILL"
---
# TSAO Processing Skill

## Workflow

1. Determine mass or molar basis, component identities, units, reaction sources, and accumulation.
2. Canonicalize before arithmetic and close every component independently.
3. Aggregate `FAIL > HOLD > CONDITIONAL/NOT_EVALUATED > PASS` without optimistic overrides.
4. Separate software integrity, engineering acceptance, and HSE status.
5. Use stable numerical forms such as `-expm1(-x)` and represent undefined statistics as `null + reason`.
6. Block public artifacts containing controlled, internal, project-controlled, or non-public-eligible records.
7. Run focused counterexamples, then the repository-native permanent gates.

## Mathematics

\[
R_{j,b}=\dot N^{in}_{j,b}-\dot N^{out}_{j,b}+G_{j,b}-C_{j,b}-\frac{dN_{j,b}}{dt}.
\]

Every required component must satisfy its own absolute-plus-relative tolerance.

## Truth boundary

Until an authorized, signed owner decision exists, preserve `BLOCKED_CONTROLLED_METADATA_CLASSIFICATION`. A software PASS is not engineering or HSE approval.
