# Scientific trust model

The state chain is explicit:

```text
proposed → planned → prepared → submitted → running → completed
         → parsed → converged → validated → accepted
```

A zero process exit status proves only process completion. Acceptance remains fail-closed until the record includes numerical convergence, physical checks, uncertainty, applicability, evidence lineage, and any required expert approval.

Capability records identify required evidence and failure modes. Solver adapters default `live_execution_verified` to `false`. High-risk reactor, dynamic-control, digital-twin, safety, runaway, and commercial-handoff capabilities require human approval.
