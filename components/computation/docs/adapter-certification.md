# Adapter certification

Adapter presence is not proof that a solver is installed, licensed, scientifically applicable, or live-tested.

| Level | Evidence boundary |
|---|---|
| A0 | Method planning only; no executable-integration claim. |
| A1 | Metadata and environment-probe contract. |
| A2 | A1 plus an explicit input contract and bounded guidance. |
| A3 | A2 plus argv command planning and conservative parser fixtures. |
| A4 | A3 plus deterministic success/failure fixtures and numerical/physical validation gates. |
| A5 | A4 plus a versioned live-solver smoke test, fixture hashes, platform record, and lawful-environment evidence. |

Every adapter record carries a structured certification object containing its level, evidence scope, evidence classes, last verification date, limitations, platform scope, solver versions, fixture hashes, and live-execution flag.

All current repository adapters remain below A5 and keep `live_execution_verified=false`. Repository fixtures can validate contracts, failure handling, conservative parsing, and internal validation gates, but they do not establish external solver availability.

An A5 promotion requires all of the following:

1. exact solver and dependency versions;
2. lawful license state where applicable;
3. platform and execution environment;
4. immutable input and output fixture hashes;
5. observed normal and failure-path results;
6. numerical convergence evidence;
7. physical validation, uncertainty, and applicability evidence;
8. regression tests and qualified review.

Removing evidence or changing the supported execution surface requires certification reassessment. The strict Adapter Schema rejects unknown fields, malformed types, level mismatches, and unsupported A5 claims.
