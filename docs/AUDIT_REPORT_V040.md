# TsaoSciResearcher v0.4.0 re-audit report

**Branch:** `agent/tsao-sci-researcher-v040-reaudit`  
**Verified baseline:** `main` commit `d4912dd80b85057d43b31d38b3e95a3a5d51fd38`  
**Last verified remote branch head before this update:** `489ff6d6295db4f0fd8babf02506aab216c5f887`  
**Status:** the changes described below are locally validated. PR CI, main CI, tag creation, Release publication, and downloaded Release-asset verification are separate gates and remain pending until evidenced.

## Baseline decision

The re-audit starts from the exact `main` commit above. Existing Draft PR #2 was not used as source because its patch used encoded/compressed source transport and workflows that reconstructed, deleted, and pushed source. The current work uses ordinary reviewable files and read-only validation workflows.

## Reproduced defects in the exact remote snapshot

- **TSR-015:** the structure validator matched its own literal placeholder signature and rejected itself.
- **TSR-016:** a capability test fixture used a category absent from the production catalog.
- **TSR-017:** an isolated test module failed with `ModuleNotFoundError: common`; prior tests could hide the error by mutating `sys.path`.
- **TSR-018–021:** repository-wide static gates, catalog I/O caching, mutation authenticity, and order/global-state validation were incomplete.

The machine-readable details and state transitions are in `docs/audit/defects-v0.4.0.json`.

## Locally verified test architecture

- **16** pytest modules and **109** collected tests.
- Every script module is imported in a fresh interpreter; no bare sibling alias may leak into `sys.modules`.
- Fifteen argparse CLIs are exercised directly with `--help` using `sys.executable`, explicit `cwd`, `shell=False`, a bounded timeout, and captured streams.
- An autouse fixture detects and restores leaks in `sys.path`, `os.environ`, the current directory, root logging handlers, and warning filters.
- The suite is exercised in normal, reverse, and seeded-random order; the recorded random seed is **20260717**.
- CI defines per-module isolated jobs and five consecutive complete-suite executions. The five local repetitions completed in 7.217–7.669 seconds each with 109/109 tests passing.
- The module-level inventory is recorded in `docs/audit/test-inventory-v0.4.0.json`.

## Locally verified quality and security gates

- Python compileall: pass for `scripts` and `tests`.
- Ruff format: pass across all scripts and tests.
- Ruff lint: pass across all scripts and tests.
- Mypy strict: pass across all **24** source modules.
- Bandit: no medium/high-severity findings in `scripts`.
- Mutation smoke: **15/15** named critical mutants killed after an isolated unmodified baseline first passed.
- Repository audit, structure validation, capability catalog validation, router self-test, figure contract validation, and deterministic release validation: pass in the local validation environment.

## Bounded local performance evidence

Measured on Linux with Python 3.13 in the available local validation environment:

| Workload | Measured seconds |
|---|---:|
| 10,000 route operations | 4.444373 |
| 100 capability catalog loads | 0.170459 |
| 1,000 JSONL records | 0.003045 |
| 1,000 Claim + 1,000 Evidence graph | 0.139078 |
| all 8 schemas | 0.047574 |
| 1,000 ZIP members | 0.008772 |
| install + uninstall | 0.192890 |
| two deterministic release builds | 0.132233 |

Peak `tracemalloc` evidence for the representative memory probe was **145,998 bytes**. Memory collection is separated from timing so instrumentation overhead does not manufacture a timing regression.

## Principal remediations

1. Deterministic bounded ZIP packaging and external SHA-256 sidecars.
2. Zip Slip, archive-link, collision, expanded-size, and compression-ratio defenses.
3. Managed atomic installer/uninstaller with target boundaries and rollback.
4. Collision-resistant project IDs and state/time/approval invariants.
5. Bidirectional Claim–Evidence graph validation.
6. Finite standard JSON and atomic state writes.
7. Unicode-aware deterministic routing with bounded input and cached rules.
8. Eight identified closed Draft 2020-12 schemas, including capability records.
9. Explicit package imports and fresh-process module/CLI isolation tests.
10. Catalog caching with copy-on-return isolation and bounded performance checks.
11. Fifteen baseline-authenticated critical mutations.
12. Full-repository Ruff and strict mypy gates, pinned Actions, read-only permissions, and a 3-OS × 4-Python matrix.

## Gate separation

| Gate | Status in this report |
|---|---|
| Local validation | locally-validated |
| PR CI | pending |
| main CI | not executed |
| Release assets | not executed |
| PR merge | not executed |
| tag / GitHub Release | not executed |

No statement in this report upgrades a local result to PR-CI, main-CI, or Release evidence.
