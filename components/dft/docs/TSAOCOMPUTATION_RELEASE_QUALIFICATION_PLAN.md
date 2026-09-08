# TsaoComputation Release Qualification Contract and External Evidence Roadmap

Date: 2026-07-31  
Branch policy: `main` only

## Current phase status

The repository-side release qualification for the evidence trust boundary, Parser contract and permanent quality gate is closed. The last fully completed documentation CI entering this status normalization was commit `9d4550588062e0ff90dfc6071ccd9e1db0c9883a`, GitHub Actions run `30558895182`.

The repository currently has:

- Python 3.10, 3.12 and 3.13 permanent quality gates;
- Ruff lint and formatting;
- ordinary mypy across 18 isolated targets;
- strict mypy for `shell_contract.py`, `trust_boundary.py`, `engine_parser_contract.py` and `benchmark_bridge.py`;
- blocking whole-repository coverage thresholds of 90% statement and 80% branch;
- 100% statement and at least 95% branch coverage requirements for the six trust/HPC core modules;
- Bandit, strict repository audit and nine non-empty unittest suites;
- CodeQL, runtime/development/locked dependency audits and CycloneDX SBOM generation;
- structured-argv execution contracts and scheduler/path/environment injection rejection;
- Manifest-bound approval, executable Schemas and field-by-field Policy enforcement;
- Ed25519-signed independent review bound to Policy, plan, candidates and evidence root;
- atomic content-addressed evidence publication and independent Bundle verification;
- a unified Gaussian/VASP/Quantum ESPRESSO/CP2K Parser state contract and deterministic Parser-to-benchmark bridges;
- installer rollback and concurrent-install locking;
- non-invoking hardware inventory and bounded autotuning candidate generation.

## Repository acceptance gates

A repository commit is release-qualified only when all of the following pass on that commit:

1. whole-repository statement coverage at or above 90%;
2. whole-repository branch coverage at or above 80%;
3. six core modules at 100% statement and at least 95% branch coverage per file;
4. Ruff lint and formatting;
5. ordinary and strict trust-boundary mypy;
6. Bandit and strict repository audit;
7. all nine test suites;
8. Python 3.10, 3.12 and 3.13 matrix jobs;
9. CodeQL, three dependency-audit layers and CycloneDX SBOM.

Thresholds may not be met by narrowing the production denominator, excluding reachable code, adding blanket coverage pragmas or lowering the formal minima.

## Evidence and capability boundary

Repository tests, deterministic fixtures, synthetic engine excerpts, Parser validation and generated benchmark candidates are engineering evidence. They do not establish legal real-engine execution, scientific equivalence on a real site or measured acceleration.

`QUALIFIED_FOR_SCOPED_L3_PERFORMANCE_EVIDENCE` is evidence-package eligibility only. The public capability remains `L2_VALIDATED_ADAPTER` unless a separate explicit registration supplies the complete accepted L3 contract.

## External evidence roadmap

The following evidence must come from a legal target environment and is not fabricated or auto-submitted by this repository:

- exact engine, version, executable and build fingerprint;
- site, scheduler, CPU/GPU, driver, runtime, compiler and MPI identity;
- content-addressed inputs and outputs;
- an accepted CPU reference and sufficient repeated candidate runs;
- numerical equivalence for declared scientific observables before speedup;
- measured wall time, resource use and optional energy metrics;
- verified artifacts, Bundle digest and evidence-root SHA-256;
- Ed25519-signed independent review bound to Policy, plan, candidates and evidence root;
- explicit public capability registration.

Gaussian, VASP, Quantum ESPRESSO, CP2K or any other external engine must not be run merely to satisfy repository CI. No job is submitted automatically.

## Closure interpretation

Repository-internal release blockers are distinct from missing external L3 evidence. A green repository release does not claim L3 execution coverage; missing real-site evidence remains an explicit external limitation rather than an unresolved repository defect.
