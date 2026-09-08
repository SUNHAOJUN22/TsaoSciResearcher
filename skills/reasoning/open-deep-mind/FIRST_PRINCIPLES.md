# First Principles / 第一性原理 — Compatibility Entry

> **Canonical module:** [`first-principles/METHOD.md`](first-principles/METHOD.md)

This root-level file is retained only for backward-compatible links and earlier installations.

The canonical First Principles module is isolated under:

```text
open-deep-mind/first-principles/
├── METHOD.md
├── README.md
├── module.json
├── model-contract.schema.json
├── decision-record.schema.json
├── example-model-contract.json
├── example-decision-record.json
└── scripts/validate_module.py
```

Use [`first-principles/METHOD.md`](first-principles/METHOD.md) for the normalized **P9 method (`P1..P9`)** and [`first-principles/README.md`](first-principles/README.md) for its contracts.

**Isolation invariant:** the First-Principles method body does not contain TRIZ procedures and does not auto-load TRIZ. TRIZ may be entered only through the root router after explicit user activation; TRIZ concepts return here for physical, empirical, uncertainty, and falsification validation.
