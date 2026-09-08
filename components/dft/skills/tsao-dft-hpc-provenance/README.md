# Tsao DFT HPC and Provenance

General execution Skill for computational chemistry on local machines, Slurm, PBS and cloud/HPC. It generates reviewable scripts and provenance records but does not submit without explicit approval.

```bash
python scripts/validate_hpc_manifest.py examples/slurm/hpc-manifest.yaml
python scripts/generate_job_script.py examples/slurm/hpc-manifest.yaml --out job.slurm
python scripts/classify_failure.py examples/failures/gaussian-memory.log
```

## Acceleration registry

`plan_acceleration.py` and `hardware_optimization_contract.py` load library, alias and backend compatibility views at runtime from `scripts/acceleration_registry.py`. They no longer maintain independent mirror catalogs. The root quality gate rejects a planner that reintroduces a local `_library` catalog or stops loading the canonical registry.

```bash
python ../../scripts/validate_acceleration_registry.py --json
```

Registry membership is planning metadata. It does not prove that CUDA-X, ROCm, oneAPI, Metal or any external DFT engine is installed or executed.

## Profile-gated software acceleration cores

The repository keeps Python as the scientific control plane and does not treat a whole-repository C++ rewrite as an optimization strategy. The binding engineering authority is [`../../docs/ACCELERATION_ENGINEERING_DOCTRINE.md`](../../docs/ACCELERATION_ENGINEERING_DOCTRINE.md).

The first implemented repository-owned numerical core is the governed neighbor-search layer in `../tsao-structure-prep/scripts/neighbor_list.py`. It preserves scalar and NumPy references, adds deterministic cell-list candidate reduction and supports non-periodic, orthogonal, triclinic and partial-periodic geometry. It does not select a GPU implicitly and does not establish DFT-engine speedup.

The shared parser transport is `scripts/engine_scan_core.py`. It maps non-empty output artifacts read-only, calculates the mapped SHA-256 and exposes bounded literal/regex scans, last-marker resolution and block boundaries. `engine_parser_contract.py` consumes this core for Gaussian, VASP, Quantum ESPRESSO and CP2K. This reduces duplicated parser transport and preserves fatal-over-success semantics; it is parser/workflow acceleration, not electronic-structure acceleration.

Native C++/OpenMP and CUDA/HIP/SYCL remain profile-, build- and equivalence-gated. A native sidecar or device backend cannot be claimed until it exists, builds on the governed platforms, falls back safely and matches the CPU reference under explicit scientific tolerances.

## Benchmark-result authority and migration

The only authoritative production contract is the nested v1.1 Schema:

```text
templates/benchmark-result.schema.json
```

The repository-level `../../templates/benchmark-result.schema.json` is a byte-identical mirror checked by the permanent gate. Producers such as `benchmark_bridge.py`, import/validation commands, signed performance qualification and the bounded compute campaign all converge on this contract.

The internal semantic validator is also native nested v1.1. `performance_evidence.validate_canonical_result()` rejects any other version. The public `validate_result()` entrypoint first routes input through `benchmark_contract.normalize_record()` and then invokes native v1.1 semantics. There is no nested v1.0 semantic downgrade view and no internal rewrite from `1.1` to `1.0`.

Two historical contracts remain explicit compatibility inputs only:

- **nested v1.0** has the same evidence shape and is accepted only by the central adapter, which performs a version-only transition to v1.1 before semantic validation;
- **flat v1.0** is preserved as `templates/benchmark-result-flat-v1.0.schema.json` and requires an explicit `scientific-reference` or `acceleration-candidate` role mapping.

The nested v1.0 transition preserves the submitted evidence and does not promote its qualification. Direct nested v1.0 calls to the native semantic function fail closed. Flat v1.0 cannot encode every v1.1 provenance field. Migration therefore never guesses the engine executable, model identity, convergence thresholds or original artifact path. Missing or contradictory information is written to `evidence_source.missing_fields`, the source becomes `imported-unverified`, and qualification remains `EXTERNAL_HOLD`.

