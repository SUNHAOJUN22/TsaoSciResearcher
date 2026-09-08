# TsaoDFT 0.4.0-alpha.2 Release Notes

Release date: 2026-07-31  
Release type: prerelease snapshot  
Public capability level: `L2_VALIDATED_ADAPTER`

## What this release closes

This release freezes the repository-side engineering qualification completed after `0.4.0-alpha.1`. It closes the permanent quality-gate, execution trust-boundary, evidence-integrity, Parser-contract, installation-safety and supply-chain work already verified on `main` without adding a new scientific feature or claiming new real-engine coverage.

The release remains a repository-style Agent Skill suite. Gaussian, VASP, Quantum ESPRESSO, CP2K, Multiwfn, VMD, schedulers, accelerators, licensed data and site infrastructure remain external.

## Permanent quality gate

The single permanent workflow, `.github/workflows/ci.yml`, applies the same release-blocking sequence on Python 3.10, 3.12 and 3.13:

1. generated-demo and repository contracts;
2. governance, capability, security and documentation validators;
3. Ruff lint and format checks;
4. ordinary mypy across isolated targets;
5. strict mypy across the four trust-boundary modules;
6. whole-repository statement and branch coverage;
7. Bandit;
8. strict repository audit;
9. all nine unittest suites.

Hosted CI additionally runs CodeQL `security-extended`, runtime/development/locked dependency audits and locked CycloneDX JSON SBOM generation.

## Structured argv and Shell boundary

Formal engine and scheduler commands are represented as structured argument vectors rather than accepted as raw shell fragments. Executables and arguments are quoted separately. Scheduler headers, identifiers, working paths, modules, source files, launchers, environment names and control characters are validated. Generated scripts remain approval-gated and are never submitted automatically.

## Bound approval and Ed25519 review

Execution approval is bound to the Manifest SHA-256, benchmark plan, candidate and method fingerprint. Independent performance review uses Ed25519 verification and binds reviewer identity, scope, issue and expiry time, Policy, plan, candidates, key fingerprint and evidence root. Unsigned, expired, forged, scope-mismatched or digest-mismatched attestations fail closed.

## Content-addressed evidence Bundle

Formal performance evidence is first written to staging, completely verified and then atomically published under `evidence-<root_sha256>`. The evidence root covers records, summary, Policy, review, qualification state and file digest/size metadata. Missing, extra, altered, partially published or root/directory-mismatched content is rejected by an independent verifier.

## Unified four-engine Parser contract

Gaussian, VASP, Quantum ESPRESSO and CP2K selected-field Parsers now emit a common versioned state contract. Final or fatal state takes precedence over earlier success markers; missing output becomes a structured failure rather than an inferred value. Parser acceptance remains separate from scientific acceptance.

## Parser-to-benchmark bridge

Deterministic bridges join Parser output with Manifest identity, method fingerprint, runtime and scheduler provenance, GPU inventory and artifact hashes. Missing fields remain explicit. A record cannot become eligible merely because a Parser found a normal-termination marker.

## Installer rollback and concurrency protection

The installer tracks ownership, stages replacements atomically, refuses foreign or modified destinations without an accepted policy, restores the prior installation if marker publication fails and prevents concurrent installation transactions through a lock.

## Non-invoking hardware inventory

Hardware and environment inventory is bounded and non-invoking. It reports availability and identity needed for planning without launching an electronic-structure engine, exposing secret environment values or scanning unrelated filesystems. Missing optional tools are represented as `NOT_AVAILABLE`, not fabricated zeroes.

## Science-identity-locked automatic-tuning candidates

Automatic-tuning materialization preserves input SHA-256, method fingerprint and convergence-policy identity, requires an FP64 CPU reference, enforces memory/topology and candidate-count limits and resets every generated candidate to `pending`. Candidate generation is not execution and is not measured acceleration evidence.

## Public L2 boundary

The public capability remains `L2_VALIDATED_ADAPTER`. Deterministic fixtures, synthetic output excerpts, Schema validation, Parser tests, hardware-inventory fixtures and generated candidates are repository engineering evidence only.

`QUALIFIED_FOR_SCOPED_L3_PERFORMANCE_EVIDENCE` means that a bounded evidence package is eligible for review. It does not alter the public capability registry and is not equivalent to `L3_EXECUTION_TESTED`.

## External evidence still required for L3

A future scoped or public L3 record requires evidence from a legal target environment, including:

- exact engine, version, executable and build fingerprint;
- site, scheduler, CPU/GPU, driver, runtime, compiler and MPI identity;
- content-addressed real inputs and outputs;
- an accepted CPU reference and sufficient repeated candidate runs;
- numerical equivalence for declared observables before speedup;
- measured performance and resource use;
- verified artifact, Bundle and evidence-root digests;
- an Ed25519-signed independent review bound to the accepted scope;
- separate explicit public capability registration.

No external engine or scheduler was invoked to produce this release snapshot.

## Upgrade and compatibility

- Repository release notation: `0.4.0-alpha.2`.
- PEP 440 project notation: `0.4.0a2`.
- Supported CI Python versions remain 3.10, 3.12 and 3.13.
- The packaging model remains `repository-skill-suite`; no wheel or sdist support is claimed.
- Existing Skill names, routes, command interfaces, Schemas, Policy IDs, engine examples and support levels are unchanged by the version freeze.

## Explicit non-claims

This release does not claim:

- real Gaussian, VASP, Quantum ESPRESSO or CP2K regression execution;
- measured CPU/GPU or multi-GPU speedup;
- universal CUDA-X, ROCm, SYCL, Metal or native-kernel acceleration;
- scientific equivalence from fixtures or Parser tests;
- public L3 capability;
- automatic job submission;
- a Tag or GitHub Release created by the version-freeze phase.
