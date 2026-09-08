# TsaoDFT Release Acceptance

## Acceptance decision

The repository software is accepted only when the deterministic machine report states:

```text
software_acceptance.state = SOFTWARE_ACCEPTANCE_READY
external_execution.state = EXTERNAL_HOLD
```

`SOFTWARE_ACCEPTANCE_READY` is deliberately scoped to repository software: source code, Schemas, adapters, documentation, governance, the permanent Linux/Windows CI contract and its regression gates. It does not claim execution on a licensed Gaussian, VASP, Quantum ESPRESSO, CP2K or other external solver.

The canonical acceptance artifact is:

```text
release-acceptance.json
```

Generate it with:

```bash
python scripts/build_release_acceptance.py --out release-acceptance.json --json
```

The permanent quality gate deterministically generates and validates the same file before coverage, security and final unit-test stages. The accepted commit SHA and successful CI run bind the verified generator, Schema and input contracts; the operator should regenerate and retain `release-acceptance.json` from that exact accepted commit as part of the handoff package.

## Software-side acceptance scope

The report verifies all of the following without invoking an external engine:

1. `VERSION` and `docs/CAPABILITY_STATUS.yaml` identify the same release.
2. Every registered capability is implemented at `L2_VALIDATED_ADAPTER` or `L3_EXECUTION_TESTED` and its declared scripts exist.
3. The quality-gate stage order is exact and includes release acceptance, coverage, Bandit, repository validation and the complete unit-test suite.
4. The permanent workflow contains Linux Python 3.10/3.12/3.13, a real `windows-latest` control-plane job, supply-chain/SBOM audit and CodeQL.
5. Compute-contract evidence remains valid, invokes no external engine and publishes no performance ratio.
6. The scientific-claim policy, acceleration doctrine, acceptance Schema, permanent CI and capability registry are content-addressed in the report.
7. Any missing file, contract drift, malformed/non-finite JSON, capability downgrade, CI matrix change or evidence promotion changes the software state to `UNQUALIFIED`.

## External execution hold

`EXTERNAL_HOLD` remains mandatory until the operator supplies all of the following as real evidence:

- licensed solver binary and exact version;
- fixed accepted input set and method fingerprint;
- engine build, CPU/GPU/MPI and hardware fingerprints;
- site identity and globally unique run IDs;
- at least three repeated runs for each candidate;
- immutable verified artifacts and parser acceptance;
- scientific reference values and explicit tolerances;
- content-addressed evidence root and independent signed review.

Correctness qualification must pass before performance qualification. Repository fixtures, detected GPUs, generated job scripts, synthetic profiles and the fastest single run cannot lift `EXTERNAL_HOLD`.

## Operator handoff

For repository acceptance, deliver together:

1. `release-acceptance.json` regenerated from the exact accepted commit;
2. `compute-contract-evidence.json` regenerated from the same commit;
3. `coverage-report.json` for Linux Python 3.12;
4. the Windows control-plane artifact;
5. dependency-audit JSON and CycloneDX SBOM;
6. the permanent CI run URL showing all six jobs successful.

If external execution is not part of the current acceptance scope, record the final decision as:

```text
Repository software: SOFTWARE_ACCEPTANCE_READY
External solver correctness/performance: EXTERNAL_HOLD
```

## Unified repository qualification

`SOFTWARE_PREFLIGHT_READY` verifies only preflight contracts. It never grants final software qualification. The full quality runner writes `quality-run-acceptance.json` after every required stage has actually finished. The monorepo CI and its exact-commit receipt remain authoritative.
