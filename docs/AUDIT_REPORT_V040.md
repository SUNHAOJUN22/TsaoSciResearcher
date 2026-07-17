# TsaoSciResearcher v0.4.0 re-audit report

**Branch:** `agent/tsao-sci-researcher-v040-reaudit`  
**Verified baseline:** `main` commit `d4912dd80b85057d43b31d38b3e95a3a5d51fd38`  
**Status:** implementation and local validation completed for the registered defects; remote PR, CI, main, tag and Release status are separate gates and are not implied here.

## Baseline decision

The re-audit starts from the exact `main` commit above. Existing Draft PR #2 was not used as source because its current patch contains encoded/compressed source transport and workflows that reconstruct, delete and push source from GitHub Actions. That is incompatible with transparent source commits and least-privilege CI.

## Verified local gates

- Python compileall: pass for changed scripts and tests.
- Pytest: 53 tests pass, including adversarial and Hypothesis property tests.
- Ruff format/lint: pass for changed security, state and release modules and their tests.
- Mypy strict: pass for ten core modules.
- Bandit: no medium/high-severity findings in scripts.
- Mutation smoke: 3/3 critical mutants killed.
- Performance smoke: 10,000 routes and 1,000 JSONL records within regression thresholds.
- Deterministic package: two builds are byte-identical; sidecars verify; bounded safe extraction passes.

## Principal remediations

1. Deterministic bounded ZIP packaging and external SHA-256 sidecars.
2. Zip Slip, archive symlink, duplicate path and compression-bomb defenses.
3. Managed atomic installer/uninstaller with target boundaries and rollback.
4. Collision-resistant project IDs and state/time/approval invariants.
5. Bidirectional Claim–Evidence graph validation.
6. Finite standard JSON and atomic state writes.
7. Unicode-aware deterministic routing with bounded input and cached rules.
8. Eight identified Draft 2020-12 schemas, including capability records.
9. Property, adversarial, mutation, performance and cross-platform CI gates.
10. Pinned GitHub Actions with read-only permissions.

See `docs/audit/defects-v0.4.0.json` for the machine-readable ledger.
