# Capability model

The v2 catalog contains **340 records**:

```text
322 named AI-for-Science catalog contracts
+ 18 native runtime/core contracts
= 340 total records
```

The 322 named records comprise 158 general research contracts and 164 computation/engineering domain contracts. Each record preserves a stable internal ID, a public slug/name, routing metadata, inputs/outputs, validators, failure/recovery guidance, approval points, references and a computation boundary.

Implementation levels mean:

- `native-research` — executed by the deterministic core or repository validators;
- `human-review` — structured support with a mandatory qualified decision;
- `computation-delegated` — method and validation contract requiring a real external tool or TsaoSciComputation handoff.

A named record is discoverable and testable metadata. It is not proof that a database, model, solver or instrument is installed or that a scientific task ran.
