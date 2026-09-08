# TsaoDFT Gaussian Batch Profiling Phase 9 Report

**Program:** `TSAODFT_FULL_NUMERICAL_CORRECTNESS_PERFORMANCE_AND_REAL_ACCELERATION_V2`  
**Phase:** 9 — privacy-safe multi-log Gaussian parser profiling and aggregate hotspot analysis  
**Starting HEAD:** `c09cd0e2aab01afa516cd892a62513e6885bfb83`  
**Validated implementation HEAD:** `a9e6d12d58fe903c2d29460c63a0737f43179a35`  
**Validated GitHub Actions run:** `30760765290`  
**External Gaussian execution:** `NO`  
**Representative real Gaussian logs supplied:** `NO`  
**Public capability boundary:** `L2_VALIDATED_ADAPTER`

## 1. Objective

Phase 8 made privacy-safe profiling of one local Gaussian log executable. A single log, however, cannot establish whether a parser hotspot is stable across successful jobs, rich-property jobs, incomplete jobs, transition states, IRC workflows and late error terminations.

Phase 9 adds a standalone multi-log profiler that:

- invokes the validated local-log profiler independently for every input;
- preserves per-file parser-result and input hashes;
- aggregates parser status, file scale, timing, memory and hotspot observations;
- identifies duplicate file contents without recording their paths or basenames;
- supports deterministic sequential profiling by default;
- supports explicit cross-log process parallelism for throughput;
- marks concurrent timing as potentially affected by resource contention;
- fails the complete batch when any input cannot be profiled;
- does not run Gaussian, a scheduler, a DFT kernel or a GPU kernel.

The phase improves measurement scalability and evidence organization. It does not claim Gaussian-engine, CPU, GPU or scientific acceleration.

## 2. Added executable

```text
scripts/profile_gaussian_log_batch.py
```

The executable accepts one or more local Gaussian text logs and produces a single JSON report.

### Windows PowerShell

```powershell
python scripts/profile_gaussian_log_batch.py `
  "C:\logs\minimum.log" `
  "C:\logs\transition-state.log" `
  "C:\logs\late-error.log" `
  --iterations 3 `
  --taxonomy-iterations 5 `
  --max-input-mib 512 `
  --workers 1 `
  --out "C:\logs\gaussian-batch-profile.json"
```

### Linux shell

```bash
python scripts/profile_gaussian_log_batch.py \
  /logs/minimum.log \
  /logs/transition-state.log \
  /logs/late-error.log \
  --iterations 3 \
  --taxonomy-iterations 5 \
  --max-input-mib 512 \
  --workers 1 \
  --out /logs/gaussian-batch-profile.json
```

Default maximum batch size:

```text
256 input files
```

Default maximum input size:

```text
512 MiB per file
```

## 3. Execution modes

### 3.1 Isolated sequential mode

```text
--workers 1
execution.mode = ISOLATED_SEQUENTIAL
per_file_timing_contention_possible = false
```

This is the default and preferred mode when comparing per-file parser timing. Each local file is read and profiled after the prior input completes.

### 3.2 Concurrent batch-throughput mode

```text
--workers N, N > 1
execution.mode = CONCURRENT_BATCH_THROUGHPUT
per_file_timing_contention_possible = true
```

Separate processes profile different files concurrently. The implementation caps used workers at the number of supplied files and records both requested and used worker counts.

This mode can reduce batch completion time on suitable systems, but individual parser timing and memory observations may be affected by shared CPU, storage, cache and memory contention. The report therefore does not present concurrent per-file timing as directly interchangeable with isolated sequential timing.

No numeric parallel speedup threshold is embedded in CI. Timing is an observation, not a quality-gate pass condition.

## 4. Privacy and identity contract

The batch report excludes:

- every source path;
- every source basename;
- every source file content;
- hostname;
- username;
- user home directory;
- arbitrary environment variables.

The report declares:

```text
source.kind = LOCAL_FILES
source.origin_verified = false
source_paths_recorded = false
source_basenames_recorded = false
source_contents_recorded = false
input_sha256_recorded = true
```

Failures identify an input only by its one-based ordinal. Error messages are sanitized against:

- the original path string;
- the basename;
- the resolved absolute path when resolution succeeds.

Input SHA-256 values remain in the report for auditability and duplicate detection. They may still be sensitive identifiers and must be handled according to the data policy of the user or organization.

## 5. Batch report structure

Every successful report contains:

```text
LOCAL_INPUT_FILES
BATCH_PARSER_PROFILE
NOT_DFT_ENGINE_PERFORMANCE_EVIDENCE
NOT_GPU_PERFORMANCE_EVIDENCE
external_dft_engine_invoked = false
scientific_acceptance = NOT_EVALUATED
performance_qualification = NOT_ELIGIBLE_FOR_DFT_OR_GPU_ACCELERATION_CLAIMS
```

### 5.1 Aggregate fields

The report aggregates:

- input count;
- unique-content count;
- duplicate-content count;
- parser-status counts;
- normal-termination count;
- error-termination count;
- minimum, median, maximum and sum of file bytes;
- minimum, median, maximum and sum of line counts;
- read/decode timing summary;
- parser median-timing summary;
- parser traced-allocation summary;
- taxonomy legacy/current ratio summary where available;
- anonymized environment-fingerprint counts;
- cross-file hotspot summary.

### 5.2 Cross-file hotspot summary

Each hotspot entry contains:

- function identity from the existing cProfile summary;
- number of files in which the function appeared;
- median rank;
- median cumulative time;
- total cumulative time across observations;
- total call count.

