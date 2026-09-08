# TsaoDFT Gaussian Local-Log Profiling Phase 8 Report

**Program:** `TSAODFT_FULL_NUMERICAL_CORRECTNESS_PERFORMANCE_AND_REAL_ACCELERATION_V2`  
**Phase:** 8 — privacy-safe local Gaussian log profiling readiness  
**Starting HEAD:** `363dfb72b3c20b39c7db5d57d644deaf3b580163`  
**Validated implementation HEAD:** `d407643da7ea904a202f2b34ce0dd4edb4ec95eb`  
**Validated GitHub Actions run:** `30757856383`  
**External Gaussian execution:** `NO`  
**Representative real Gaussian log supplied:** `NO`  
**Public capability boundary:** `L2_VALIDATED_ADAPTER`

## 1. Objective

Phase 7 established a deterministic synthetic Gaussian-parser microprofile and resolved one measured repository hotspot. The remaining parser architecture could not be changed truthfully without representative real logs. Phase 8 therefore did not perform another speculative parser rewrite. It added a standalone local-file profiler so legally usable Gaussian logs can be measured immediately when they become available.

The tool profiles repository parsing behavior only. It does not run Gaussian, evaluate electronic-structure performance, submit scheduler jobs, execute GPU kernels, or qualify CPU/GPU acceleration.

## 2. Added executable

```text
scripts/profile_gaussian_log.py
```

The executable accepts one local Gaussian text log and produces a JSON report containing:

- streamed input SHA-256;
- input byte and line counts;
- UTF-8 replacement-character count;
- separate read/decode time;
- repeated parser wall-time observations;
- peak traced Python allocation;
- cProfile cumulative-function ranking;
- complete normalized parser-result SHA-256;
- status and selected count fields;
- same-process legacy/current error-taxonomy comparison;
- a minimal anonymized environment summary;
- explicit source, scientific and performance limitations.

## 3. Evidence and claim boundary

Every successful local report contains:

```text
LOCAL_INPUT_FILE
PARSER_ONLY_OBSERVATION
NOT_DFT_ENGINE_PERFORMANCE_EVIDENCE
NOT_GPU_PERFORMANCE_EVIDENCE
external_dft_engine_invoked = false
scientific_acceptance = NOT_EVALUATED
performance_qualification = NOT_ELIGIBLE_FOR_DFT_OR_GPU_ACCELERATION_CLAIMS
```

The tool does not infer that a local file was produced by a licensed Gaussian executable. It records:

```text
source.kind = LOCAL_FILE
source.origin_verified = false
```

A local parser observation therefore cannot be promoted automatically into:

- real Gaussian engine evidence;
- CPU or GPU acceleration evidence;
- scientific-equivalence acceptance;
- L3 capability evidence;
- a public product-performance claim.

## 4. Privacy contract

The generated report deliberately excludes:

- source path;
- source basename;
- source contents;
- hostname;
- username;
- home directory;
- arbitrary environment variables.

The report explicitly declares:

```text
source_path_recorded = false
source_basename_recorded = false
source_contents_recorded = false
input_sha256_recorded = true
```

The input SHA-256 is retained for auditability. It can still act as a sensitive identifier and must be handled according to the user's data policy.

The minimal environment section contains only:

- Python version;
- Python implementation;
- operating-system family;
- operating-system release;
- machine architecture;
- SHA-256 fingerprint of those fields.

## 5. File and failure safety

The reader enforces:

- regular-file input;
- non-empty input;
- configurable positive exact-integer size limit;
- chunked reading and hashing;
- no `Path.read_bytes()` whole-file helper;
- file size and modification-time consistency before and after reading;
- UTF-8 decoding with explicit replacement accounting;
- structured failure output without source identity;
- refusal to replace the input log with the output report;
- atomic JSON publication through the existing profile-core writer.

Default maximum input size:

```text
512 MiB
```

The source text is necessarily held in memory after bounded reading because the current validated Gaussian parser accepts a text string. Phase 8 does not mislabel this as a streaming parser architecture.

## 6. Usage

### Windows PowerShell

```powershell
python scripts/profile_gaussian_log.py `
  "C:\path\to\gaussian.log" `
  --iterations 3 `
  --taxonomy-iterations 5 `
  --max-input-mib 512 `
  --out "C:\path\to\gaussian-parser-profile.json"
```

### Linux shell

```bash
python scripts/profile_gaussian_log.py \
  /path/to/gaussian.log \
  --iterations 3 \
  --taxonomy-iterations 5 \
  --max-input-mib 512 \
  --out /path/to/gaussian-parser-profile.json
