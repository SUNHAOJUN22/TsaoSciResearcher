# Changelog

All notable changes are documented here.

## [Unreleased] — Behavioral benchmark

### Added

- Added `open-deep-mind/evals/` as a separate evaluation layer; it evaluates Φ/P/TRIZ behavior but is not a fourth reasoning module.
- Added an initial **60-case** benchmark covering routing, First Philosophy, First Principles, Dual Engine, explicit TRIZ, and TRIZ near-miss/anti-trigger behavior.
- Added fixed benchmark splits: **36 train / 12 validation / 12 holdout**.
- Added four reproducible configurations:
  - no skill;
  - commit-pinned `awesome-skills/first-principles-skill`;
  - production `opendeepmind_full` with explicit-only TRIZ;
  - `opendeepmind_no_triz_ablation` on the same explicit-TRIZ cases to measure TRIZ module contribution.
- Added three declared paired comparisons: full vs no skill, full vs pinned first-principles baseline, and full vs no-TRIZ ablation on `triz-positive` cases.
- Added schemas for eval definitions, run records, grading artifacts, and aggregated benchmark output.
- Added a semantic/blind-pairwise grading rubric and explicit red-blocker policy.
- Added dependency-free scripts for benchmark-definition validation, workspace creation, and result aggregation.
- Workspace manifests now enumerate every expected run slot; missing run/grading artifacts block `publication_ready`.
- Added OpenDeepMind-specific metrics including TRIZ false-activation rate, module-leakage rate, routing accuracy, rival-model coverage, falsifier coverage, tokens, and duration.
- Added paired common-case/repetition deltas for quality, tokens, and duration.
- Added regression coverage proving an empty validation workspace has 114 expected slots and cannot be publication-ready.
- CI now validates the authored benchmark definitions on every push/pull request.

### Publication status

- **No benchmark score is published yet.** The framework and cases are committed, but a benchmark-result release will not be declared until real model runs, raw artifacts, graders, and reproducible aggregate results exist.

## [1.2.0] — 2026-08-10

### Architecture

- Refactored OpenDeepMind into three physically isolated canonical modules:
  - `open-deep-mind/first-philosophy/`
  - `open-deep-mind/first-principles/`
  - `open-deep-mind/triz/`
- Added `open-deep-mind/ARCHITECTURE.md`, `open-deep-mind/MODULES.json`, and root `VERSION`.
- Converted root `FIRST_PHILOSOPHY.md`, `FIRST_PRINCIPLES.md`, and `TRIZ_ENGINEERING.md` into thin compatibility aliases.
- Rewrote `SKILL.md` as a progressive-disclosure router rather than a duplicate method body.

### First Philosophy

- Added canonical `first-philosophy/METHOD.md`, module manifest, README, Foundation Charter schema, valid fixture, and isolated validator.
- Enforced **Φ8 = Φ0..Φ7** and prohibited TRIZ dependency from the First Philosophy method body.

### First Principles

- Added canonical `first-principles/METHOD.md`, module manifest, README, model-contract and decision-record schemas, fixtures, and isolated validator.
- Corrected the historical protocol-numbering inconsistency: **P9 now means exactly P1..P9**. Former derivation and falsification passes are combined into P8A/P8B under the ninth-stage contract.
- Enforced no embedded/automatic TRIZ procedure in the canonical First-Principles method body.

### TRIZ

- Added canonical `triz/ROUTER.md` and `triz/module.json`; **T10 now means exactly T1..T10**.
- Preserved explicit-only activation and mandatory return to First-Principles validation.
- Added deterministic Standard Inventive Solution lookup.
- Added `matrix_anomalies.json` and normalized documented matrix-transcription duplicate IDs at lookup time while preserving raw vendored data for provenance.
- Hardened TRIZ validation for activation, protocol numbering, matrix structure/anchors/anomalies, 39 parameters, 40 principles, 76 SIS class distribution, ARIZ parts, deterministic tools, and subsystem map.

### Validation and maintenance

- Upgraded repository validation from file/syntax checks to architecture/version/module/alias/link checks and execution of all module validators.
- Added HTML `src`/`href` local-link checking in addition to Markdown links.
- Made SVG asset counting recursive.
- Upgraded the proposition-ledger validator with forward-reference handling, ID collision checks, and dependency-cycle detection.
- Added cross-module `unittest` regression coverage, including matrix anchors, known matrix anomaly normalization, SIS lookup, and cyclic-ledger rejection.
- Expanded CI to run all module validators, repository/ledger validation, deterministic lookups, tests, and Python compilation.
- Updated README files, AGENTS, CONTRIBUTING, CITATION, version/provenance documentation, and licensing boundaries.
- Removed TRIZ from all default domain routes; canonical TRIZ is now reachable only through the explicit engineering route.

## [1.1.0] — 2026-08-09

### Added

- Separate optional TRIZ engineering-invention module with explicit activation gate.
- Modern TRIZ problem-identification layer: function analysis, flow analysis, CECA, trimming, feature transfer, innovative benchmarking, multi-screen analysis, and key-problem routing.
- Complete classical contradiction layer: 39 engineering parameters, 40 inventive principles, full 39×39 contradiction-matrix transcription, engineering/physical contradiction modeling, and separation principles.
- Su-Field modeling and 76-item Standard Inventive Solutions index using the public MATRIZ five-class numbering.
- ARIZ-85C operational map, ideality/IFR/resources, FOS/effects, S-curve/TESE, concept substantiation, worked examples, deterministic matrix lookup, and TRIZ integrity validation.
- TRIZ source/provenance map and vendored MIT license notice.

### Changed

- Integrated TRIZ as opt-in and returned generated concepts to First-Principles/evidence/safety validation.
- Updated repository validator, GitHub Actions, README, notices, and citation metadata for TRIZ support.

## [1.0.0] — 2026-08-08

### Added

- Agent Skills-compatible `open-deep-mind/SKILL.md`.
- First Philosophy and First Principles engines.
- Foundation Charter and Φ8 foundation-qualification protocol.
- D/O/L/C/A/E/V/U proposition ledger and JSON schema.
- First-principles decomposition, model, falsification, and decision protocol.
- Cross-domain routing for science, engineering, modeling, strategy, policy, personal decisions, and creative/product innovation.
- More than thirty executable method cards.
- Red-blocker gate and twelve-dimension 100-point quality rubric.
- Scale-bridge and uncertainty audit.
- Failure-mode catalog, worked examples, output templates, validators, CI, bilingual README files, visual diagrams, licensing and maintenance documentation.
