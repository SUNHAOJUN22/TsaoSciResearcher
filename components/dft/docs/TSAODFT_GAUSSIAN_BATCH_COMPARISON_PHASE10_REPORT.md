# TsaoDFT Gaussian Batch Profile Comparison Phase 10 Report

**Program:** `TSAODFT_FULL_NUMERICAL_CORRECTNESS_PERFORMANCE_AND_REAL_ACCELERATION_V2`  
**Phase:** 10 — privacy-safe baseline/candidate comparison of Gaussian batch-profile reports  
**Starting HEAD:** `5b9f70f2273ad9d12099de15b965ad6974950ae1`  
**Validated implementation HEAD:** `e4394ddf86f6957e584495b8dedd84c14c888121`  
**Validated GitHub Actions run:** `30763453448`  
**External Gaussian execution:** `NO`  
**Representative real Gaussian logs supplied:** `NO`  
**Public capability boundary:** `L2_VALIDATED_ADAPTER`

## 1. Objective

Phase 9 can profile a reviewed set of local Gaussian logs and produce one anonymous aggregate report. That report is useful for identifying parser hotspots, but a manual comparison of two reports can still introduce several errors:

- comparing different input-log sets;
- comparing one isolated run with one process-parallel run;
- comparing reports produced with different repeat settings;
- accepting timing changes when normalized parser outputs changed;
- accepting timing changes across different environment fingerprints;
- treating a local parser ratio as Gaussian-engine, CPU, GPU or product acceleration;
- leaking source report paths or calculation identities into a comparison document.

Phase 10 adds a fail-closed comparison tool that separates four questions:

1. Were the same anonymous input contents compared?
2. Did normalized parser semantics remain identical?
3. Are the local timing observations methodologically comparable?
4. Which functions were added, removed, retained or moved in the hotspot ranking?

A timing classification is generated only when all comparison prerequisites pass. Otherwise the tool reports the reason and withholds timing conclusions.

## 2. Added executable

```text
scripts/compare_gaussian_batch_profiles.py
```

The executable accepts two Phase 9 batch-profile JSON reports:

```text
baseline report
candidate report
```

It emits one deterministic anonymous JSON comparison.

### Windows PowerShell

```powershell
python scripts/compare_gaussian_batch_profiles.py `
  "C:\profiles\baseline-batch-profile.json" `
  "C:\profiles\candidate-batch-profile.json" `
  --max-regression-percent 10 `
  --max-report-mib 64 `
  --out "C:\profiles\batch-comparison.json"
```

### Linux shell

```bash
python scripts/compare_gaussian_batch_profiles.py \
  /profiles/baseline-batch-profile.json \
  /profiles/candidate-batch-profile.json \
  --max-regression-percent 10 \
  --max-report-mib 64 \
  --out /profiles/batch-comparison.json
