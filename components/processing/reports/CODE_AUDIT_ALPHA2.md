# TSAO source-core code audit — 0.1.0-alpha.2

## Scope

This audit covers the active GitHub source core, Python package and CLI, JSON Schemas, repository automation, project initialization/audit, deterministic archive code, specialist-skill entry points and GitHub configuration in Draft PR #1.

The separately qualified complete distribution and its historical specialist archives remain immutable external evidence. This report does not reinterpret their scientific or industrial Gate status.

## Defects found and corrected

### Gate and approval integrity

- Rejected noncanonical and duplicate Gate IDs.
- Made transitions transactional: an invalid target state no longer leaves a Gate marked `PASS`.
- Required accountable retirement and all-prior-Gate completion before downstream `PASS`.
- Added ordered G0–G18 Schema enforcement and project-audit validation.

### Evidence and model qualification

- Made malformed review dates and unknown contradiction states fail closed.
- Rejected superseded and retracted evidence for decisions.
- Restricted model risk and status values to the declared MR1–MR5 contract.
- Preserved independent review for MR4/MR5 qualification.

### Scientific kernels

- Added finite, numeric and sign validation to flow balances.
- Rejected empty, ragged and nonfinite stoichiometric matrices.
- Prevented substring route false positives such as `poetry` being classified as POE.

### Project and CLI behavior

- Rejected non-mapping YAML briefs, occupied output paths and symlinked template trees.
- Made template ingestion explicit rather than dependent on the caller's current directory.
- Expanded project audit to validate fields, subskills, Gate enums, Gate prerequisites and the technical-approval boundary.
- Added structured CLI failures and a ZIP-verification command.

### Archive and release security

- Rejected output archives inside the source tree.
- Rejected source symlinks, secret-like files, private-key suffixes and case-insensitive path collisions.
- Preserved empty directories deterministically.
- Added ZIP validation for traversal, backslashes, drive paths, symlinks, encrypted members, duplicate/case-colliding names, excessive ratios, member floods, CRC and total uncompressed size.

### CI and repository engineering

- Split the monolithic core into independently testable modules while retaining `tsao.core` compatibility.
- Replaced pipe-based timeout handling with temporary-file logging and process-group cleanup.
- Added Schema, CLI, archive, process-timeout and whole-repository contract tests.
- Corrected the GitHub Issue Form schema.
- Pinned GitHub Actions to immutable commit SHAs and bounded Python dependencies.
- Aligned `pyproject.toml`, package metadata, `manifest.yaml`, `CITATION.cff` and the changelog at alpha.2.

## Validation protocol

The Draft PR CI matrix independently performs, on Python 3.11 and 3.12:

1. editable installation with bounded dependencies;
2. dependency-integrity inspection;
3. Python compilation;
4. normal, boundary and adversarial pytest suites;
5. Ruff static checks;
6. wheel construction;
7. CLI smoke tests; and
8. a second integrated compile/test/lint run through `scripts/run_ci.py`.

The PR must remain Draft until both matrix jobs are green after the final source change.

## Approval boundary

A green software audit does not constitute catalyst, laboratory, process-simulation, equipment, relief, HAZOP/LOPA/SIL, legal FTO, customer, pilot, demonstration or industrial approval. Every such status remains `NOT_EVALUATED` until project-specific evidence, acceptance criteria and named qualified approval are attached.
