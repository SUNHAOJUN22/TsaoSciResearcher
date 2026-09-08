# Code Quality and Test Audit

Date: 2026-07-31  
Version: `0.4.0-alpha.2`  
Branch: `main`  
Pre-freeze qualification source commit: `3cb0925acd8605a897163e9a48f33c0a689c6454`  
Pre-freeze qualification GitHub Actions run: `30595469898`  
Release-snapshot source commit: `d02abc442f017f839311f3d52e172eb1d015a259`  
Release-snapshot GitHub Actions run: `30597772162`

## Evidence rule

A passing parser, fixture, static-analysis stage, scheduler test or acceleration materializer is engineering evidence. It is not proof of scientific correctness, legal real-engine execution or measured speedup. Unavailable account-level and external-site facts remain `NOT VERIFIED`.

## Audited scope

- the single permanent GitHub Actions workflow and all 21 quality stages;
- root validators, installers, coverage/type/security wrappers and all eight Skills;
- structured HPC execution generation and Manifest approval binding;
- executable benchmark, Policy, Parser and attestation Schemas;
- signed review, content-addressed evidence and qualification state handling;
- four engine Parser state machines and Parser-to-benchmark bridges;
- installer rollback, ownership and concurrency behavior;
- capability/public-claim boundaries and L2/L3 separation;
- 325 tests across nine isolated suites.

## Release-snapshot verification

The alpha.2 source and release-document snapshot at `d02abc442f017f839311f3d52e172eb1d015a259` was validated by GitHub Actions run `30597772162`. Python 3.10, 3.12 and 3.13, CodeQL, all three dependency-audit modes and CycloneDX SBOM generation completed successfully. The release snapshot retained 325 tests, 92.48% statement coverage, 80.18% branch coverage and the six core-module thresholds without regression.

The exact artifact IDs and digests are recorded in `docs/RELEASE_EVIDENCE_0.4.0-alpha.2.json` and `docs/RELEASE_SHA256_0.4.0-alpha.2.txt`.

## Closed P0/P1 findings

### Shell and scheduler trust boundary

Manifest commands now use structured argv. Executables and arguments are quoted individually. Job identifiers, scheduler fields, environment names, module/source fields and working paths are validated. Raw command fields and unsafe shell forms are rejected on the formal evidence path.

### Approval and independent review

Execution approval is bound to the Manifest SHA-256, benchmark plan, candidate and method fingerprint. Review attestations use Ed25519 verification with reviewer identity, scope, issue/expiry time, key fingerprint and evidence binding. A plain `status: approved` field is not sufficient.

### Atomic content-addressed evidence

Formal evidence is written to staging, fully verified and atomically renamed to `evidence-<root_sha256>`. The root Manifest covers records, summary, Policy, review, qualification and file digests. Missing, altered or extra files, wrong directory identity, digest/size mismatch and failed publication all fail closed.

### Executable Schema and Policy

Draft 2020-12 validation runs before semantic validation. Integer/date/enumeration/unknown-field rules are enforced. The performance Policy is executable rather than descriptive: repeats, real-source, artifact, numerical-equivalence, performance, review and scaling requirements are consumed by code.

### Benchmark isolation

A formal comparison accepts one benchmark plan. Candidate aggregation is separated by scientific, build, hardware and topology identity. CPU references must belong to the same plan. Invalid records cannot produce a qualified status.

### Unified engine Parser contract

Gaussian, VASP, Quantum ESPRESSO and CP2K emit a versioned common contract. Fatal markers and final-stage failure take precedence over earlier success markers. Missing outputs produce structured failures. Scientific acceptance remains pending and separate from Parser acceptance.

### Parser-to-evidence bridge

Deterministic bridges combine Parser result, Manifest, method fingerprint, runtime provenance, scheduler metrics, GPU inventory and artifact hashes. Missing data is recorded in `missing_fields`; it is never replaced with fabricated values.

### Installer transaction

Destination, backup and ownership marker are treated as a recoverable transaction. Marker failure restores the previous destination. Concurrent installation attempts are rejected by a lock.

## Static quality and security

- Ruff lint and formatting: blocking and PASS;
- ordinary mypy: 18 isolated targets, PASS;
- strict mypy: `shell_contract.py`, `trust_boundary.py`, `engine_parser_contract.py`, `benchmark_bridge.py`, PASS;
- Bandit: production sources with exact reviewed allowances, PASS;
- CodeQL Python `security-extended`: hosted blocking job, PASS;
- secret, ignore-marker, XML/YAML, governance and repository-shape validators: PASS;
- runtime, development and locked-environment `pip-audit`: PASS;
- locked CycloneDX JSON SBOM: generated and uploaded.

## Coverage result

- entire repository statement coverage: **92.48%**;
- entire repository branch coverage: **80.18%**;
- six trust/execution core modules: **100% statement**;
- core branch coverage: **98.53%–100%**.

The coverage runner measures subprocess-launched tests and CLIs, combines all nine suites and publishes a machine-readable artifact for every Python matrix job.

## Test result

- suites: 9;
- tests: 325;
- failed suites: 0.

Distribution: root 99; suite 4; researcher 32; structure 5; periodic 11; ML 16; HPC 148; kinetics 5; catalysis 5.

## Permanent quality sequence

```text
assets and contracts
→ governance, capability and security validators
→ Ruff lint and format
→ isolated mypy
→ trust-boundary strict mypy
→ statement/branch coverage
→ Bandit
→ strict repository audit
→ all unittest suites
```

## Capability boundary

The root validator checks both:

1. generic L3 execution evidence; and
2. the complete signed acceleration L3 contract for repositories declaring HPC acceleration capability.

Future HPC L3 registration requires build/hardware/site identity, repeated real-engine runs, artifact and evidence-root SHA-256, CPU reference, numerical/parser/performance passes, review attestation identity/scope/signature verification and independent approval. Non-L3 capabilities may not carry execution evidence.

The current public state remains `L2_VALIDATED_ADAPTER`.

## Remaining external limits

- legal real-engine/site/GPU execution and measured performance remain external;
- live-model Agent traces remain `NOT VERIFIED`;
- branch protection, signed commits, account secret scanning/push protection, Dependabot alert state and private reporting remain `NOT VERIFIED` through the available App;
- the user-required main-only policy remains a deliberate review-separation exception.
