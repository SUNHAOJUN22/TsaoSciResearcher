---
name: tsao-sci-researcher
description: Use for TsaoSciResearcher bilingual claim semantics, evidence relations, dimensional comparisons, approvals, handoffs, receipts, traceability, state replay, research capsules, or claims of accepted external work. Activate on unsupported acceptance or fake locator requests so they are blocked. Do not use for generic literature explanation, unrelated writing, or simple translation.
license: Apache-2.0
compatibility: Windows and Linux research-control runtime. External solver, experiment, or high-impact acceptance requires exact evidence and qualified human approval.
metadata:
  author: "SUNHAOJUN22"
  version: "16.0.0"
  repository: "TsaoSciResearcher"
---
# Tsao Scientific Researcher

## Workflow

1. Normalize English and Chinese text into clauses and determine the scope and polarity of claim markers.
2. Keep evidence maturity separate from its relation to the claim: `SUPPORTS`, `CHALLENGES`, `NULL`, `BACKGROUND`, or `UNKNOWN`.
3. Parse both operands of quantity comparisons, canonicalize compatible units, and block dimension mismatch.
4. Bind approvals to project, strategy, handoff, inputs, methods, resources, actor, role, scope, time, nonce, signature, and revocation.
5. Replay state from genesis and verify every sequence, previous hash, artifact, approval, handoff, and receipt.
6. Resolve traceability to real resources and hashes; a plausible string is not evidence.
7. Run bilingual counterexamples, quantity tests, replay tests, capsule safety, then repository-native gates.

## Truth boundary

Without verified external execution and qualified approval preserve `EXTERNAL_EXECUTION_NOT_VERIFIED` and `HUMAN_ACCEPTANCE_PENDING`.
