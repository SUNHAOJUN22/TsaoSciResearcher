# Changelog

## 0.1.0-alpha.15 — 2026-08-02

- Added an opt-in adaptive Dormand–Prince 5(4) integration layer above the locked Phase A3 RHS.
- Added strict request/result schemas, identifier linkage, non-negative-state rejection, finite-value, time-monotonic, step-control and applicability Gates.
- Added convergence, restart-parity, analytic single-channel, external-flow and trajectory-conservation tests with 97% branch coverage for the new integrator.
- Fixed deterministic source snapshots so overlay-only files, including the Phase A3 executable layer, are included and hashed.
- Promoted Windows 3.11–3.14 to the core CI matrix and removed macOS from the release Gate.
- Hardened EPDM scalar Arrhenius, rate, moment and semibatch paths to fail closed on non-finite derived values; small scalar exposures use `expm1` for batch parity.
- Kept parameter calibration and all scientific, engineering, HSE, customer and industrial approvals `NOT_EVALUATED`.

## 0.1.0-alpha.14 — 2026-08-02

- Added strict reaction-channel rate-law and parameter-set binding for every A2 channel.
- Added SI-unit and Arrhenius parameter contracts with provenance, uncertainty, identifiability and applicability-domain states.
- Implemented the calculated-reference EPDM structural RHS, live/dead/TDB moment-source terms and explicit external flows.
- Added named conservation ledgers, zero/single/multi-channel hand calculations and short reference integration smoke tests.
- Preserved the frozen V1 public API and kept scientific, engineering, HSE, customer and industrial approval `NOT_EVALUATED`.

## 0.1.0-alpha.13 — 2026-08-02

- Corrected EPDM heterogeneous-site chain moments to use one consistent weighted rate set.
- Replaced artificial finite chain lengths with fail-closed HOLD records when no finite steady chain length exists.
- Corrected POE hot-start material balance to use incremental polymer production.
- Replaced unbounded full-factorial materialization with bounded index sampling for large DoE spaces.
- Kept all scientific, engineering, HSE, customer, and industrial approvals `NOT_EVALUATED`.

## 0.1.0-alpha.12 — 2026-08-02

- Closed cross-component balance cancellation and process-package component-substitution false PASS paths.
- Added stream/equipment topology checks, explicit reaction-basis controls, strict JSON output, and stable reason codes.
- Split initialization, project, transition, and release audits while preserving the legacy fail-closed audit default.
- Added append-only Gate event integrity, safe manifest paths, and an incremental source-overlay verification mechanism.
- Kept scientific, engineering, HSE, customer, and industrial approvals `NOT_EVALUATED`.

## Unreleased — EPDM scientific-kernel phases

- Closed Phase A0 evidence governance with qualified-status and applicability Gates, explicit internal-error signaling, strict case schemas, and a machine-visible HOLD for the V1 fixed-concentration semibatch assumption.
- Completed Phase A1 software contracts: frozen enumerations, strict Draft 2020-12 schemas, SI/evidence validation, layered qualification, semantic cross-reference checks, and metadata-only V1-to-V2 migration.
- Implemented the Phase A2 structural kernel: deterministic generated-state layouts, terminal×incoming propagation topology, activation/initiation/transfer/inhibition/deactivation/TDB channels, a structural stoichiometric matrix, and active-site inventory conservation audits.
- Strengthened Wheel contracts so A2 code, schemas, catalogs, fixtures, and installed-runtime structural smoke tests cannot be omitted silently.
- Kept V2 rate evaluation, numerical RHS/integration, calibration, thermodynamics, GPC/moment prediction, reactor dynamics, and all scientific/engineering/HSE/customer/industrial approvals explicitly unimplemented or `NOT_EVALUATED`.

## 0.1.0-alpha.11 — 2026-07-27

- Added NumPy-broadcast EPDM screening for temperature, residence-time, active-site and propagation-multiplier scenario grids.
- Added a once-validated full-history EPDM semibatch trajectory and a POE terminal-only RK4 execution path.
- Replaced POE RK4 inner-loop dataclass dispatch with a fixed-state numerical kernel while preserving public result identity.
- Expanded performance evidence to 20 workloads with warm-ups, medians, variability, cProfile hotspots, peak traced memory and scale checks.
- Added exact, analytical-tolerance and semantic parity contracts instead of applying an invalid cross-version digest rule to every workload.
- Added primary-source technology review and an explicit non-adoption record for SciPy, Numba, JAX and process parallelism.
- Added deterministic batch-scan and performance-regression diagrams, bringing the bilingual README contract to eighteen assets.
- Upgraded the permanent CI to the alpha.11 v2 performance gate while retaining Python 3.11–3.14 and isolated Wheel installation checks.

