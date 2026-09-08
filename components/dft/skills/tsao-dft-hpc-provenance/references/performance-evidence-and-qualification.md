# Real benchmark evidence and scoped L3 qualification

## Evidence state machine

```text
planned candidate
→ imported evidence
→ executable Schema and artifact validation
→ single-plan scientific/build/hardware isolation
→ parser-accepted successful repeats
→ numerical-equivalence gate
→ performance statistics
→ prequalification root SHA-256
→ Ed25519-signed independent review
→ atomic content-addressed evidence publication
→ scoped L3 performance eligibility
```

No transition is inferred from an earlier state. Scheduler success, a self-reported support level, an unsigned approval file or one fast run cannot bypass any gate.

## Input contract

`benchmark-result.schema.json` records plan/candidate/repeat identity, engine/build/runtime, CPU/GPU hardware, scheduler/site/filesystem, input and method hashes, convergence, Parser status, observables, performance metrics, artifacts and evidence source.

The Draft 2020-12 Schema is executed before semantic validation. JSON, YAML, JSONL and dotted-field CSV imports preserve successful and failed attempts. Duplicate plan/candidate/repeat/run identities are rejected.

A formal qualification accepts exactly one benchmark plan. Candidates cannot be silently aggregated across scientific identity, engine build, driver, GPU model, node/rank/thread topology or hardware fingerprint.

## Unified Parser contract

Gaussian, VASP, Quantum ESPRESSO and CP2K produce `engine-parser-result.schema.json` records containing termination, fatal state, electronic and geometry convergence, Parser acceptance reasons, energy/force/stress units, SCF count, elapsed time, warnings and failed stage.

Final or fatal engine state takes precedence over an earlier success marker. Scientific acceptance remains `pending`.

Deterministic bridge CLIs combine the Parser result with the HPC Manifest, method fingerprint, runtime provenance, scheduler metrics, GPU inventory and artifact hashes. Missing evidence is recorded in `missing_fields`; no placeholder is fabricated.

## Numerical-equivalence-first rule

Before any effective speedup is calculated, the candidate and CPU reference must share:

- benchmark plan and scientific identity;
- engine and engine version;
- input SHA-256 and method fingerprint;
- functional, basis/pseudopotential and correction policy;
- convergence thresholds and observable set;
- Parser acceptance and successful exit.

Energy, forces, stress and declared scalar properties must pass Policy tolerances. A failed numerical gate produces no effective speedup.

## Statistics

The default Policy requires three accepted repeats per candidate. Formal summaries use medians, not the fastest run, and include min/max, quartiles, IQR, MAD, modified-z outliers, failed runs, CPU-to-candidate and single-to-multi-GPU speedups, strong-scaling efficiency, GPU-hours, CPU-core-hours, memory, SCF iterations, I/O and optional energy-to-solution.

## Signed review contract

The review is a machine-readable Ed25519 attestation. Verification requires:

- reviewer identity and attestation ID;
- issue and expiry time;
- decision and `scoped-performance-evidence` scope;
- Policy ID, benchmark plan and candidate IDs;
- prequalification evidence-root SHA-256;
- public-key fingerprint and valid Ed25519 signature.

A plain `status: approved` or unsigned YAML file is not an approval.

## Atomic content-addressed bundle

Qualification first writes a temporary staging directory, verifies every document and atomically publishes:

```text
evidence-<root_sha256>/
  records.json
  benchmark-summary.json
  policy.json
  review-attestation.json
  qualification-report.json
  evidence-root.json
```

`evidence-root.json` records the digest and size of every formal file. The directory name is the SHA-256 of that root document. Missing, altered or extra files, digest/size mismatch, wrong directory identity, collision and partial publication fail closed.

`verify_evidence_bundle.py` independently verifies the published directory.

## Qualification states

Possible states include:

- `QUALIFIED_FOR_SCOPED_L3_PERFORMANCE_EVIDENCE`;
- `INSUFFICIENT_REPEATS`;
- `NUMERICAL_MISMATCH`;
- `BUILD_IDENTITY_MISSING`;
- `HARDWARE_IDENTITY_MISSING`;
- `PARSER_NOT_ACCEPTED`;
- `ARTIFACT_HASH_MISMATCH`;
- `REFERENCE_MISSING`;
- `PERFORMANCE_NOT_IMPROVED`;
- `PERFORMANCE_POLICY_FAILED`;
- `L2_ONLY`.

Scoped eligibility never modifies the public capability level. Public HPC L3 additionally requires explicit capability registration with generic execution evidence and the complete signed acceleration evidence contract.

## Optional metric adapters

`collect_optional_metrics.py` parses supplied summaries from Slurm `sacct`, GNU `time -v`, NVIDIA, ROCm, Intel GPU, Nsight and engine Parsers. It does not invoke those tools. Missing or invalid optional data returns `NOT_AVAILABLE`, never a fabricated zero.

## Commands

```bash
python skills/tsao-dft-hpc-provenance/scripts/validate_benchmark_result.py \
  results/*.yaml \
  --schema skills/tsao-dft-hpc-provenance/templates/benchmark-result.schema.json \
  --artifact-root run-artifacts

python skills/tsao-dft-hpc-provenance/scripts/import_benchmark_evidence.py \
  results/* \
  --schema skills/tsao-dft-hpc-provenance/templates/benchmark-result.schema.json \
  --artifact-root run-artifacts \
  --out build/evidence.jsonl

python skills/tsao-dft-hpc-provenance/scripts/qualify_performance_evidence.py \
  results/* \
  --result-schema skills/tsao-dft-hpc-provenance/templates/benchmark-result.schema.json \
  --policy skills/tsao-dft-hpc-provenance/templates/performance-qualification-policy.yaml \
  --policy-schema skills/tsao-dft-hpc-provenance/templates/performance-qualification-policy.schema.json \
  --artifact-root run-artifacts \
  --review signed-review-attestation.json \
  --review-public-key reviewer-ed25519-public.pem \
  --out-parent build/performance-evidence

python skills/tsao-dft-hpc-provenance/scripts/verify_evidence_bundle.py \
  build/performance-evidence/evidence-<root_sha256>
```

These commands process supplied evidence only. They do not submit jobs or execute a DFT engine.