```

The output JSON can be shared for parser-profile analysis without sharing the source filename or contents. The input SHA-256 remains present and should be reviewed before external disclosure.

## 7. Direct contract tests

Phase 8 adds `tests/test_gaussian_local_log_profile.py` with direct checks for:

1. exact positive-integer CLI and API contracts;
2. profile-core import failure;
3. chunked file reading without `Path.read_bytes()`;
4. byte count, line count and SHA-256 correctness;
5. invalid UTF-8 replacement accounting;
6. empty-file rejection;
7. configured size-limit rejection;
8. non-regular-file rejection;
9. read-time file mutation detection;
10. deterministic parser-result hashing;
11. source path and basename non-disclosure;
12. minimal environment fields;
13. local-report non-qualification labels;
14. taxonomy A/B semantic equality;
15. parser iteration instability detection;
16. cProfile instability detection;
17. non-finite timing and memory rejection;
18. atomic report publication;
19. source/output path collision rejection;
20. missing-file failure without path disclosure.

## 8. Permanent quality-gate result

Validated implementation HEAD:

```text
d407643da7ea904a202f2b34ce0dd4edb4ec95eb
```

GitHub Actions run:

```text
30757856383
```

Result:

| Metric | Phase 7 final | Phase 8 validated implementation |
|---|---:|---:|
| Tests | 465 | **473** |
| Suites | 9 | **9** |
| Failed suites | 0 | **0** |
| Statement coverage | 94.17% | **94.21%** |
| Branch coverage | 83.69% | **83.71%** |

The validated implementation passed:

- Python 3.10;
- Python 3.12;
- Python 3.13;
- Ruff lint and format;
- mypy across 18 isolated targets;
- strict trust-boundary mypy across 4 targets;
- Bandit;
- strict repository audit;
- CodeQL Python analysis;
- runtime, development and exact locked-environment dependency audits;
- CycloneDX SBOM generation;
- all nine unit/integration suites.

Trust-core coverage remains:

| Core | Statement | Branch |
|---|---:|---:|
| `shell_contract.py` | 100% | 100% |
| `trust_boundary.py` | 100% | 100% |
| `engine_parser_contract.py` | 100% | 100% |
| `benchmark_bridge.py` | 100% | 100% |
| `generate_job_script.py` | 100% | 98.53% |
| `validate_hpc_manifest.py` | 100% | 99.29% |

Python 3.12 coverage artifact:

```text
artifact_id = 8836521705
sha256 = 6184268bcca832c8e172ad895dba48fbf1cc5d423291bbb47021793930bfedbf
```

Supply-chain artifact:

```text
artifact_id = 8836508854
sha256 = 8fbdb2620961fda94fef8dbb8fe0f1e031b694add6a393ede8d597ba5bc51976
```

## 9. What Phase 8 did not do

No representative user or production Gaussian log was available in the execution environment. Consequently, Phase 8 did not establish:

- the real distribution of Gaussian file sizes;
- the real share of orientation parsing, route parsing or repeated line splitting;
- parser performance on specific Gaussian revisions;
- real peak resident memory;
- real parser speedup against a pre-Phase-7 binary or deployment;
- any Gaussian electronic-structure engine speedup;
- any CPU/GPU accelerator benefit.

The new tool makes those measurements executable later; it does not fabricate them now.

## 10. Next evidence step

When legally usable representative logs are available, profile at least:

1. one successful minimum/frequency job;
2. one transition-state/frequency/IRC workflow;
3. one rich-property job with orbitals, excited states or NMR data;
4. one incomplete job;
5. one late error-termination job;
6. one small, one medium and one operationally large file.

For each file:

- retain the report JSON;
- preserve input SHA-256 privately;
- confirm normalized parser output with domain review;
- compare hotspot rankings across files;
- avoid architecture changes unless a path is materially dominant across representative logs;
- include read/decode and parser costs separately;
- keep parser evidence separate from Gaussian engine performance evidence.

## 11. Status

```text
GAUSSIAN_LOCAL_LOG_PROFILER: IMPLEMENTED_VALIDATED
LOCAL_FILE_SIZE_LIMIT: IMPLEMENTED
LOCAL_FILE_MUTATION_GUARD: IMPLEMENTED
SOURCE_PATH_DISCLOSURE: NO
SOURCE_BASENAME_DISCLOSURE: NO
SOURCE_CONTENT_DISCLOSURE: NO
INPUT_SHA256_RECORDED: YES
LOCAL_ENVIRONMENT_MINIMIZATION: PASS
ATOMIC_REPORT_PUBLICATION: PASS
STRUCTURED_FAILURE: PASS
REAL_GAUSSIAN_LOG_PROFILE_EXECUTED: NO
REAL_GAUSSIAN_ENGINE_BENCHMARK: NOT_AVAILABLE
REAL_GPU_BENCHMARK: NOT_AVAILABLE
TESTS: 473
STATEMENT_COVERAGE: 94.21%
BRANCH_COVERAGE: 83.71%
PUBLIC_CAPABILITY_LEVEL: L2_VALIDATED_ADAPTER
BRANCH_CREATED: NO
PULL_REQUEST_CREATED: NO
FORCE_PUSH: NO
HISTORY_REWRITE: NO
QUALITY_GATE_REDUCTION: NO
TEST_DELETION: NO
FABRICATED_PERFORMANCE_CLAIM: NO
```