## 0.1.0-alpha.10 — 2026-07-27

- Added deterministic `timeit`/`cProfile` performance evidence with exact-result SHA-256 parity and fail-closed regression thresholds.
- Reused validated EPDM state and kinetic parameters across heterogeneous-site and semibatch inner loops.
- Moved POE RK4 validation outside the integration loop, removed repeated dataclass serialization and reused validated estimation arrays.
- Replaced quadratic settling-time tail scans with a linear last-violation algorithm.
- Reduced provenance I/O to one canonical read per file and removed costly Path conversion work from the source walk.
- Reused validated stream numerics in universal process-package equipment balances.
- Parallelized independent post-coverage CI audits, added elapsed-time reporting and removed duplicate specialist audits from permanent Actions.
- Added a permanent performance-regression gate and machine-generated bilingual README performance tables.

## 0.1.0-alpha.9 — 2026-07-26

- Added a fail-closed source/installed Skillpack inventory for all four delivered Skills.
- Packaged the master Skill, process-general, polymer-general, specialist contracts, schemas, examples, documentation, qualification reports, maintenance scripts and sixteen deterministic diagrams into the Wheel data tree.
- Replaced the former Wheel zipimport smoke test with independent `pip install --target` and clean standard-virtual-environment tests, including hard import-origin checks that reject host editable-install leakage.
- Added installed bilingual-README relative-link auditing so packaged documentation cannot silently reference missing files.
- Expanded the Wheel content contract to require fourteen process-general modules, six workflows, six polymer-general scripts and the complete installed Skill tree.
- Extended the permanent CI matrix through Python 3.14 and kept current-stable Windows/macOS coverage on Python 3.14.
- Added four functional diagrams for control/safety, simulator-neutral integration, EPDM identifiability/uncertainty and the raw-polymer-to-customer bridge.
- Rebuilt the capability matrix around all four Skills and truthful executable/framework/approval boundaries.
- Added cross-platform Skillpack smoke checks and downloadable structured qualification reports to GitHub Actions.
- Sealed target-directory and clean standard-virtual-environment installs with hard module/data origin checks.
- Promoted the hardened source tree to alpha.9 so distinct source and Wheel contents no longer share the released alpha.8 identity.
- Added exact Python classifiers, project URLs, dependency-parity tests and Wheel METADATA/console-script verification.
- Packaged immutable release identity, current source status, complete-distribution boundary and source manifest inside the Wheel.

## 0.1.0-alpha.8 — 2026-07-24

- Added the universal executable process-package platform.
- Promoted EPDM to a flagship P1 reference specialist with fourteen modules and twenty requirements.
- Added generic/EPDM CLI, Schema, fixtures, wheel runtime and adversarial tests.
- Simplified README around universal package, EPDM and POE entrances.


All notable changes are documented here. The project follows Semantic Versioning.

## 0.1.0-alpha.7 — 2026-07-24

### POE P1 reference and delivery closure

- Added bounded parameter estimation, identifiability, reactor, property/transport, dynamics and scale-up reference kernels.
- Added model-asset passports and evidence-level process-package audit v2.
- Added `tsao poe` CLI, P1 audit, coverage gate, wheel member and installed-runtime verification.
- Simplified and synchronized the English/Chinese READMEs and capability matrix.
- Removed one-shot repair/export/finalizer workflows from the final source tree.

### Boundary

The alpha.7 qualification covers open software artifacts only. Historical model restoration and all scientific, engineering, HSE, legal, customer and industrial approvals remain `NOT_EVALUATED`.

## 0.1.0-alpha.6 — 2026-07-23

### POE executable specialist alpha

