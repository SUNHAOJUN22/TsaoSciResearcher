# TsaoDFT Phase 2 Final Code Audit Report

**Protocol:** `Phase 2 Final Code Audit & Full Repair Protocol`  
**Audit baseline:** `3d8e0e9960ab45ca1e7e9b266363cab5148bc457`  
**Audited implementation HEAD:** `0150e4a5201615003a51c12950473ae287b07f18`  
**Permanent CI run:** `30693638348`  
**Evidence boundary:** `NOT_PERFORMANCE_EVIDENCE`

## 1. Audit summary

The Phase 2 hardware-aware optimization control plane was reviewed across production code, templates, JSON Schema, CLI behavior, tests, scientific-claim boundaries, security gates and permanent CI. The review covered:

- `hardware_aware_optimizer.py`
- `hardware_optimization_contract.py`
- `hardware_provider_policy.py`
- hardware optimization and edge-inference templates
- output-plan JSON Schema
- existing and new fail-closed tests
- repository-wide lint, format, typing, coverage, security and supply-chain gates

No native C++, CUDA, HIP or SYCL implementation was added. No real hardware, engine, numerical-equivalence or speedup claim is established by this audit.

## 2. Issues found and repaired

### P2-AUD-001 — High

**File:** `skills/tsao-dft-hpc-provenance/scripts/hardware_optimization_contract.py`  
**Problem:** Direct Python API calls with a non-mapping profile root could raise an exception before producing a structured failure.  
**Root cause:** Root-type validation existed at the CLI boundary but not inside the reusable validation contract.  
**Fix:** `validate_profile()` now accepts untrusted input and returns `profile root must be a mapping` without dereferencing invalid roots.  
**Why safe:** Valid mapping inputs retain the existing normalized output and planner API.

### P2-AUD-002 — High

**File:** `skills/tsao-dft-hpc-provenance/scripts/hardware_optimization_contract.py`  
**Problem:** Enum-like fields and `schema_version` were normalized with `str(...)`; mappings, lists, booleans and numeric `1.0` could be silently converted to strings before rejection or, for the schema version, accidentally accepted.  
**Root cause:** Convenience coercion was used where strict untrusted-input typing was required.  
**Fix:** Added strict string and choice validators for schema version, engine, stage, target, vendor, backend, provider, precision, expected kernel, edge runtime, evidence source kind and model family.  
**Why safe:** Existing valid case-insensitive strings remain accepted; lossy coercion is rejected fail-closed.

### P2-AUD-003 — Medium

**File:** `skills/tsao-dft-hpc-provenance/scripts/hardware_aware_optimizer.py`  
**Problem:** The output Schema was used without first validating that it was itself a valid Draft 2020-12 Schema. Unicode decoding and schema-construction failures were not returned through the structured CLI failure path. Error sorting also relied on raw path-token comparison.  
**Root cause:** Instance validation was implemented without a meta-schema gate and with a narrower exception boundary.  
**Fix:** Added `Draft202012Validator.check_schema`, explicit `SchemaError` and `UnicodeError` handling, and deterministic string-token path sorting.  
**Why safe:** The valid shipped Schema and successful output format are unchanged; malformed schemas now fail closed.

### P2-AUD-004 — Medium

**File:** `skills/tsao-dft-hpc-provenance/scripts/hardware_provider_policy.py`  
**Problem:** A non-string CP2K workload `model` value was converted to text. A mapping containing words such as `linear` could influence sparse-route classification.  
**Root cause:** Workload metadata was treated as display text rather than typed decision input.  
**Fix:** CP2K model matching is now performed only for actual strings.  
**Why safe:** Valid string model names retain the same behavior; malformed metadata can no longer trigger a computational route.

### P2-AUD-005 — Medium

**File:** `skills/tsao-dft-hpc-provenance/scripts/hardware_optimization_contract.py`  
**Problem:** The first repair candidate introduced a `KeyError` for an unknown backend and changed the established `source_kind` error contract.  
**Root cause:** Compatibility checks indexed the backend map before confirming membership, and a generic enum message replaced a domain-specific message.  
**Fix:** Backend/vendor compatibility now checks map membership first; the established `evidence.source_kind must be simulation or observed` contract is preserved.  
**Why safe:** The correction restores previous fail-closed behavior and existing test compatibility rather than weakening tests.

## 3. Reviewed candidates that were not defects

- Import ordering was already the repository's Ruff-approved standalone-script ordering; it was not changed.
- Set-based recommendation assembly already emits sorted deterministic output; no change was required.
- No new `availability_evidence` field was added because that would change the output API and Schema. Existing `SIMULATED_AVAILABLE`, `source_kind` and non-claim fields already preserve the evidence boundary.

## 4. Modified files

- `skills/tsao-dft-hpc-provenance/scripts/hardware_aware_optimizer.py`
- `skills/tsao-dft-hpc-provenance/scripts/hardware_optimization_contract.py`
- `skills/tsao-dft-hpc-provenance/scripts/hardware_provider_policy.py`
- `skills/tsao-dft-hpc-provenance/tests/test_hardware_aware_optimizer_final_audit.py`

## 5. Test and coverage results

Permanent CI for the audited implementation completed with:

- suites: 9
- tests: 391
- failed suites: 0
- statement coverage: 93.51%
- branch coverage: 82.51%

This exceeds the required Phase 1 floor of 93.08% statement and 81.73% branch coverage.

Trust-core coverage remained:

| File | Statement | Branch |
|---|---:|---:|
| `shell_contract.py` | 100% | 100% |
| `trust_boundary.py` | 100% | 100% |
| `engine_parser_contract.py` | 100% | 100% |
| `benchmark_bridge.py` | 100% | 100% |
| `generate_job_script.py` | 100% | 98.53% |
| `validate_hpc_manifest.py` | 100% | 99.29% |

## 6. Security and supply-chain result

The same implementation HEAD passed:

- Python 3.10, 3.12 and 3.13 quality gates
- Ruff lint and format
- all 18 mypy targets
- all 4 strict trust-boundary mypy targets
- Bandit production audit
- strict repository audit
- secret and ignore-marker audits
- CodeQL Python analysis
- runtime, development and exact-lock dependency audits
- CycloneDX SBOM generation

## 7. Scientific and performance boundary

All simulation fixtures remain explicitly labeled:

```text
SIMULATION_ONLY
NOT_REAL_HARDWARE
NOT_PERFORMANCE_EVIDENCE
```

The optimizer continues to state that provider eligibility is planning evidence only. It does not establish installed-library use, real engine acceleration, numerical equivalence, speedup, scientific acceptance or an L3 capability upgrade.

## 8. Repository operation confirmation

- new branch: no
- pull request: no
- force push: no
- history rewrite: no
- validator weakening: no
- test deletion or exclusion: no
- coverage-threshold reduction: no

## 9. Final decision

`ALL_CHECKS_PASS`

`PHASE_2_FINAL_RELEASE_READY`