The flat adapter also records lossy or contradictory cases explicitly, including:

- runtime/backend claims that disagree with the hardware inventory;
- an accelerated scientific-reference role;
- an acceleration candidate without accelerator identity;
- parser acceptance that conflicts with exit or convergence evidence;
- heterogeneous accelerator inventories that nested v1.1 cannot represent losslessly;
- missing build/hardware identities, simulated sources and `ml-surrogate` mapping to `generic`.

Unknown versions, mixed flat/nested documents, duplicate identities and non-finite values fail closed.

```bash
python ../../scripts/validate_benchmark_contract.py --json

python scripts/import_benchmark_evidence.py \
  legacy-results/*.json \
  --schema templates/benchmark-result.schema.json \
  --legacy-reference-candidate CPU-REFERENCE \
  --legacy-acceleration-candidate GPU-CANDIDATE \
  --out build/evidence.jsonl \
  --report build/evidence-import-report.json
```

The role flags are required only for flat v1.0 because that historical shape did not record the role. They are not inference switches and cannot upgrade evidence eligibility.

A caller-provided custom Schema remains available for nonqualifying ingestion. Such records keep their original version, receive `qualification_impact: NOT_ELIGIBLE`, and are not passed through canonical scientific or performance semantics. The importer never rewrites a custom version to `1.0`.

## EngineCapability

VASP, Quantum ESPRESSO and CP2K use the strict `EngineCapability` contract to record:

- engine and executable identity;
- engine version and executable SHA-256;
- compiler, compiler version and build type;
- MPI implementation/version and OpenMP runtime;
- accelerator backend, GPU vendor and toolkit version;
- deterministic build fingerprint;
- version-probe observation, upstream-test status and execution authorization.

Repository templates intentionally contain `NOT_AVAILABLE` fields and validate as `EXTERNAL_HOLD`:

```bash
python ../../scripts/validate_engine_capabilities.py --json

python scripts/engine_capability.py \
  templates/vasp-engine-capability.yaml \
  --json
```

`IDENTITY_VERIFIED` means that the build identity is complete. It is not numerical or performance qualification. Missing engine access, license, build identity or authorization remains `EXTERNAL_HOLD`.

## Compute-campaign policy authority and migration

The compute-campaign configuration is a policy and participant-selection contract. It is independent of the benchmark-result evidence contract even though both canonical contracts currently use version `1.1`.

The authoritative closed Draft 2020-12 Schema is:

```text
templates/compute-qualification-campaign.schema.json
```

The repository-level `../../templates/compute-qualification-campaign.schema.json` is a byte-identical mirror. The historical configuration contract remains explicit at:

```text
templates/compute-qualification-campaign-v1.0.schema.json
```

Canonical campaign v1.1 replaces the implicit `reference_candidate_id` plus `candidate_ids` split with explicit participants:

```yaml
schema_version: "1.1"
participants:
  - candidate_id: CPU-FP64-REFERENCE
    role: scientific-reference
  - candidate_id: GPU-CANDIDATE
    role: acceleration-candidate
```

`compute_campaign_contract.py` is the only loader and migration authority. It rejects duplicate YAML or JSON keys before object construction, rejects non-finite constants and exponent overflow, validates a closed Schema with no defaults, then enforces semantic invariants that JSON Schema alone cannot express cleanly. These include globally unique candidate identities across roles, exactly one scientific reference, at least one acceleration candidate and non-whitespace identifiers.

A legal v1.0 campaign is accepted only by the central adapter. Migration performs one explicit operation: it converts `reference_candidate_id` and `candidate_ids` into typed participant records. It records `NO_EVIDENCE_PROMOTION`, `defaults_applied: []` and `evidence_fields_added: []`. It does not infer a solver, executable, license, run, hardware, scientific result or any other benchmark evidence, and therefore cannot remove an existing `EXTERNAL_HOLD`.

