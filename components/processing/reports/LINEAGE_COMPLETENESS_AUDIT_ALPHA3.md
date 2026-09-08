# TSAO lineage-completeness audit — alpha.3

## Verdict

Alpha.2 was strong in software assurance but did **not** fully preserve the earliest operating mission in the root Skill. Alpha.3 restores the highest-priority missing contracts and now passes both source-core and complete-distribution qualification.

It is now a credible universal chemical-process development alpha release. It is **not yet accurate** to call it stable 1.0 or equally deep in every process domain.

## Baselines compared

1. `SJTU-POE-PROCESSING-SKILL 1.0.0` — evidence to kinetics, properties, reactor, steady/dynamic process, scale-up and acceptance.
2. `SJTU-UNIVERSAL-POLYMER-TECHNOLOGY-DEVELOPMENT-SKILL 2.0.0` — one-call project generation, fourteen workstreams, recursive file inventory, falsifiable research graph and M0–M9 maturity.
3. `EPDM Universal Polymer Technology Development Skill 9.0.0` — catalyst/active-site/terpolymer architecture/recovery/compound/customer and lifecycle assurance.
4. `TSAO 0.1.0-alpha.2` — hardened Gate, evidence, model, project, archive and cleanroom baseline.

## Restored from the earliest skills

- mandatory one-call execution contract;
- fourteen professional workstreams and accountable roles;
- explicit observed/reported/calculated/inferred/assumed/proposed/planned/approved states;
- M0–M9 maturity model;
- immediate reusable project artifacts;
- truthful `PLANNED` / `REQUIRES_EXTERNAL_EXECUTION` boundaries;
- POE evidence–kinetics–properties–reactor–steady/dynamic–scale-up–acceptance chain;
- universal-polymer route neutrality;
- EPDM v9 assurance, evidence-life and specialist depth.

## New completeness corrections

- added `skills/process-general/` for non-polymer reaction, separation, bioprocess, electrochemical, solids, fine-chemical and petrochemical work;
- every initialized project must activate at least one supported subskill;
- aligned root Skill, package, manifest, citation and CI version identity;
- added lineage and specialist-content regression tests;
- made the complete-distribution CI wrapper independent of caller working directory;
- moved the pytest hard exit to `pytest_sessionfinish`, eliminating 100%-complete teardown hangs.

## Qualification

### Public GitHub source core

The same alpha.3 head commit passed two executions of the GitHub Actions matrix. Python 3.11 and 3.12 each passed installation, dependency integrity, compilation, tests, Ruff, non-isolated wheel construction, CLI smoke and the integrated CI runner.

### Complete distribution

- full CI round 1: **428/428 PASS**;
- full CI round 2: **428/428 PASS**;
- frozen core hash: `0935a32c3a0ea352df4f97d5d6e42af715033e3f2f4b082ad4611ea293220a04`;
- core unchanged during both rounds: PASS;
- dual deterministic ZIP build: byte-identical;
- archive members: **1,136**;
- archive SHA-256: `1a2a027869314b44b7c3c1d2e70ef112767de31b562a181a6bbb91e317361f47`;
- cleanroom extracted CI: **428/428 PASS**;
- cleanroom issues: none.

## Remaining stable-1.0 blockers

1. The public PR does not yet expose every file from all inherited specialist source trees as ordinary reviewable source.
2. POE and universal-polymer executable test depth remains much smaller than EPDM.
3. Non-polymer domains need dedicated model libraries and known-solution fixtures comparable to EPDM.
4. Windows and macOS installation/CLI qualification is not yet complete.
5. More typed schemas are required for workstreams, maturity evidence, scale-up claims, package acceptance and external-execution handoffs.

## Approval boundary

Software-artifact qualification is PASS. Physical experiments, commercial simulation, engineering design, HAZOP/LOPA/SIL, legal FTO, customer qualification, pilot/demonstration and industrial performance remain `NOT_EVALUATED`.