- Registered all 139 audited SJTU POE corpus assets with SHA-256, lifecycle, confidentiality, software and scale metadata.
- Added the 18-item requirement trace, seven conflict/deviation records and twelve module contracts.
- Isolated historical `POE_Kinetics.m` as controlled evidence and added an independent reference kinetics kernel with conservation and boundary tests.
- Added property-method and simulator-neutral steady/dynamic case qualification.
- Replaced filename/non-empty package checks with manifest, Schema, hash, content, cross-reference, conflict and approval auditing.
- Added placeholder, path-traversal, hash-tampering, malformed composition, unclosed recycle, missing dynamic asset and Chinese legacy-package attacks.
- Packaged the POE Skill and controlled data into the wheel, verified wheel contents, and removed tracked build/egg-info duplicates.
- Kept historical commercial execution and all scientific/engineering/HSE/customer/industrial approvals `NOT_EVALUATED`.


### Trust-chain convergence

- Unified the package, manifest, Skill, citation, README, CI and release-identity version.
- Made `doctor --profile full` verify the complete-distribution manifest, `FILE_MANIFEST.tsv`, `checksums.sha256`, SBOM and release identity—not just marker-file presence.
- Added deterministic public-source snapshots with internal metadata and an externally reported SHA-256.
- Added Markdown-link, release-metadata, tampering and source-snapshot regression tests.
- Reduced GitHub Actions to least privilege: qualification and snapshot jobs are read-only; only the source-manifest refresh job can write.
- Removed the untested `[skip ci]` manifest-head pattern. A refreshed manifest commit triggers a second qualification run.
- Reconciled stale README/report references and corrected the final alpha.5 complete-distribution count to 470/470.

### Boundary

Source-core qualification and complete-distribution qualification are separate hashes and records. Scientific, engineering, safety, legal, customer and industrial approvals remain `NOT_EVALUATED`.

## 0.1.0-alpha.5 — 2026-07-23

### Added and strengthened

- Added `tsao doctor` for one-command version, Schema, capability, repository and provenance validation.
- Added separate public-source and complete-distribution SHA-256 manifests.
- Added source-asset Schema and explicit source-parity documentation.
- Expanded POE and universal-polymer known-solution, invalid-input, evidence, matrix, package, scale-up, balance and DoE tests.
- Isolated the 334 inherited EPDM tests by file to eliminate aggregate pytest teardown deadlocks without removing tests.
- Simplified both READMEs to one canonical usage path while retaining the complete engineering contract in `SKILL.md`.
- Qualified the complete distribution twice at 470/470 tests and revalidated the deterministic archive from a cleanroom extraction.

### Boundary

Source manifests identify public source, generated reports and controlled binaries separately. Software qualification remains distinct from scientific, engineering, safety, legal, customer and industrial approval.

## 0.1.0-alpha.4 — 2026-07-22

### Completed

- Simplified the English and Chinese READMEs around mission, four routes, one-call output, quick start and truthful boundaries.
- Made one-call execution machine-backed: `tsao init` creates 266 G0–G18 × 14-workstream packages, M0–M9 maturity and explicit execution states.
- Expanded `process-general` into a non-polymer process pack and added known-solution kernels for reactors, bioprocess transfer, electrochemistry, crystallization, recycle, reliability and capability.
- Added typed contracts for work packages, maturity, scale-up claims, external execution and acceptance.
- Hardened POE and universal-polymer scripts against duplicate evidence, empty matrices, invalid numbers, unsafe force rebuilds and obsolete G0–G12 plans.
- Added balanced specialist, capability, Schema and adversarial regression tests.
- Qualified the complete distribution twice at 458/458 tests and revalidated the deterministic archive from a cleanroom extraction.

## 0.1.0-alpha.3 — 2026-07-22

- Restored the original one-call execution contract, fourteen workstreams, evidence/claim states, accountable roles and M0–M9 maturity.
- Added `skills/process-general/` and integrated it into routing, initialization and Schema.
- Added lineage-completeness and subskill-content regression tests.

## 0.1.0-alpha.2 — 2026-07-21

- Split the monolithic core into independently testable Gate, evidence, model, assurance, routing, science, project and archive modules.
- Made Gate transitions, evidence, model risk, projects and archives fail closed.
- Added structured CLI errors, process-group cleanup and repository/Schema regression tests.

## 0.1.0-alpha.1 — 2026-07-21

- Added the TSAO master skill, G0–G18 lifecycle, EPDM/POE/universal-polymer contracts, initial Schemas, CLI, tests and governance.
