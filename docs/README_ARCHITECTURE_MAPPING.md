# Design → code → test mapping

This matrix maps the v0.7.0 design to executable evidence.

| Design intent | Code or artifact | Automated evidence | Status |
|---|---|---|---|
| Route before loading | `SKILL.md`, `router.py`, route contracts | property, bilingual and semantic tests | Implemented |
| Full lifecycle | 15 workflows and gates | repository cross-contract audit | Implemented |
| 322 named skills | `capabilities/v2/capabilities.json` | catalog and design-compliance tests | 322/322 |
| Recoverable state | atomic writes, locks and lifecycle transitions | state, I/O and tamper tests | Implemented |
| Evidence/claim integrity | closed schemas and validators | schema, claim and quality tests | Implemented |
| Computation preparation | `handoff.py` and v2 handoff schema | path, checksum, CLI and mutation tests | Implemented |
| External execution provenance | `receipts.py` and receipt schema | success/failure, identity, duration and hash-tamper tests | Implemented |
| Deterministic transfer | `capsule.py` and capsule manifest schema | byte identity, path safety and tamper tests | Implemented |
| Version single source | `VERSION`, sync/bump scripts | stale-metadata and audit tests | Implemented |
| Coverage and test quality | quality baseline and coverage JSON | line/branch thresholds, order and 18 mutations | Gated |
| Supply chain | exact direct lock, SBOM, pip-audit and attestation | deterministic SBOM and CI audit | Gated |
| Distribution | source ZIP, wheel and sdist | byte comparison, metadata and isolated import | Gated |
| Documentation consistency | README facts and MkDocs | README mirror/link/fact tests and strict build | Gated |
| Real external execution | connected solver/lab/HPC | guarded handoff + receipt required | External |
| Final acceptance | project approval and evidence review | distinct accepted state | Human-approved |

```text
Design requirement
  → workflow/capability/schema
  → runtime validator/state gate
  → automated test and CI artifact
  → bounded README claim
```
