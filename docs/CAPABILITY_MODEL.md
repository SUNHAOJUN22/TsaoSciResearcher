# Capability model

The v2 catalog contains **341 records**:

```text
322 named AI-for-Science catalog contracts
+ 19 native runtime/core contracts (18 base records and one strategy extension)
= 341 total records
```

The 322 named records comprise 158 general research contracts and 164 computation/engineering domain contracts. Each record preserves a stable internal ID, a public slug/name, routing metadata, inputs/outputs, validators, failure/recovery guidance, approval points, references and a computation boundary.

Implementation levels mean:

- `native-research` — executed by the deterministic core or repository validators;
- `human-review` — structured support with a mandatory qualified decision;
- `computation-delegated` — method and validation contract requiring a real external tool or TsaoSciComputation handoff.

A named record is discoverable and testable metadata. It is not proof that a database, model, solver or instrument is installed or that a scientific task ran.

## Catalog updates and caches

Catalog loading and search read bounded UTF-8 snapshots before consulting their
caches. The cache identity includes the actual contents of both the base and
extension catalogs. A same-size edit or replacement therefore invalidates the
relevant rows and search index even when the modification timestamp is retained.
The exact snapshot used as the cache key is also the one decoded and validated;
an invalid replacement cannot be hidden by an earlier cached result.

This retains the JSON size limit, strict duplicate-key and numeric validation,
and detached result objects. Parsing and index construction remain cached, but
each access reads the current files. Writers should publish complete catalog
updates atomically; simultaneous in-place edits are not a transactional snapshot
across multiple files.