Unknown versions, mixed v1.0/v1.1 role fields, duplicate roles or identities, invalid repeat counts, invalid ratios, malformed or non-finite tolerances, type confusion and additional fields fail closed. There are no valid-contract defaults for repeat counts, ratios or tolerance values.

Both `CampaignConfig` and `CampaignDocument` recursively freeze nested mappings and sequences. Callers receive explicit detached copies for validation or downstream libraries, so mutation after validation cannot alter the policy or evidence being qualified.

## Reproducible CPU/accelerator qualification

`qualify_compute_campaign.py` no longer consumes `compute_qualification_view`. Every input now follows two independent central boundaries:

```text
campaign YAML/JSON
  -> compute_campaign_contract.load_campaign()
  -> closed Schema + semantic validation
  -> explicit v1.0-to-v1.1 policy migration when required
  -> immutable CampaignConfig

benchmark result JSON
  -> benchmark_contract.normalize_record()
  -> performance_evidence.validate_canonical_result()
  -> immutable CampaignDocument typed accessor
  -> identity, numerical and performance gates
```

The campaign therefore reads canonical nested v1.1 evidence fields directly. It does not flatten engine, software, hardware, execution, scientific, performance, artifact or provenance structures before qualification. Legacy flat benchmark-result v1.0 may still enter through its separate explicit central adapter, but its `imported-unverified` source, migration impact and irrecoverable missing fields keep the campaign on `EXTERNAL_HOLD`. Custom benchmark-result Schemas are rejected from this workflow.

The former projection lost or weakened material qualification evidence:

- canonical role was moved to a private auxiliary key and was not enforced by the campaign;
- engine executable, compiler/MPI/OpenMP identity and most accelerator-runtime identity were discarded;
- site, scheduler, job, filesystem, scratch, topology, GPU vendor/model/UUID/memory/driver/binding and artifact verification were discarded;
- model identity, convergence thresholds and declared observable identity were discarded;
- scientific properties were flattened and could collide with standard result names such as `energy_ev`;
- all non-real provenance kinds were collapsed to one local-parser label.

`compute_qualification_view` remains exported for one compatibility deprecation cycle because it is an existing module-level diagnostic API. It is explicitly **not qualification input**. The permanent validator proves that it still calls the central `normalize_record`, that the campaign source does not reference it, that custom or unknown inputs fail closed, and that its qualification impact is `NOT_ELIGIBLE`.

A canonical campaign can reach `QUALIFIED_FOR_REVIEW` only when all of the following are present:

- at least three contiguous repeats for the CPU reference and every acceleration candidate;
- an exact match between campaign role and canonical `role`;
- globally unique `execution.run_id` values;
- one stable campaign `site_id` and matching hardware/execution site identity;
- stable per-candidate engine version, executable, build fingerprint, compiler/MPI/OpenMP/runtime, hardware fingerprint, topology and GPU binding;
- stable multi-GPU UUID sets across repeats;
- one canonical scientific identity across all records, including engine version, input hash, method fingerprint, model identity, convergence thresholds and observable set;
- real-engine provenance with no missing fields;
- successful parsing and exit status;
- fully `VERIFIED` artifacts;
- property-specific numerical equivalence within declared absolute and relative tolerances;
- a finite median reference-over-candidate wall-time ratio that meets the declared threshold.

Before Schema validation, the campaign and evidence loaders reject non-standard `NaN`/`Infinity` constants and exponent overflow such as `1e999`. Non-finite thresholds, wall times, nested result arrays, convergence thresholds or scientific properties therefore cannot enter equivalence, median or performance-ratio calculations. Standard-result/property key collisions also fail closed instead of inheriting the lossy projection's overwrite behavior.

```bash
python ../../scripts/validate_compute_qualification.py --json

python scripts/qualify_compute_campaign.py \
  templates/compute-qualification-campaign.yaml \
  results/*.json \
  --workers 8 \
  --out qualification-report.json
```