Hotspots are sorted by:

1. number of files in which the function appears;
2. total cumulative time;
3. stable function-name ordering.

The summary is limited to the first 25 aggregated functions. Each individual record retains the first eight functions from its local profile.

### 5.3 Deterministic record ordering

Records are sorted by:

```text
(input_sha256, parser_result_sha256)
```

The result is independent of input path names and process-completion order.

Duplicate contents are not discarded. They are assigned a `content_occurrence_index` and retained as independent observations. This makes duplicate data visible without silently changing the requested workload.

## 6. Fail-closed contracts

The implementation rejects:

- an empty input list;
- a batch larger than `--max-files`;
- the same normalized input path supplied more than once;
- non-positive or lossy worker, iteration, taxonomy-iteration and limit values;
- malformed child-profile schemas;
- malformed or missing child-profile mappings;
- malformed input, result or environment hashes;
- malformed hotspot records;
- non-finite or negative timing and memory values;
- non-equivalent taxonomy comparisons;
- an output path that resolves to any input path;
- a partial batch in which one or more files fail.

The tool does not publish a partial success report. A failed batch returns structured JSON on stderr and preserves an existing output file.

## 7. Direct contract tests

Phase 9 adds:

```text
tests/test_gaussian_log_batch_profile.py
```

The eight test methods cover:

1. exact integer contracts and module-import failure;
2. sequential aggregation, duplicate-content detection, deterministic hashes and source redaction;
3. explicit worker capping and concurrent-mode contention labelling;
4. worker and batch failure redaction;
5. empty, over-limit and duplicate-path rejection;
6. malformed schema, non-finite timing and taxonomy mismatch rejection;
7. successful atomic private report publication;
8. failed-batch non-publication and source/output collision protection.

The permanent Python 3.12 log confirms that all eight methods passed.

## 8. Permanent quality-gate result

Validated implementation HEAD:

```text
a9e6d12d58fe903c2d29460c63a0737f43179a35
```

GitHub Actions run:

```text
30760765290
```

Result:

| Metric | Phase 8 final | Phase 9 validated implementation |
|---|---:|---:|
| Tests | 473 | **481** |
| Suites | 9 | **9** |
| Failed suites | 0 | **0** |
| Statement coverage | 94.21% | **94.23%** |
| Branch coverage | 83.71% | **83.71%** |

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
- all nine unit and integration suites.

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
artifact_id = 8837387908
sha256 = f038400710151737e0c6c3e706b2b0d28e33c43da6c0c73f4a48844fd1394dba
```

Supply-chain artifact:

```text
artifact_id = 8837373882
sha256 = 2ac2e0137ada19da010814aa49b1051a7edd2e2e60fcc9c6964133eb4247d97b
```

## 9. Evidence boundary

No representative user or production Gaussian logs were supplied during Phase 9. The permanent tests use deterministic local fixtures generated by the existing synthetic-log builder.

Consequently, Phase 9 does not establish:

- the real distribution of Gaussian log sizes;
- real cross-revision parser behavior;
- real cross-job hotspot stability;
- production storage throughput;
- production batch-throughput speedup;
- production parser resident memory;
- Gaussian electronic-structure acceleration;
- CPU/GPU DFT acceleration;
- scientific equivalence of different engine builds.

The batch tool makes a representative cross-log study executable later; it does not fabricate that study now.

## 10. Next evidence step

Run the batch profiler in `ISOLATED_SEQUENTIAL` mode on a legally usable set containing at least:

1. a successful minimum and frequency calculation;
2. a transition-state and frequency calculation;
3. a forward/reverse IRC workflow;
4. a rich-property calculation containing orbitals, NMR or excited states;
5. an incomplete calculation;
6. a late error-termination calculation;
7. small, medium and operationally large logs.

After obtaining that batch report:

- compare hotspot `files_present` and median rank;
- inspect whether orientation parsing, repeated line splitting or other blocks dominate across categories;
- verify result hashes against the current parser;
- preserve late-error-wins behavior;
- create a native or state-machine candidate only when the cross-log profile demonstrates a material end-to-end hotspot;
- include conversion, I/O and process-launch overhead in any candidate benchmark.

## 11. Status

```text
GAUSSIAN_SINGLE_LOCAL_LOG_PROFILER: IMPLEMENTED_VALIDATED
GAUSSIAN_MULTI_LOG_BATCH_PROFILER: IMPLEMENTED_VALIDATED
SEQUENTIAL_PER_FILE_PROFILE_MODE: IMPLEMENTED_VALIDATED
PROCESS_PARALLEL_BATCH_MODE: IMPLEMENTED_VALIDATED
CONCURRENT_TIMING_CONTENTION_LABEL: ENFORCED
DUPLICATE_CONTENT_DETECTION: IMPLEMENTED_VALIDATED
CROSS_LOG_HOTSPOT_AGGREGATION: IMPLEMENTED_VALIDATED
SOURCE_PATH_DISCLOSURE: BLOCKED_BY_CONTRACT
SOURCE_BASENAME_DISCLOSURE: BLOCKED_BY_CONTRACT
PARTIAL_BATCH_PUBLICATION: BLOCKED
REPRESENTATIVE_REAL_GAUSSIAN_BATCH_PROFILE: NOT_AVAILABLE
REAL_GAUSSIAN_ENGINE_BENCHMARK: NOT_AVAILABLE
REAL_GPU_BENCHMARK: NOT_AVAILABLE
VALIDATED_IMPLEMENTATION_CI: PASS
TESTS: 481
STATEMENT_COVERAGE: 94.23%
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