```

The output may also be written only to stdout by omitting `--out`.

## 3. Input-report trust boundary

The comparator does not trust either input JSON merely because it was named as a Phase 9 report. It validates:

- schema version;
- report scope;
- exact evidence-label set;
- explicit absence of external DFT execution;
- `NOT_EVALUATED` scientific acceptance;
- ineligible performance qualification;
- complete source-privacy declaration;
- worker and execution-mode consistency;
- exact positive repeat and size-limit values;
- non-empty record collection;
- valid SHA-256 identifiers;
- contiguous duplicate-content occurrence indexes;
- finite non-negative timing and memory values;
- valid parser-result status and scientific counts;
- contiguous hotspot ranks without duplicate functions;
- aggregate counts consistent with individual records;
- environment-fingerprint counts consistent with individual records.

The reports are read in bounded binary chunks. The comparator records their SHA-256 digests, enforces a configurable size limit, requires regular non-empty files, requires strict UTF-8 and JSON, and rejects a file that changes while it is being read.

Default maximum report size:

```text
64 MiB per report
```

## 4. Anonymous record identity

A record is matched by:

```text
(input_sha256, content_occurrence_index)
```

This identity preserves duplicate contents as separate requested observations without using:

- source log path;
- source log basename;
- report path;
- report basename;
- file-order position;
- process-completion order.

The comparator reports baseline-only and candidate-only identities when the anonymous input multisets differ.

## 5. Semantic-equivalence gate

For every matched record, the comparator checks:

```text
input_bytes
input_lines
utf8_replacement_character_count
status
normal_termination
error_termination
scf_energy_count
frequency_count
orientation_block_count
result_sha256
```

Timing is ineligible when any field differs.

This prevents a faster result from being accepted when the parser:

- changes job classification;
- loses or gains scientific values;
- changes termination interpretation;
- changes normalized output content;
- reads a different byte/line representation.

The comparison then reports:

```text
semantic_equivalent
semantic_difference_fields
records_with_differences
```

No attempt is made to reinterpret or repair a semantic mismatch.

## 6. Timing-comparability gate

Timing classification requires all of the following:

1. identical anonymous input-content multiset;
2. semantic equivalence for every matched record;
3. baseline mode `ISOLATED_SEQUENTIAL`;
4. candidate mode `ISOLATED_SEQUENTIAL`;
5. neither report marks timing contention;
6. identical parser repeat count;
7. identical taxonomy repeat count;
8. identical per-file maximum input limit;
9. identical environment fingerprint for every matched record;
10. positive parser median time on both sides.

The comparison policy explicitly declares:

```text
requires_identical_input_content_multiset = true
requires_semantic_equivalence = true
requires_isolated_sequential_mode = true
requires_identical_iteration_settings = true
requires_identical_environment_fingerprints = true
concurrent_batch_timing_eligible = false
```

Potential ineligibility reasons include:

```text
INPUT_SET_MISMATCH
SEMANTIC_MISMATCH
BASELINE_NOT_ISOLATED_SEQUENTIAL
CANDIDATE_NOT_ISOLATED_SEQUENTIAL
TIMING_CONTENTION_MARKED
ITERATION_SETTINGS_DIFFER
TAXONOMY_ITERATION_SETTINGS_DIFFER
MAX_INPUT_LIMIT_DIFFERS
ENVIRONMENT_FINGERPRINT_MISMATCH
NON_POSITIVE_PARSER_TIMING
```

## 7. Observation classification

When timing is comparable, the per-record observations are:

```text
observed_baseline_over_candidate_ratio
candidate_delta_percent
candidate_minus_baseline_peak_mib
classification
```

The default tolerance is:

```text
10 percent
```

Classification semantics:

```text
candidate_delta_percent > threshold  -> REGRESSION_OBSERVED
candidate_delta_percent < -threshold -> IMPROVEMENT_OBSERVED
otherwise                            -> WITHIN_TOLERANCE
```

The complete comparison status is selected in fail-closed priority order:

```text
INPUT_SET_MISMATCH
SEMANTIC_MISMATCH
TIMING_NOT_COMPARABLE
REGRESSION_OBSERVED
IMPROVEMENT_OBSERVED
WITHIN_TOLERANCE
```

If any comparable record has an observed regression beyond the threshold, the overall status is `REGRESSION_OBSERVED` even when another record improved.

The wording deliberately uses `OBSERVED`. It is not an engine, product, CPU or GPU speedup claim.

## 8. Hotspot migration analysis

The comparator rebuilds hotspot aggregates from validated individual records rather than trusting a precomputed aggregate list.

Functions are classified as:

```text
ADDED
REMOVED
PERSISTENT
```

For persistent functions it reports:

- baseline and candidate file prevalence;
- baseline and candidate median rank;
- candidate-minus-baseline median-rank change;
- timing observation only when the complete timing gate passes.

Hotspot comparisons remain useful even when timing is ineligible. For example, a semantic mismatch can still show that a function appeared or disappeared, but the comparator does not turn that observation into a performance conclusion.

## 9. Privacy contract

The comparison excludes:

- both source report paths;
- both source report basenames;
- source Gaussian log paths;
- source Gaussian log basenames;
- source Gaussian log contents;
- hostname;
- username;
- home directory;
- arbitrary environment variables.

It declares:

```text
source.kind = LOCAL_BATCH_PROFILE_REPORTS
source.origin_verified = false
report_paths_recorded = false
report_basenames_recorded = false
source_log_paths_recorded = false
source_log_contents_recorded = false
input_sha256_recorded = true
```

The comparison retains:

- input SHA-256 values;
- baseline report SHA-256;
- candidate report SHA-256;
- anonymous environment fingerprints.

These values support auditability but may still be sensitive identifiers. They remain subject to the user's data-governance policy.

## 10. Fail-closed publication

The comparator:

- refuses to replace either input report;
- writes output atomically;
- removes temporary output after a publication failure;
- preserves an existing output when validation fails;
- emits structured JSON failure on stderr;
- does not place report paths or basenames in the failure document.

No partial comparison is published.

## 11. Evidence labels

Every successful comparison is labelled:

```text
LOCAL_BATCH_PROFILE_COMPARISON
PARSER_ONLY_OBSERVATION
NOT_DFT_ENGINE_PERFORMANCE_EVIDENCE
NOT_GPU_PERFORMANCE_EVIDENCE
NOT_PRODUCT_PERFORMANCE_CLAIM
```

It also records:

```text
external_dft_engine_invoked = false
scientific_acceptance = NOT_EVALUATED
performance_qualification = NOT_ELIGIBLE_FOR_DFT_OR_GPU_ACCELERATION_CLAIMS
```

## 12. Direct tests

Phase 10 adds:

```text
tests/test_gaussian_batch_profile_comparison.py
tests/test_gaussian_batch_profile_comparison_edges.py
```

The 16 test methods cover:

- exact scalar and SHA-256 contracts;
- deterministic report hashing;
- bounded report reading;
- missing, empty, oversized, invalid UTF-8 and invalid JSON files;
- non-regular and read-time-mutating reports;
- strict report scope, evidence and privacy contracts;
- malformed records and hotspots;
- duplicate identities and non-contiguous occurrence indexes;
- aggregate/record mismatches;
- semantic mismatch suppression of timing conclusions;
- input-set mismatch reporting;
- concurrent-mode ineligibility;
- environment and repeat-setting mismatch ineligibility;
- non-positive timing ineligibility;
- improvement, regression and within-tolerance statuses;
- hotspot added, removed and persistent paths;
- atomic output success and failure;
- stdout-only execution;
- output/input collision refusal;
- successful and failed privacy redaction.

The permanent Python 3.12 log confirms all 16 methods passed.

## 13. Permanent quality-gate result

Validated implementation HEAD:

```text
e4394ddf86f6957e584495b8dedd84c14c888121
```

GitHub Actions run:

```text
30763453448
```

| Metric | Phase 9 final | Phase 10 validated implementation |
|---|---:|---:|
| Tests | 481 | **497** |
| Suites | 9 | **9** |
| Failed suites | 0 | **0** |
| Statement coverage | 94.23% | **94.36%** |
| Branch coverage | 83.71% | **84.21%** |

The implementation passed:

- Python 3.10;
- Python 3.12;
- Python 3.13;
- Ruff lint and format;
- mypy across 18 isolated targets;
- strict trust-boundary mypy across 4 targets;
- 497 tests across 9 suites;
- statement and branch coverage;
- Bandit;
- strict repository audit;
- CodeQL Python analysis;
- runtime, development and exact locked-environment dependency audits;
- CycloneDX SBOM generation.

The six tracked execution/trust cores remain unchanged:

| Core | Statement | Branch |
|---|---:|---:|
| `shell_contract.py` | 100% | 100% |
| `trust_boundary.py` | 100% | 100% |
| `engine_parser_contract.py` | 100% | 100% |
| `benchmark_bridge.py` | 100% | 100% |
| `generate_job_script.py` | 100% | 98.53% |
| `validate_hpc_manifest.py` | 100% | 99.29% |

No coverage exclusion, denominator change, test deletion or gate reduction was used.

## 14. Validated artifacts

Python 3.12 coverage artifact:

```text
ID: 8838202490
SHA-256: 50cf41aaa782911822055d3d9093938194e450df9a245183e7a4c3eff64f5999
```

Supply-chain artifact:

```text
ID: 8838188651
SHA-256: ae71ee71f37300aced9014d8a4e27fb06617e4821ede460fdabb35575bec4d37
```

## 15. Change scope

Compared with Phase 9 final HEAD, the validated implementation is a seven-commit fast-forward and changes only:

```text
scripts/compare_gaussian_batch_profiles.py
tests/test_gaussian_batch_profile_comparison.py
tests/test_gaussian_batch_profile_comparison_edges.py
```

No branch, pull request, force push or history rewrite was used.

## 16. Remaining evidence gap

Phase 10 validates comparison mechanics, not a real parser optimization result.

No representative real Gaussian log set or paired baseline/candidate reports were supplied. Therefore the repository does not currently contain a truthful measured value for:

- real Gaussian parser improvement;
- real Gaussian parser regression;
- batch throughput speedup;
- Gaussian electronic-structure engine acceleration;
- CPU acceleration;
- GPU acceleration;
- multi-GPU scaling;
- edge-device acceleration.

Current truthful state:

```text
GAUSSIAN_BATCH_PROFILE_COMPARATOR: IMPLEMENTED_VALIDATED
INPUT_MULTISET_EQUIVALENCE_GATE: IMPLEMENTED_VALIDATED
PARSER_SEMANTIC_EQUIVALENCE_GATE: IMPLEMENTED_VALIDATED
ISOLATED_TIMING_COMPARABILITY_GATE: IMPLEMENTED_VALIDATED
HOTSPOT_MIGRATION_ANALYSIS: IMPLEMENTED_VALIDATED
COMPARISON_PRIVACY_CONTRACT: IMPLEMENTED_VALIDATED
REPRESENTATIVE_REAL_GAUSSIAN_BATCH_COMPARISON: NOT_AVAILABLE
REAL_GAUSSIAN_ENGINE_BENCHMARK: NOT_AVAILABLE
REAL_GPU_BENCHMARK: NOT_AVAILABLE
PUBLIC_CAPABILITY_LEVEL: L2_VALIDATED_ADAPTER
```

## 17. Next scientific execution

The next evidence-producing step is not another blind code rewrite. It is:

1. Select a legally usable representative Gaussian log set.
2. Produce a Phase 9 baseline report using `--workers 1`.
3. Apply one controlled parser candidate change.
4. Produce a candidate report on the same machine with identical settings and `--workers 1`.
5. Run the Phase 10 comparator.
6. Accept timing observations only when input, semantic, environment and execution gates all pass.
7. Inspect hotspot movement before admitting any broader parser redesign or native extension.

Until that sequence exists, broader parser optimization remains `PROFILE_GATED` and all external-engine acceleration remains `REAL_EVIDENCE_REQUIRED`.