Without real GPU, licensed solver, engine build, site/run/hardware identity, verified artifacts and accepted scientific result evidence, the workflow reports `EXTERNAL_HOLD` and does not calculate or publish a speedup. `QUALIFIED_FOR_REVIEW` is still not signed L3 evidence.

## Machine-readable contract evidence

The permanent quality gate writes `compute-contract-evidence.json` from the acceleration registry, benchmark contract, EngineCapability, compute-qualification validators and implemented software-acceleration architecture without invoking an external engine. Evidence Schema v1.5 records:

- canonical acceleration registry validation and runtime single-source status;
- nested v1.1 benchmark-result authority and root-mirror digest;
- native benchmark-result semantic version `1.1`;
- canonical compute-campaign v1.1 authority, Schema digest and synchronized root mirror;
- legal campaign v1.0 migration, no-default and no-evidence-creation guarantees;
- campaign and benchmark-result contract independence;
- immutable campaign policy and evidence accessors;
- unknown or mixed campaign input as `FAIL_CLOSED`;
- `compatibility_view_present: false` for the removed benchmark nested-v1.0 semantic downgrade view;
- `legacy_semantic_bypass: FAIL_CLOSED`;
- flat benchmark-result v1.0 migration impact as `EXTERNAL_HOLD`;
- compute campaign input model `canonical-nested-v1.1-typed-accessor`;
- mandatory central normalization and native semantic validation;
- diagnostic projection retained, not consumed, and `NOT_ELIGIBLE` for qualification;
- explicit role, run, site, build, hardware, multi-GPU, scientific and artifact invariants;
- profile-first Python control-plane doctrine;
- implemented reference/NumPy/cell-list neighbor-search contract and periodicity coverage;
- implemented shared read-only mmap Parser transport for four engines;
- native sidecar and CUDA-kernel state without fabricating implementation;
- VASP, Quantum ESPRESSO and CP2K template state;
- repository performance qualification as `NOT_ESTABLISHED`;
- compute campaign state as `EXTERNAL_HOLD`;
- the eight-worker hard bound;
- `external_engine_invoked: false` and `performance_ratio_published: false`.

```bash
python ../../scripts/capture_compute_contract_evidence.py \
  --out compute-contract-evidence.json \
  --json
```

The coverage stage must load this report and embeds it under `contract_evidence` in `coverage-report.json`. A missing, malformed, invalid, externally invoking or ratio-publishing report fails the quality gate. CI coverage artifacts therefore carry both test coverage and the current non-qualification boundary.

## Permanent gates

The root quality gate now runs, in order:

1. explicit legacy acceleration evidence contracts;
2. single-authority benchmark-result contract, native v1.1 semantics and migration validation;
3. canonical acceleration registry validation;
4. EngineCapability validation;
5. closed canonical compute-campaign contract, migration and immutable-access validation;
6. native canonical compute qualification and projection-isolation validation;
7. machine-readable compute contract and software-architecture evidence capture;
8. compute architecture audit;
9. lint, formatting, typing, evidence-bound coverage, security and repository tests.

The benchmark and compute-contract gates perform table-driven negative regression over canonical/legacy/custom evidence, canonical/legacy campaign policies, rare flat-field combinations, duplicate keys and identities, missing and contradictory provenance, role and version migration, site/run/build/hardware identity, multi-GPU UUID stability, artifact status, non-finite values, projection collision/equivalence boundaries and unknown or mixed shapes. The architecture evidence additionally fails closed if the doctrine, neighbor-search contract, inspector binding, shared mmap scanner or four-engine parser consumption drifts.

```bash
python ../../scripts/quality_gate.py
```

## v0.4 depth

See `SKILL.md`, `manifest.yaml`, `scripts/`, `templates/`, and `tests/` for the deterministic DFT adapters and scientific gates introduced in v0.4.0-alpha.1.
